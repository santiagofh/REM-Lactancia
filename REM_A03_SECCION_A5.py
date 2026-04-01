#%%
import pandas as pd
import csv
import re
import locale
from pathlib import Path
locale.setlocale(locale.LC_COLLATE, 'es_ES.UTF-8')  # para sistemas Linux/Mac
# locale.setlocale(locale.LC_COLLATE, 'Spanish_Spain.1252')  # para Windows

#%%
DIC_CODIGO_COMUNAS={
'13502':'Alhué',
'13402':'Buin',
'13403':'Calera de Tango',
'13102':'Cerrillos',
'13103':'Cerro Navia',
'13301':'Colina',
'13104':'Conchalí',
'13503':'Curacaví',
'13105':'El Bosque',
'13602':'El Monte',
'13106':'Estación Central',
'13107':'Huechuraba',
'13108':'Independencia',
'13603':'Isla de Maipo',
'13109':'La Cisterna',
'13110':'La Florida',
'13111':'La Granja',
'13112':'La Pintana',
'13113':'La Reina',
'13302':'Lampa',
'13114':'Las Condes',
'13115':'Lo Barnechea',
'13116':'Lo Espejo',
'13117':'Lo Prado',
'13118':'Macul',
'13119':'Maipú',
'13504':'Maria Pinto',
'13501':'Melipilla',
'13120':'Ñuñoa',
'13604':'Padre Hurtado',
'13404':'Paine',
'13121':'Pedro Aguirre Cerda',
'13605':'Peñaflor',
'13122':'Peñalolén',
'13202':'Pirque',
'13123':'Providencia',
'13124':'Pudahuel',
'13201':'Puente Alto',
'13125':'Quilicura',
'13126':'Quinta Normal',
'13127':'Recoleta',
'13128':'Renca',
'13401':'San Bernardo',
'13129':'San Joaquín',
'13203':'San José de Maipo',
'13130':'San Miguel',
'13505':'San Pedro',
'13131':'San Ramón',
'13101':'Santiago',
'13601':'Talagante',
'13303':'Tiltil',
'13132':'Vitacura',
}

CODIGOS_DE_INTERES = ["A0200001", "A0200002"]

PATHS = [
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2025\Datos\SerieA2025.csv",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2024\Datos\SerieA2024.csv",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2023\Datos\SerieA2023.txt",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2022\SerieA.txt",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2021\2021\SerieA_2021.txt",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2020\SerieA_2020.txt",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2019\SerieA_2019.txt",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2018\SerieA_txt.txt",
    r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2017\SerieA_txt.txt",
    # r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2016\SERIE_REM_2016\SerieA.txt",
    # r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2015\SERIE_REM_2015\SerieA.txt",
    # r"C:\Users\fariass\OneDrive - SUBSECRETARIA DE SALUD PUBLICA\Escritorio\DATA\REM\REM_2014\SERIE_REM_2014\SerieA2014.csv",
]
#%%
# ----------------------------------------------------------------------
# 2. Función para extraer el año y crear el diccionario {año: ruta}
# ----------------------------------------------------------------------
def paths_por_anno(paths) -> dict[int, Path]:
    """
    Convierte la lista de rutas en un diccionario cuya key es el año (int)
    y el value es la ruta (Path).
    """
    paths_dict = {}
    for p in paths:
        p = Path(p)
        # Busca el primer “2024”, “2023”… que aparezca en la ruta
        m = re.search(r'(?<!\d)(20\d{2})(?!\d)', str(p))
        if not m:
            raise ValueError(f"No se pudo extraer un año de: {p}")
        anno = int(m.group(1))
        paths_dict[anno] = p
    return paths_dict

FILES = paths_por_anno(PATHS)        # {2024: Path(...), 2023: Path(...), …}
#%%
# ----------------------------------------------------------------------
# 3. Función para detectar el separador leyendo *solo* la primera línea
# ----------------------------------------------------------------------
def detectar_sep(path: Path) -> str:
    """
    Lee la primera línea del archivo y trata de identificar su separador.
    Usa csv.Sniffer si es posible; si no, aplica una heurística sencilla.
    """
    with path.open('rb') as fh:
        first_line = fh.readline().decode('latin-1', errors='replace')
    
    try:
        dialect = csv.Sniffer().sniff(first_line)
        return dialect.delimiter
    except csv.Error:
        # Heurística de reserva.
        if first_line.count(';') >= first_line.count(',') and ';' in first_line:
            return ';'
        elif ',' in first_line:
            return ','
        elif '\t' in first_line:
            return '\t'
        else:
            return '|'          # último recurso: “pipe”
#%% 
# ----------------------------------------------------------------------
# 4. Loop principal: lee cada archivo con su separador y concatena
# ----------------------------------------------------------------------
frames = []
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

for anno, path in sorted(FILES.items()):          # orden cronológico
    sep = detectar_sep(path)
    print(f"Leyendo {path.name} ({anno}) con separador '{sep}'…")

    # Algunos años vienen sin la columna Mes en el archivo base.
    header_cols = pd.read_csv(
        path,
        sep=sep,
        dtype=str,
        encoding='latin-1',
        nrows=0,
        low_memory=False,
    ).columns.tolist()
    usecols_disponibles = [c for c in USECOLS if c in header_cols]

    # Leer por chunks para reducir RAM
    for chunk in pd.read_csv(
        path,
        sep=sep,
        dtype=str,              # evita inferencias erróneas
        encoding='latin-1',     # o 'utf-8-sig' si tus CSV vienen en UTF-8
        usecols=usecols_disponibles,
        low_memory=False,
        chunksize=CHUNK_SIZE,
    ):
        for c in ["Mes", "Col04", "Col05", "Col06"]:
            if c not in chunk.columns:
                chunk[c] = pd.NA
        # Filtra: códigos de interés y Región Metropolitana (IdRegion == 13)
        chunk = chunk[
            chunk['CodigoPrestacion'].isin(CODIGOS_DE_INTERES) &
            (chunk['IdRegion'].astype(str) == '13')
        ]
        if chunk.empty:
            continue
        chunk['Ano'] = anno                       # etiqueta el año
        frames.append(chunk)

# DataFrame final con todos los años
df = pd.concat(frames, ignore_index=True)
#%%
# ----------------------------------------------------------------------
# 5. Asignación de nombre_ss, nombre_establecimiento y nombre_comuna
# ----------------------------------------------------------------------
df['IdEstablecimiento'] = (
    pd.to_numeric(df['IdEstablecimiento'], errors='coerce')
      .astype('Int64')
)

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
df['nombre_comuna']=df.IdComuna.map(DIC_CODIGO_COMUNAS)

#%%
# ----------------------------------------------------------------------
# 6. Filtrar y asignar 
# ----------------------------------------------------------------------
DIC_PRESTACION = {
    "A0200001": 'MENORES CONTROLADOS',
    "A0200002": 'LACTANCIA MATERNA EXCLUSIVA',
}

DIC_COLUMNAS_A3 = {
    # Según diccionario A03:
    # Col04=1° mes, Col05=3° mes, Col06=6° mes
    'Col04': '1° mes',
    'Col05': '3° mes',
    'Col06': '6° mes'
}

COLUMNAS=[
    "Ano",
    "Mes",
    "IdServicio",
    "nombre_ss",
    "IdEstablecimiento",
    "nombre_establecimiento",
    "IdRegion",
    "IdComuna",
    "nombre_comuna",
    "CodigoPrestacion",
    "Prestación",
    "1° mes",
    "3° mes",
    "6° mes",
]
df = df.rename(columns=DIC_COLUMNAS_A3)
df['Prestación'] = df['CodigoPrestacion'].map(DIC_PRESTACION)
df_export=df[COLUMNAS]
# ------------------------------------------------------------------
# 6-bis. Forzar dtype entero en columnas clave
# ------------------------------------------------------------------
COLS_INT = [
    "Ano", "Mes", "IdServicio", "IdEstablecimiento",
    "IdRegion", "IdComuna", "1° mes", "3° mes", "6° mes",
]

for c in COLS_INT:
    # • pd.to_numeric convierte strings a número.
    # • errors='coerce' => si encuentra algo no numérico lo convierte en NaN.
    # • astype('Int64') da el tipo entero *nullable* de pandas (acepta NaN).
    df[c] = (
        pd.to_numeric(df[c], errors="coerce")   # ⇢  números o NaN
          .astype("Int64")                      # ⇢  enteros (nullable)
    )

# Ahora ya puedes re-crear df_export con la certeza
# de que esas columnas son int:
df_export = df[COLUMNAS]
# %%
# ----------------------------------------------------------------------
# 7. Exportar a EXCEL y CSV 
# ----------------------------------------------------------------------

df_export.to_csv('output/2017-2025_A03_SECCION_A5.csv')
df_export.to_excel('output/2017-2025_A03_SECCION_A5.xlsx')
# %%
