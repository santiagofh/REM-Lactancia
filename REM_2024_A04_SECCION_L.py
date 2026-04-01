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
"04040420",
"04040421",
"09600287",
"09600288",
"09600289",
"04040423",
"04040424",
"04040425",
"04040426",

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
        'output/2024_A04_SECCION_L_establecimientos_sin_cruce.csv',
        index=False
    )
#%%

# Filtrar y renombrar las Columnas correspondientes a la sección a04_l
seccion_a04_l = {
"04040420":"Consulta de Lactancia - Consulta Lactancia Materna de alerta",
"04040421":"Consulta de Lactancia - Consulta de Lactancia Materna de seguimiento",
"09600287":"Consulta de Lactancia - Otras consultas de Lactancia Materna",
"09600288":"Consejería de Lactancia - Consejería prenatal en Lactancia Materna",
"09600289":"Consejería de Lactancia - Consejería posnatal en Lactancia Materna",
"04040423":"Consulta de Lactancia por profesional  - Médico/a",
"04040424":"Consulta de Lactancia por profesional  - Matrona/ón",
"04040425":"Consulta de Lactancia por profesional  - Enfermera/o",
"04040426":"Consulta de Lactancia por profesional  - Nutricionista ",
}


seccion_a04_l_Col = {
    "Col01": "TOTAL",
    "Col02": "De 0 a 29 días",
    "Col03": "De 1 mes a 2 meses 29 días",
    "Col04": "De 3 meses a 5 meses 29 días",
    "Col05": "De 6 meses a 11 meses 29 días",
    "Col06": "De 1 a 2 años",
    "Col07": "Gestantes",
    "Col08": "Pueblos Originarios",
    "Col09": "Migrantes"
}


df_a04_l = df[df['CodigoPrestacion'].isin(seccion_a04_l.keys())]
df_a04_l = df_a04_l.rename(columns=seccion_a04_l_Col)
df_a04_l['CodigoPrestacion'] = df_a04_l['CodigoPrestacion'].astype(str)
df_a04_l['descripcion_prestacion'] = df_a04_l['CodigoPrestacion'].map(seccion_a04_l)
cols = ['descripcion_prestacion'] + [c for c in df_a04_l.columns if c != 'descripcion_prestacion']
df_a04_l = df_a04_l[cols]



columns_to_drop = [Col for Col in df_a04_l.columns if Col.startswith('Col')]
df_a04_l = df_a04_l.drop(columns=columns_to_drop)

df_a04_l.to_csv('output/2024_A04_SECCION_L.csv')
df_a04_l.to_excel('output/2024_A04_SECCION_L.xlsx')


# %%
