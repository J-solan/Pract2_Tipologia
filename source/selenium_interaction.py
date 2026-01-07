from seleniumbase import Driver
from selenium.webdriver.common.by import By
import pandas as pd
import time
import random
from datetime import datetime, timedelta
from io import StringIO 

# --- CONFIGURACIÓN ---
TRAMOS_HORARIOS = [f"{h:02d}_00" for h in range(0, 24, 2)] 

DIAS_HISTORICO = 7
ARCHIVO_SALIDA = "vuelos_semana_completa.csv"

XPATH_TABLA = "//main//table" 

def generar_fechas(dias):
    return [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, dias + 1)]

def search_flights(headless, aeropuerto) -> pd.DataFrame:    
    driver = Driver(uc=True, headless=headless, block_images=True)
    
    fechas = generar_fechas(DIAS_HISTORICO)
    todos_los_datos = [] # Aquí se guardarán los DataFrames
    consulta_actual = 0

    try:
        for fecha in fechas:
            print(f"\nProcesando: {aeropuerto['ciudad']} - {fecha}")
            
            for hora in TRAMOS_HORARIOS:
                consulta_actual += 1
                url = f"https://www.flightera.net/es/airport/{aeropuerto['ciudad']}/{aeropuerto['icao']}/departure/{fecha}%20{hora}"
                                    
                try:
                    driver.get(url)
                    
                    try:
                        driver.wait_for_element(XPATH_TABLA, timeout=6)
                    except:
                        print("❌ Timeout", end="\r")
                        continue

                    # Extracción
                    tabla_element = driver.find_element(By.XPATH, XPATH_TABLA)
                    tabla_html = tabla_element.get_attribute('outerHTML')
                    
                    # Parseo
                    dfs = pd.read_html(StringIO(tabla_html))
                    
                    if dfs:
                        df = dfs[0]
                        # Limpieza de cabeceras repetidas
                        df = df[df.iloc[:, 0] != df.columns[0]]
                        
                        if len(df) > 0:
                            df['Origen'] = aeropuerto['ciudad']
                            df['ICAO'] = aeropuerto['icao']
                            todos_los_datos.append(df)
                
                except Exception as e:
                    print(f"❌ Err", end="\r")
                
                # Pausa de seguridad
                time.sleep(random.uniform(0.25, 1))

    finally:
        driver.quit()

    if todos_los_datos:
        df_final = pd.concat(todos_los_datos, ignore_index=True)
        # Quitamos algunas columnas que coge el script sin sentido
        df_final = df_final.loc[:, ~df_final.columns.str.contains('^Unnamed')]
        
        # ELIMINAR DUPLICADOS
        # Como escaneamos cada 2h, hay solapamientos. Esto deja solo los únicos.
        df_final = df_final.drop_duplicates()
        return df_final
    else:
        print("\nNo se extrajeron datos. Revisa tu conexión.")
