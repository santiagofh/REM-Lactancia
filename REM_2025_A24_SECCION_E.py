#%%
import os
from pathlib import Path
import pandas as pd
import numpy as np
import locale
locale.setlocale(locale.LC_COLLATE, 'es_ES.UTF-8')  # para sistemas Linux/Mac
# locale.setlocale(locale.LC_COLLATE, 'Spanish_Spain.1252')  # para Windows
os.makedirs('output', exist_ok=True)

# Códigos Sección E A24 (incluye transición 2024-2025)
codigos_de_interes = [
    "24200100",  # histórico
    "24200134",
    "24300103",
    "24311025",
    "24311026",
    "24311027",
    "24311028",
    "29101770",
    "29101771",
    "29101772",
]

path_a =r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2025\Datos\SerieA2025.csv"
CHUNK_SIZE = 200_000
USECOLS = [
    "CodigoPrestacion",
    "IdRegion",
    "IdServicio",
    "IdEstablecimiento",
    "IdComuna",
    "Col01",
    "Col02",
    "Col03",
    "Col04",
]

chunks = []

# Filtrar los datos del archivo path_a
for chunk in pd.read_csv(path_a, sep=";", usecols=USECOLS, dtype=str, chunksize=CHUNK_SIZE):
    filtered_chunk = chunk[(chunk['CodigoPrestacion'].isin(codigos_de_interes)) & 
                           (chunk['IdRegion'].astype(str) == '13')]
    if filtered_chunk.empty:
        continue
    chunks.append(filtered_chunk)

filtered_data = pd.concat(chunks, ignore_index=True)

#%%
est_dir = Path(r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\ESTABLECIMIENTOS")
candidates = sorted(est_dir.glob("establecimientos_*.csv"))
if not candidates:
    raise FileNotFoundError(f"No se encontró establecimientos_*.csv en {est_dir}")
est_path = candidates[-1]
df_est = pd.read_csv(est_path, dtype=str, sep=";")

filtered_data['IdEstablecimiento'] = (
    pd.to_numeric(filtered_data['IdEstablecimiento'], errors='coerce')
      .astype('Int64')
)

df_est['codigo_establecimiento'] = pd.to_numeric(df_est['EstablecimientoCodigo'], errors='coerce').astype('Int64')
df_est['nombre_ss'] = df_est['SeremiSaludGlosa_ServicioDeSaludGlosa']
df_est['nombre_establecimiento'] = df_est['EstablecimientoGlosa']
df_est['nombre_comuna'] = df_est['ComunaGlosa']
df_est.drop_duplicates(subset=['codigo_establecimiento'], inplace=True)

dict_ss = dict(zip(df_est.codigo_establecimiento, df_est.nombre_ss))
dict_establecimiento = dict(zip(df_est.codigo_establecimiento, df_est.nombre_establecimiento))
dict_comuna = dict(zip(df_est.codigo_establecimiento, df_est.nombre_comuna))

filtered_data['nombre_ss'] = filtered_data.IdEstablecimiento.map(dict_ss)
filtered_data['nombre_establecimiento'] = filtered_data.IdEstablecimiento.map(dict_establecimiento)
filtered_data['nombre_comuna'] = filtered_data.IdEstablecimiento.map(dict_comuna)

# Diagnostico de cruces perdidos
missing_mask = filtered_data['nombre_establecimiento'].isna()
missing_count = int(missing_mask.sum())
total_count = int(len(filtered_data))
if missing_count:
    missing_ids = (
        filtered_data.loc[missing_mask, 'IdEstablecimiento']
        .dropna()
        .astype('Int64')
        .drop_duplicates()
        .sort_values()
    )
    print(
        f"[AVISO] Establecimientos sin cruce: {missing_count} de {total_count} "
        f"({missing_count/total_count:.2%})."
    )
    # Guardar lista para revision
    missing_df = pd.DataFrame({'IdEstablecimiento': missing_ids})
    missing_df.to_csv('output/2025_A24_SECCION_E_establecimientos_sin_cruce.csv', index=False)
#%%
# Filtrar y renombrar las Columnas correspondientes a la sección A24
seccion_a24 = {
    "24200100": "Egresados con lactancia materna exclusiva (código histórico)",
    "24200134": "Total de recién nacidos/as egresados/as",
    "24300103": "RN egresados con LME durante hospitalización y al alta",
    "24311025": "RN egresados que recuperaron LME al alta",
    "24311026": "RN egresados con lactancia mixta al alta",
    "24311027": "RN egresados solo fórmula láctea (excepto VIH/HTLV-1/Ley 21.155/protección)",
    "24311028": "RN egresados solo fórmula por protección o madre grave",
    "29101770": "RN egresados con madres serología positiva (VIH)",
    "29101771": "RN egresados con madres serología positiva (HTLV-1)",
    "29101772": "RN egresados con madres acogidas a Ley 21.155",
}

seccion_a24_Col = {
    'Col01': 'Maternidad',
    'Col02': 'Neonatología',
    'Col03': 'Pueblos originarios',
    'Col04': 'Migrantes',
}

df_a24 = filtered_data[filtered_data['CodigoPrestacion'].isin(seccion_a24.keys())]
df_a24 = df_a24.rename(columns=seccion_a24_Col)

df_a24['CodigoPrestacion'] = df_a24['CodigoPrestacion'].astype(str)
df_a24['descripcion_prestacion'] = df_a24['CodigoPrestacion'].map(seccion_a24)
cols = ['descripcion_prestacion'] + [c for c in df_a24.columns if c != 'descripcion_prestacion']
df_a24 = df_a24[cols]



# Filtrar y renombrar las Columnas correspondientes a la sección REM. A04, SECCIÓN L


columns_to_drop = [Col for Col in df_a24.columns if Col.startswith('Col')]
df_a24 = df_a24.drop(columns=columns_to_drop)


df_a24.to_csv('output/2025_A24_SECCION_E.csv')
df_a24.to_excel('output/2025_A24_SECCION_E.xlsx')
