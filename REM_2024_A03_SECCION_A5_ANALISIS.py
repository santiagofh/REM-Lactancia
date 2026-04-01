# %%
import pandas as pd
import locale

# Ajustar colación a español para que las comunas queden bien ordenadas
try:
    locale.setlocale(locale.LC_COLLATE, 'es_ES.UTF-8')
except locale.Error:
    pass

df = pd.read_csv("output/2024_A03_SECCION_A5.csv")

ORDEN_SS = [
    'Región Metropolitana',
    'Servicio de Salud Metropolitano Norte',
    'Servicio de Salud Metropolitano Occidente',
    'Servicio de Salud Metropolitano Central',
    'Servicio de Salud Metropolitano Oriente',
    'Servicio de Salud Metropolitano Sur',
    'Servicio de Salud Metropolitano Sur Oriente',
]

def tabla_lme(
    df: pd.DataFrame,
    mes_col: str,
    group_col: str,
    orden_filas: list[str] | None = None
) -> pd.DataFrame:
    """
    Construye la tabla de lactancia materna exclusiva para un mes dado y una
    columna de agrupación (Servicio de Salud o comuna).

    Parameters
    ----------
    df : DataFrame con todas las prestaciones.
    mes_col : '1° mes', '3° mes', '6° mes', …
    group_col : 'nombre_ss'  o 'nombre_comuna'.
    orden_filas : lista opcional para reindexar; si es None se ordena alfabético.

    Returns
    -------
    DataFrame con totales y tasa (%).
    """
    df_excl = df[df['Prestación'].str.strip().str.upper() == 'LACTANCIA MATERNA EXCLUSIVA']
    df_ctrl = df[df['Prestación'].str.strip().str.upper() == 'MENORES CONTROLADOS']

    excl_por_g = (df_excl.groupby(group_col, as_index=True)[mes_col]
                         .sum()
                         .rename('CON LACTANCIA MATERNA EXCLUSIVA'))

    ctrl_por_g = (df_ctrl.groupby(group_col, as_index=True)[mes_col]
                         .sum()
                         .rename('TOTAL NIÑOS CONTROLADOS'))

    tabla = pd.concat([excl_por_g, ctrl_por_g], axis=1)
    tabla.loc['Región Metropolitana'] = tabla.sum(numeric_only=True)

    tabla['TASA LACTANCIA MATERNA EXCLUSIVA'] = (
        tabla['CON LACTANCIA MATERNA EXCLUSIVA'] /
        tabla['TOTAL NIÑOS CONTROLADOS'] * 100
    )

    if orden_filas is not None:
        # Reindexa según lista explícita
        tabla = tabla.reindex(orden_filas)
    else:
        # Orden alfabético natural según locale
        tabla = tabla.loc[sorted(tabla.index, key=locale.strxfrm)]

        # Asegurarse de que la fila de totales quede arriba
        if 'Región Metropolitana' in tabla.index:
            tabla = pd.concat([tabla.loc[['Región Metropolitana']],
                               tabla.drop('Región Metropolitana')])

    return tabla


# %% ----------- GENERAR TODAS LAS TABLAS QUE NECESITAS ----------------
tablas_por_mes_y_nivel = {}

for mes in ['1° mes', '3° mes', '6° mes']:
    tablas_por_mes_y_nivel[f'Servicio {mes}'] = tabla_lme(df, mes, 'nombre_ss', ORDEN_SS)
    tablas_por_mes_y_nivel[f'Comuna {mes}'] = tabla_lme(df, mes, 'nombre_comuna')
    tablas_por_mes_y_nivel[f'Establecimiento {mes}'] = tabla_lme(df, mes, 'nombre_establecimiento')


# %% ---- Si quieres exportar a Excel en pestañas separadas -------------
with pd.ExcelWriter('output/2024_A03_SECCION_A5_TABLAS.xlsx') as writer:
    for nombre, t in tablas_por_mes_y_nivel.items():
        t.to_excel(writer, sheet_name=nombre[:31])     # Excel ≤31 caracteres

# %%
