# Cancelación y retraso de vuelos en los aeropuertos españoles más importantes en relación con el clima.

**Autor:** Jorge Solán Morote
**Asignatura:** Tipología y ciclo de vida de los datos  
**Máster:** Data Science, UOC  
**Práctica:** 2

---

## Descripción

Este proyecto tiene como objetivo extraer, combinar, limpiar y analizar información sobre **retrasos y cancelaciones de vuelos** en España con **datos climáticos** de las estaciones meteorológicas de los aeropuertos correspondientes. El flujo general del proyecto es:

1. Extracción de un dataset con registros de **retrasos y cancelaciones de vuelos** con destino en distintos aeropuertos de España.
2. Extracción de un dataset con **datos climáticos** de las estaciones meteorológicas asociadas a esos aeropuertos, incluyendo precipitaciones, temperaturas y rachas de viento.
4. **Limpieza y transformación** de ambos dataset antes de la fusión.
3. **Fusión de ambos datasets** según ciudad de destino y estación, y fecha del vuelo y medición meteorológica, generando un dataset final más completo.

---

## Estructura del proyecto
```text
main/
├─ data/                      # Carpeta donde se guardan los datasets generados
│ ├─ aemet_clean.csv          # Dataset con los datos limpios del clima de la AEMET
│ ├─ aemet.csv                # Dataset con los datos del clima de la AEMET
│ ├─ dataset.csv              # Dataset final para el modelado
│ ├─ flights_clean.csv        # Dataset con los datos limpos de vuelos
│ └─ flights.csv              # Dataset con los datos de vuelos
├─ source/
│ ├─ main.py                  # Script principal de la práctica.
│ ├─ clean_data.py            # Script para la limpieza necesaria de los datasets
│ ├─ selenium_interaction.py  # Funciones de interacción con Selenium
│ └─ wscapping_aemet.py       # Scraping de datos meteorológicos de AEMET
└─ analisis.ipynb             # Jupyter notebook con el análisis de los datos
```
---

## Uso

El script principal es `main.py`, que permite generar datasets de vuelos con datos climáticos además de los datasets intermedios para ver su progrso de limpieza.

**Opciones de ejecución:**

- `--headless`  
  Ejecuta Selenium en modo headless (sin abrir la ventana del navegador). False por defecto


## Ejemplo de uso

**Generar dataset de vuelos, clima y su fusión para el modelado sin abrir ventana para selenium**
```
python source/main.py --headless
```
