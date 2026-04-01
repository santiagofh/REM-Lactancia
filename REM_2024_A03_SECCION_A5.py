#%%
import os
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

path_a =r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2024\Datos\SerieA2024.csv"
df = pd.DataFrame()
df = pd.read_csv(path_a, sep=";")
df = df[(df['CodigoPrestacion'].isin(codigos_de_interes)) & 
                        (df['IdRegion'] == 13)]
#%%
df_deis=pd.read_excel('data_DEIS/Establecimientos DEIS MINSAL 07-01-2025 (2).xlsx',
                 sheet_name='BASE_ESTABLECIMIENTO_2025-01-07')

df_deis['codigo_establecimiento']=df_deis['Código Vigente']
df_deis['nombre_ss']=df_deis['Nombre Dependencia Jerárquica (SEREMI / Servicio de Salud)']
df_deis['nombre_establecimiento']=df_deis['Nombre Oficial']
df_deis['nombre_comuna']=df_deis['Nombre Comuna']

ls_codigo_ss=list(df_deis.codigo_establecimiento)
ls_nombre_ss=list(df_deis.nombre_ss)
ls_codigo_est=list(df_deis.codigo_establecimiento)
ls_nombre_est=list(df_deis.nombre_establecimiento)
ls_codigo_comuna=list(df_deis.codigo_establecimiento)
ls_nombre_comuna=list(df_deis.nombre_comuna)

dict_comuna= dict(zip(ls_codigo_ss, ls_nombre_comuna))
dict_ss = dict(zip(ls_codigo_ss, ls_nombre_ss))
dict_establecimiento= dict(zip(ls_codigo_ss, ls_nombre_est))

df['nombre_ss']=df.IdEstablecimiento.map(dict_ss)
df['nombre_establecimiento']=df.IdEstablecimiento.map(dict_establecimiento)
df['nombre_comuna']=df.IdEstablecimiento.map(dict_comuna)

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
        'output/2024_A03_SECCION_A5_establecimientos_sin_cruce.csv',
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
df_a3.to_csv('output/2024_A03_SECCION_A5.csv')
df_a3.to_excel('output/2024_A03_SECCION_A5.xlsx')
# %%
