from bs4 import BeautifulSoup
import requests
import pandas as pd
from datetime import datetime
from unidecode import unidecode

AEMET = "https://www.aemet.es/es/eltiempo/observacion/"
ENDPOINT = "ultimosdatos?k=esp&w=1&datos=det"

def search_station(comunidad):
    url_comunidad = AEMET +  f"ultimosdatos?k={comunidad}&w=1&datos=det"
    response_comunidad = requests.get(url_comunidad)
    soup_comunidad = BeautifulSoup(response_comunidad.text, "html.parser")

    # Seleccionamos el select de estaciones en esa página
    select_estaciones = soup_comunidad.select_one(
        "body > div:nth-of-type(4) > div:nth-of-type(2) > div > div:nth-of-type(2) > div:nth-of-type(6) > form > div:nth-of-type(2) > select"
    )

    estaciones = [option for option in select_estaciones.find_all('option')]
    return [estacion for estacion in estaciones]

def search_airport(value, objetivo):
    estaciones = search_station(value)
    for option in estaciones:
        estacion = unidecode(option.text).lower()
        if objetivo in estacion and "aeropuerto" in estacion:
            return option
    return None

def extract_stats(airport, w_values=[1, 2]):
    all_dfs = []
    
    for w in w_values:
        endpoint = f"ultimosdatos?k=and&l={airport}&w={w}&datos=det"
        response = requests.get(AEMET + endpoint)
        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar la tabla principal de datos
        tabla = soup.find("table")
        if not tabla:
            print("No se encontró ninguna tabla en la página")
            continue

        # Cabeceras - reemplazar saltos de línea por espacios
        headers = [th.text.strip().replace('\n', ' ') for th in tabla.find_all("th")]

        # Filas de datos
        filas = []
        for tr in tabla.find_all("tr")[1:]:  # Saltamos la fila de cabecera
            celdas = [td.text.strip().replace('\n', ' ') for td in tr.find_all("td")]
            if celdas:
                filas.append(celdas)

        # Crear DataFrame
        df = pd.DataFrame(filas, columns=headers)
        
        if df.empty:
            continue
        
        # Transformar DataFrame de w=1 para que coincida con w=2
        if w == 1:
            # Eliminar columnas Estación, Provincia y Dt. hasta (hora)
            cols_to_drop = ['Estación', 'Provincia', 'Dt. hasta (hora)']
            df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
            
            # Añadir columna Día con la fecha de hoy
            df['Día'] = datetime.now().strftime('%d %b. %Y').lower()
            
            # Renombrar columnas para coincidir con w=2
            rename_map = {
                'T. max. (°C)': 'T. max. (°C) (Hora)',
                'T. min. (°C)': 'T. min. (°C) (Hora)',
                'Racha (km/h)': 'Racha (km/h) (Hora)',
                'V. max. (km/h)': 'V. max. (km/h) (Hora)',
                'Pr. 00 - 24h (mm)': 'Pr. 00 - 24h (mm)'
            }
            df = df.rename(columns=rename_map)
            
            # Calcular T. media como promedio de T. max y T. min
            if 'T. max. (°C) (Hora)' in df.columns and 'T. min. (°C) (Hora)' in df.columns:
                df['T. media (°C)'] = df.apply(
                    lambda row: round((float(row['T. max. (°C) (Hora)'].split('(')[0]) + 
                                     float(row['T. min. (°C) (Hora)'].split('(')[0])) / 2, 1)
                    if row['T. max. (°C) (Hora)'] and row['T. min. (°C) (Hora)'] 
                    else None, 
                    axis=1
                )
            
            # Añadir columnas de precipitación horaria con 0.0
            df['Pr. 00 - 06h (mm)'] = '0.0'
            df['Pr. 06 - 12h (mm)'] = '0.0'
            df['Pr. 12 - 18h (mm)'] = '0.0'
            df['Pr. 18 - 24h (mm)'] = '0.0'
            
            # Reordenar columnas para que coincidan con w=2
            column_order = [
                'Día',
                'T. max. (°C) (Hora)',
                'T. min. (°C) (Hora)',
                'T. media (°C)',
                'Racha (km/h) (Hora)',
                'V. max. (km/h) (Hora)',
                'Pr. 00 - 24h (mm)',
                'Pr. 00 - 06h (mm)',
                'Pr. 06 - 12h (mm)',
                'Pr. 12 - 18h (mm)',
                'Pr. 18 - 24h (mm)'
            ]
            # Solo reordenar las columnas que existen
            df = df[[col for col in column_order if col in df.columns]]
        
        all_dfs.append(df)

    # Combinar todos los DataFrames
    if not all_dfs:
        print("No se encontraron datos")
        return None
    
    df_combined = pd.concat(all_dfs, ignore_index=True)
    
    # Convertir la columna de fecha al formato dd/mm/yyyy
    if 'Día' in df_combined.columns:
        # Diccionario para meses en español
        meses_es = {
            'ene.': '01', 'feb.': '02', 'mar.': '03', 'abr.': '04',
            'may.': '05', 'jun.': '06', 'jul.': '07', 'ago.': '08',
            'sep.': '09', 'oct.': '10', 'nov.': '11', 'dic.': '12'
        }
        
        def convertir_fecha(fecha_str):
            # Formato: "07 nov. 2025"
            partes = fecha_str.split()
            if len(partes) == 3:
                dia = partes[0].zfill(2)
                mes = meses_es.get(partes[1], '01')
                año = partes[2]
                return f"{dia}/{mes}/{año}"
            return fecha_str
        
        df_combined['Día'] = df_combined['Día'].apply(convertir_fecha)
    
    # Eliminar duplicados por fecha
    if 'Día' in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=['Día'], keep='first')
    
    return df_combined

def return_airport(objetivo: str):
    value = None
    objetivo = unidecode(objetivo).lower().replace(" ", "-")

    # Petición inicial
    url = AEMET + ENDPOINT
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Seleccionamos el select de comunidades
    select_comunidades = soup.select_one(
        "select#ccaa_selector"
    )

    comunidades = select_comunidades.find_all('option')
    for comunidad in comunidades:
        if objetivo in comunidad.text.lower():
            return search_airport(comunidad['value'], objetivo)

    try:
        for comunidad in comunidades:
            airport = search_airport(comunidad['value'], objetivo)
            if airport:
                return airport
        return None
    except Exception as e:
        print("Error:", e)
