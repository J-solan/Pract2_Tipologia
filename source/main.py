from selenium_interaction import search_flights
from wscrapping_aemet import return_airport, extract_stats
from clean_data import clean_flights, clean_weather, clean_merge_df

import argparse
import pandas as pd

def merge_data(df_vuelos: pd.DataFrame, df_clima: pd.DataFrame):
    vuelos = df_vuelos.copy()
    clima = df_clima.copy()

    # Convertimos a datetime
    vuelos['FECHA_DT'] = pd.to_datetime(vuelos['FECHA'], dayfirst=True)
    clima['FECHA_DT'] = pd.to_datetime(clima['Día'], dayfirst=True)

    ciudades_clima = clima['Ciudad'].unique()

    def encontrar_ciudad_clima(ciudad_vuelo):
        # Para cada ciudad del vuelo (ej: "Gran Canaria"), buscamos si alguna ciudad del clima (ej: "Canaria") está contenida en ella.
        for ciudad_c in ciudades_clima:
            if ciudad_c in ciudad_vuelo:
                return ciudad_c # Devolvemos el nombre tal cual aparece en el CSV de clima
        return None

    # Creamos una columna enlace en vuelos con el nombre estandarizado del clima
    vuelos['Ciudad_Enlace'] = vuelos['ORIGEN'].apply(encontrar_ciudad_clima)

    # Unimos por FECHA y por la CIUDAD ENLAZADA
    df_final = pd.merge(
        vuelos, 
        clima, 
        left_on=['FECHA_DT', 'Ciudad_Enlace'], 
        right_on=['FECHA_DT', 'Ciudad'], 
        how='left' # Left join: Mantenemos todos los vuelos, si no hay clima quedará vacío
    )

    # Eliminamos columnas auxiliares o duplicadas tras el merge
    cols_a_eliminar = ['FECHA_DT', 'Ciudad_Enlace', 'Ciudad', 'Día']
    df_final = df_final.drop(columns=cols_a_eliminar, errors='ignore')

    return df_final


if __name__ == "__main__":

    ## Configuración del parser de argumentos ##
    parser = argparse.ArgumentParser(
        description="Descarga información de vuelos de una lista de ciudades destino."
    )

    parser.add_argument(
        "--headless",
        action="store_true",              # convierte el flag en True si se pasa
        required=False,                   # no es obligatorio
        default=False,                    # valor por defecto
        help="Ejecutar el navegador en modo headless (sin interfaz gráfica)."
    )

    args = parser.parse_args()
    headless= args.headless

    # Lista para las Ciudades de la AEMET
    CIUDADES = ["Madrid", "Barcelona", "Mallorca", "Málaga", "Alicante", "Canaria", "Tenerife", "Ibiza", "Lanzarote", "Valencia"]
    # Diccionario para los aeropuertos
    AEROPUERTOS = [
        {"ciudad": "Madrid", "icao": "LEMD"},
        {"ciudad": "Barcelona", "icao": "LEBL"},
        {"ciudad": "Mallorca", "icao": "LEPA"},
        {"ciudad": "Málaga", "icao": "LEMG"},
        {"ciudad": "Alicante", "icao": "LEAL"},
        {"ciudad": "Gran Canaria", "icao": "GCLP"},
        {"ciudad": "Tenerife Sur", "icao": "GCTS"},
        {"ciudad": "Ibiza", "icao": "LEIB"},
        {"ciudad": "Lanzarote", "icao": "GCRR"},
        {"ciudad": "Valencia", "icao": "LEVC"},
    ]

    dfs_aemet = []
    dfs_aeropuertos = []
    for ciudad in CIUDADES:
        airport = return_airport(ciudad)
        df_weather = extract_stats(airport["value"])
        df_weather["Ciudad"] = ciudad
        dfs_aemet.append(df_weather)
    
    for aeropuerto in AEROPUERTOS:
        df_aeropuerto = search_flights(headless, aeropuerto)
        dfs_aeropuertos.append(df_aeropuerto)

    df_flightera = pd.concat(dfs_aeropuertos, ignore_index=True)
    df_flightera.to_csv("data/flights.csv", index=False, encoding="utf-8")
    df_aemet = pd.concat(dfs_aemet, ignore_index=True)
    df_aemet.to_csv("data/aemet.csv", index=False, encoding="utf-8")

    df_clean_flightera = clean_flights(df_flightera)
    df_clean_aemet = clean_weather(df_aemet)

    df_clean_flightera.to_csv("data/flights_clean.csv", index=False, encoding="utf-8")
    df_clean_aemet.to_csv("data/aemet_clean.csv", index=False, encoding="utf-8")

    df = merge_data(df_clean_flightera, df_clean_aemet)

    clean_df = clean_merge_df(df)
    clean_df.to_csv("data/dataset.csv", index=False, encoding="utf-8")