import pandas as pd
import numpy as np
import re


def procesar_fecha_estado(texto):
    meses = {'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'}

    texto_str = str(texto)
    
    # 1. Extracción de Fecha (Con año o sin año, algunos nuevos salen sin año)
    match_completo = re.search(r'(\d{2})\.\s([a-z]{3})\s(\d{4})', texto_str)
    match_sin_año = re.search(r'(\d{2})\.\s([a-z]{3})', texto_str)
    
    fecha_str = None
    
    if match_completo:
        dia, mes_txt, año = match_completo.groups()
        mes_num = meses.get(mes_txt.lower(), '01')
        fecha_str = f"{dia}/{mes_num}/{año}"
    elif match_sin_año:
        dia, mes_txt = match_sin_año.groups()
        mes_num = meses.get(mes_txt.lower(), '01')
        fecha_str = f"{dia}/{mes_num}/2026"
    
    # 2. Extracción de Estado
    estado = "Desconocido"
    texto_lower = texto_str.lower()
    
    if "aterrizado" in texto_lower: estado = "Aterrizado"
    elif "cancelado" in texto_lower: estado = "Cancelado"
    # Si no es ninguno de estos, se queda en "Desconocido" para borrarlo luego, 
    # puede haber vuelos "desviados" o "programados" que no tendremos en cuenta
    
    return pd.Series([fecha_str, estado])

def procesar_vuelo(texto):
    # Texto ejemplo: "IB123 IBE0123 Iberia IB/IBE"
    parts = str(texto).split()
    if not parts: return pd.Series([np.nan, np.nan])
    
    id_vuelo = parts[0]
    
    nombre_limpio = []
    if len(parts) > 1:
        for p in parts[1:]:
            # Si contiene barra '/' es código (ej: IB/IBE), lo saltamos
            if '/' in p: continue
            
            # Si parece otro código de vuelo (Letras mayúsculas seguidas de números), lo saltamos
            # Ej: IBE0123
            if re.match(r'^[A-Z]{1,3}\d{1,4}[A-Z]*$', p): continue
            
            # Si pasa los filtros, es parte del nombre
            nombre_limpio.append(p)
            
    COMPAÑIA = " ".join(nombre_limpio)
    
    return pd.Series([id_vuelo, COMPAÑIA])

def extraer_destino_icao(texto):
    match = re.search(r'\(\w+\s/\s(\w{4})\)', str(texto))
    return match.group(1) if match else np.nan

def extraer_hora_programada(texto):
    match = re.search(r'(\d{2}:\d{2})\s(CET|WET)', str(texto))
    return match.group(1) if match else np.nan

def calcular_retraso(texto):
    texto = str(texto).lower()
    if "tarde" not in texto: return 0
    
    minutos_totales = 0
    horas = re.search(r'(\d+)\s*h', texto)
    if horas: minutos_totales += int(horas.group(1)) * 60
    
    mins = re.search(r'(\d+)\s*min', texto)
    if mins: minutos_totales += int(mins.group(1))
        
    return int(minutos_totales) if minutos_totales > 0 else 0
    
def calcular_gravedad(row):
    # Cancelaciones gravedad 4
    if row['ESTADO'] == 'Cancelado':
        return 4
    
    # Obtenemos el retraso. Si es nulo, significa que fue puntual o temprano -> 0
    retraso = row['RETRASO_MIN']
    if pd.isna(retraso):
        retraso = 0
    
    # Escala de gravedad por tiempo
    if retraso > 90:
        return 3        # > 1h 30m
    elif retraso > 45:
        return 2        # > 45m y <= 90m
    elif retraso >= 20:
        return 1        # Entre 20m y 45m
    else:
        return 0        # < 20m (incluye puntuales)

def clean_flights(df: pd.DataFrame):

    # Si no existe un identificador del vuelo es basura sin importancia que ha cogido mal el script de selenium
    df = df.dropna(subset=['Vuelo']).reset_index(drop=True)

    # Quitamos 2 columnas extras que no necesitaremos en adelante
    cols_to_drop = ['LLEGADO', 'DURACIÓN']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')

    df[['FECHA', 'ESTADO']] = df['FECHA / ESTADO'].apply(procesar_fecha_estado)
    df[['ID_VUELO', 'COMPAÑIA']] = df['Vuelo'].apply(procesar_vuelo)
    df['DESTINO_ICAO'] = df['A'].apply(extraer_destino_icao)
    df['HORA_PROGRAMADA'] = df['SALIDA PROGRAMADA'].apply(extraer_hora_programada)
    df['RETRASO_MIN'] = df['PARTIDA'].apply(calcular_retraso).astype('Int64')
    df['GRAVEDAD'] = df.apply(calcular_gravedad, axis=1)
    df = df.rename(columns={'ICAO': 'ORIGEN_ICAO'})
    df = df.rename(columns={'Origen': 'ORIGEN'})

    # Filtramos las filas donde el estado sea "Desconocido"
    df_final = df[df['ESTADO'] != 'Desconocido'].copy()

    # Selección de columnas
    columnas_finales = [
        'FECHA', 'GRAVEDAD', 'ORIGEN_ICAO', 'DESTINO_ICAO', 
        'COMPAÑIA', 'ID_VUELO', 'HORA_PROGRAMADA', 'RETRASO_MIN', "ORIGEN"
    ]

    df_final = df_final[columnas_finales]

    return df_final

def clean_weather(df_weather: pd.DataFrame):
    df = df_weather.copy()
    df['Día'] = pd.to_datetime(df['Día'], dayfirst=True)
    df = df.sort_values(['Ciudad', 'Día'])

    # Función auxiliar de limpieza
    def extraer_solo_numero(valor):
        # Si es nulo o vacío
        if pd.isna(valor) or str(valor).strip() == '' or str(valor) == 'nan': 
            return np.nan
        # Caso especial '0.00.0' -> devuelve 0.0
        if '0.00.0' in str(valor): 
            return 0.0
        
        # Regex para buscar float o int
        match = re.search(r"([-+]?\d*\.\d+|\d+)", str(valor))
        return float(match.group(1)) if match else np.nan

    # 1. Si faltan datos, se realiza interpolación lineal en el viento y la temperatura
    cols_termicas = [
        'T. max. (°C) (Hora)', 'T. min. (°C) (Hora)', 'T. media (°C)', 
        'Racha (km/h) (Hora)', 'V. max. (km/h) (Hora)'
    ]

    for col in cols_termicas:
        if col in df.columns:
            df[col] = df[col].apply(extraer_solo_numero)
            # Interpolamos ya que la temperatura suele ser continua
            df[col] = df.groupby('Ciudad')[col].transform(
                lambda x: x.interpolate(method='linear', limit_direction='both')
            )

    # 2. Si faltan datos en la lluvia no interpolamos, rellenamos con 0
    cols_precip = [
        'Pr. 00 - 24h (mm)', 'Pr. 00 - 06h (mm)', 
        'Pr. 06 - 12h (mm)', 'Pr. 12 - 18h (mm)', 'Pr. 18 - 24h (mm)'
    ]

    for col in cols_precip:
        if col in df.columns:
            df[col] = df[col].apply(extraer_solo_numero)
            df[col] = df[col].fillna(0)

    return df

def limpiar_valor_clima(valor):
    """Extrae el número de strings tipo '4.9(17:30)'"""
    if pd.isna(valor) or valor == '0.00.0': return 0.0
    match = re.search(r"([-+]?\d*\.\d+|\d+)", str(valor))
    return float(match.group(1)) if match else 0.0

def clean_merge_df(df):
    df_ml = df.copy()
    
    # Limpieza de columnas térmicas y viento
    cols_clima = ['T. max. (°C) (Hora)', 'T. min. (°C) (Hora)', 'T. media (°C)', 
                  'Racha (km/h) (Hora)', 'V. max. (km/h) (Hora)']
    for col in cols_clima:
        df_ml[col] = df_ml[col].apply(limpiar_valor_clima)

    # Conversión de Hora del día a minutos
    df_ml['MINUTOS_DIA'] = df_ml['HORA_PROGRAMADA'].apply(lambda x: int(x.split(':')[0])*60 + int(x.split(':')[1]))
    
    df_ml['HORA_SIN'] = np.sin(2 * np.pi * df_ml['MINUTOS_DIA'] / 1440)
    df_ml['HORA_COS'] = np.cos(2 * np.pi * df_ml['MINUTOS_DIA'] / 1440)

    # Precipitación por ventana horaria
    def asignar_precip(row):
        h = int(row['HORA_PROGRAMADA'].split(':')[0])
        if 0 <= h < 6: return row['Pr. 00 - 06h (mm)']
        if 6 <= h < 12: return row['Pr. 06 - 12h (mm)']
        if 12 <= h < 18: return row['Pr. 12 - 18h (mm)']
        return row['Pr. 18 - 24h (mm)']

    df_ml['PRECIP_MOMENTO'] = df_ml.apply(asignar_precip, axis=1)

    # Temperatura Estimada
    def asignar_temp_estimada(row):
        # Usamos la hora del VUELO
        h = int(row['HORA_PROGRAMADA'].split(':')[0])
        
        if 22 <= h or h < 8: 
            return row['T. min. (°C) (Hora)'] 
        if 12 <= h < 18: 
            return row['T. max. (°C) (Hora)']
        return row['T. media (°C)']

    df_ml['TEMP_ESTIMADA'] = df_ml.apply(asignar_temp_estimada, axis=1)


    # Quitamos las columnas originales de lluvia y horas para evitar redundancia
    df_ml = df_ml.rename(columns={'Racha (km/h) (Hora)': 'Racha (km/h)'})
    cols = [
        'FECHA', 'GRAVEDAD', 'ORIGEN_ICAO', 'DESTINO_ICAO', 'COMPAÑIA', 
        'RETRASO_MIN', 'HORA_SIN', "HORA_COS", "MINUTOS_DIA", 'PRECIP_MOMENTO', 'TEMP_ESTIMADA', 
        'Racha (km/h)'
    ]
    
    return df_ml[cols]