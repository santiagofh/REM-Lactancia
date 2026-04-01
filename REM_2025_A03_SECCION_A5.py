#%%
import os
from pathlib import Path
import pandas as pd
import numpy as np
import locale
locale.setlocale(locale.LC_COLLATE, 'es_ES.UTF-8')  # para sistemas Linux/Mac
# locale.setlocale(locale.LC_COLLATE, 'Spanish_Spain.1252')  # para Windows
os.makedirs('output', exist_ok=True)

# Cargar datos de ejemplo
codigos_de_interes = [
    "A0200001",
    "A0200002",
]

path_a =r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2025\Datos\SerieA2025.csv"
CHUNK_SIZE = 200_000
USECOLS = [
    "CodigoPrestacion",
    "IdRegion",
    "IdServicio",
    "IdEstablecimiento",
    "IdComuna",
    "Mes",
    "Col04",
    "Col05",
    "Col06",
]

chunks = []
for chunk in pd.read_csv(path_a, sep=";", usecols=USECOLS, dtype=str, chunksize=CHUNK_SIZE):
    chunk = chunk[(chunk['CodigoPrestacion'].isin(codigos_de_interes)) & 
                  (chunk['IdRegion'].astype(str) == '13')]
    if chunk.empty:
        continue
    chunks.append(chunk)

df = pd.concat(chunks, ignore_index=True)
#%%
est_dir = Path(r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\ESTABLECIMIENTOS")
candidates = sorted(est_dir.glob("establecimientos_*.csv"))
if not candidates:
    raise FileNotFoundError(f"No se encontró establecimientos_*.csv en {est_dir}")
est_path = candidates[-1]
df_est = pd.read_csv(est_path, dtype=str, sep=";")

df['IdEstablecimiento'] = pd.to_numeric(df['IdEstablecimiento'], errors='coerce').astype('Int64')

df_est['codigo_establecimiento'] = pd.to_numeric(df_est['EstablecimientoCodigo'], errors='coerce').astype('Int64')
df_est['nombre_ss'] = df_est['SeremiSaludGlosa_ServicioDeSaludGlosa']
df_est['nombre_establecimiento'] = df_est['EstablecimientoGlosa']
df_est['nombre_comuna'] = df_est['ComunaGlosa']

df_est = df_est.drop_duplicates(subset=['codigo_establecimiento'])

dict_ss = dict(zip(df_est.codigo_establecimiento, df_est.nombre_ss))
dict_establecimiento = dict(zip(df_est.codigo_establecimiento, df_est.nombre_establecimiento))
dict_comuna = dict(zip(df_est.codigo_establecimiento, df_est.nombre_comuna))

df['nombre_ss'] = df.IdEstablecimiento.map(dict_ss)
df['nombre_establecimiento'] = df.IdEstablecimiento.map(dict_establecimiento)
df['nombre_comuna'] = df.IdEstablecimiento.map(dict_comuna)

# Diagnostico de cruces perdidos
missing_mask = df['nombre_establecimiento'].isna()
missing_count = int(missing_mask.sum())
total_count = int(len(df))
if missing_count:
    missing_ids = (
        df.loc[missing_mask, 'IdEstablecimiento']
        .dropna()
        .astype('Int64')
        .drop_duplicates()
        .sort_values()
    )
    print(
        f"[AVISO] Establecimientos sin cruce: {missing_count} de {total_count} "
        f"({missing_count/total_count:.2%})."
    )
    pd.DataFrame({'IdEstablecimiento': missing_ids}).to_csv(
        'output/2025_A03_SECCION_A5_establecimientos_sin_cruce.csv',
        index=False
    )
#%%
# Filtrar y renombrar las Columnas correspondientes a la sección A3
seccion_a3 = {
    "A0200001": 'MENORES CONTROLADOS',
    "A0200002": 'LACTANCIA MATERNA EXCLUSIVA',
}

seccion_a3_Col = {
    # Según diccionario A03:
    # Col04=1° mes, Col05=3° mes, Col06=6° mes
    'Col04': '1° mes',
    'Col05': '3° mes',
    'Col06': '6° mes'
}

df_a3 = df[df['CodigoPrestacion'].isin(seccion_a3.keys())]
df_a3 = df_a3.rename(columns=seccion_a3_Col)
df_a3['Prestación'] = df_a3['CodigoPrestacion'].map(seccion_a3)


# %%
df_a3.to_csv('output/2025_A03_SECCION_A5.csv')
df_a3.to_excel('output/2025_A03_SECCION_A5.xlsx')
# %%
