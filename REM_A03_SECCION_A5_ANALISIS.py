# ==========================================================================
# Tablas dinámicas de lactancia (1°, 3° y 6° mes) por Año y Comuna
# ==========================================================================

import pandas as pd
from pathlib import Path

# --------------------------------------------------------------------------
# 1. Cargar el archivo fuente
# --------------------------------------------------------------------------
CSV_IN = Path("output/2017-2025_A03_SECCION_A5.csv")
df = pd.read_csv(CSV_IN, dtype=str)

# --------------------------------------------------------------------------
# 2. Asegurar columnas numéricas
# --------------------------------------------------------------------------
NUM_COLS = ["1° mes", "3° mes", "6° mes"]

for col in NUM_COLS:
    df[col] = (
        pd.to_numeric(df[col], errors="coerce")
          .fillna(0)
          .astype("Int64")
    )

# --------------------------------------------------------------------------
# 3. Función para crear la tabla dinámica de un mes
# --------------------------------------------------------------------------
def pivot_lme(df: pd.DataFrame, month_col: str) -> pd.DataFrame:
    df_subset = df[df["Prestación"].str.strip().str.upper().isin(
        ["MENORES CONTROLADOS", "LACTANCIA MATERNA EXCLUSIVA"]
    )]

    grouped = (
        df_subset.groupby(["Ano", "nombre_comuna", "Prestación"], as_index=False)[month_col]
        .sum()
    )

    tabla = (
        grouped
        .pivot_table(
            index=["Ano", "nombre_comuna"],
            columns="Prestación",
            values=month_col,
            aggfunc="sum",
            fill_value=0
        )
        .rename(columns={
            "MENORES CONTROLADOS": "TOTAL_LACTANTES_CONTROLADOS",
            "LACTANCIA MATERNA EXCLUSIVA": "CON_LME",
        })
        .reset_index()
    )

    tabla = tabla[["Ano", "nombre_comuna",
                   "TOTAL_LACTANTES_CONTROLADOS", "CON_LME"]]

    # Agregar columna TASA (%)
    tabla["TASA_LME"] = (
        tabla["CON_LME"] / tabla["TOTAL_LACTANTES_CONTROLADOS"] * 100
    ).round(2)

    # Calcular totales por año
    totales = (
        tabla.groupby("Ano", as_index=False)[
            ["TOTAL_LACTANTES_CONTROLADOS", "CON_LME"]
        ].sum()
    )
    totales["nombre_comuna"] = "Total Región Metropolitana"
    totales["TASA_LME"] = (
        totales["CON_LME"] / totales["TOTAL_LACTANTES_CONTROLADOS"] * 100
    ).round(2)

    # Reordenar para que el total quede primero por año
    tabla = pd.concat([totales, tabla], ignore_index=True)

    return tabla

# --------------------------------------------------------------------------
# 4. Generar las tres tablas (1°, 3° y 6° mes)
# --------------------------------------------------------------------------
MESES = {
    "1° mes": "Mes_1",
    "3° mes": "Mes_3",
    "6° mes": "Mes_6",
}

tablas = {nombre_hoja: pivot_lme(df, col) for col, nombre_hoja in MESES.items()}

# --------------------------------------------------------------------------
# 5. Exportar a un único Excel con tres hojas
# --------------------------------------------------------------------------
EXCEL_OUT = Path("output/2017-2025_A03_SECCION_A5_TABLAS.xlsx")

with pd.ExcelWriter(EXCEL_OUT, engine="xlsxwriter") as writer:
    for sheet_name, tabla in tablas.items():
        tabla.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Archivo generado: {EXCEL_OUT.resolve()}")
