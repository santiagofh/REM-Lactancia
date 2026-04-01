import pandas as pd
from pathlib import Path

# ------------------------------------------------------------------
# 1. Rutas de entrada / salida
# ------------------------------------------------------------------
csv_path = Path("output/2025_A24_SECCION_E.csv")
excel_out = Path("output/2025_A24_SECCION_E_TABLAS.xlsx")

# ------------------------------------------------------------------
# 2. Etiquetas y columnas
# ------------------------------------------------------------------
TOTAL_LABEL = "Total de recién nacidos/as egresados/as"
LME_HIST_LABEL = "Egresados con lactancia materna exclusiva (código histórico)"
LME_STRICT_LABEL = "RN egresados con LME durante hospitalización y al alta"
LME_RECUP_LABEL = "RN egresados que recuperaron LME al alta"
MIXTA_LABEL = "RN egresados con lactancia mixta al alta"
FORMULA_GENERAL_LABEL = "RN egresados solo fórmula láctea (excepto VIH/HTLV-1/Ley 21.155/protección)"
FORMULA_PROT_LABEL = "RN egresados solo fórmula por protección o madre grave"
VIH_LABEL = "RN egresados con madres serología positiva (VIH)"
HTLV_LABEL = "RN egresados con madres serología positiva (HTLV-1)"
LEY_LABEL = "RN egresados con madres acogidas a Ley 21.155"

SOURCE_COLS = [
    TOTAL_LABEL,
    LME_HIST_LABEL,
    LME_STRICT_LABEL,
    LME_RECUP_LABEL,
    MIXTA_LABEL,
    FORMULA_GENERAL_LABEL,
    FORMULA_PROT_LABEL,
    VIH_LABEL,
    HTLV_LABEL,
    LEY_LABEL,
]

DISPLAY_COLS = [
    TOTAL_LABEL,
    "LME estricta",
    "LME recuperada al alta",
    "LME al alta (estricta + recuperada)",
    MIXTA_LABEL,
    FORMULA_GENERAL_LABEL,
    FORMULA_PROT_LABEL,
    VIH_LABEL,
    HTLV_LABEL,
    LEY_LABEL,
    "% Lactancia Exclusiva",
    "% LME al alta (incluye recuperada)",
]

# Orden deseado de Servicios de Salud
ORDEN_SS = [
    "Región Metropolitana",
    "Servicio de Salud Metropolitano Norte",
    "Servicio de Salud Metropolitano Occidente",
    "Servicio de Salud Metropolitano Central",
    "Servicio de Salud Metropolitano Oriente",
    "Servicio de Salud Metropolitano Sur",
    "Servicio de Salud Metropolitano Sur Oriente",
]

# ------------------------------------------------------------------
# 3. Cargar datos
# ------------------------------------------------------------------
df = pd.read_csv(csv_path, dtype=str)
for col in ["Maternidad", "Neonatología"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")


def tabla_dinamica(
    df_src: pd.DataFrame,
    col_val: str,
    indice: str,
    orden_prioritario: list | None = None,
) -> pd.DataFrame:
    tabla = df_src.pivot_table(
        index=indice,
        columns="descripcion_prestacion",
        values=col_val,
        aggfunc="sum",
        fill_value=0,
    )

    tabla.loc["Región Metropolitana"] = tabla.sum(numeric_only=True)

    for col in SOURCE_COLS:
        if col not in tabla.columns:
            tabla[col] = 0

    # En 2024 el código histórico (24200100) ya contiene 24300103.
    # Para evitar doble conteo: usar histórico cuando existe; si no, usar 24300103.
    tabla["LME estricta"] = tabla[LME_HIST_LABEL].where(
        tabla[LME_HIST_LABEL] > 0,
        tabla[LME_STRICT_LABEL],
    )
    tabla["LME recuperada al alta"] = tabla[LME_RECUP_LABEL]
    tabla["LME al alta (estricta + recuperada)"] = (
        tabla["LME estricta"] + tabla["LME recuperada al alta"]
    )

    total = tabla[TOTAL_LABEL].replace({0: pd.NA})
    tabla["% Lactancia Exclusiva"] = tabla["LME estricta"] / total
    tabla["% LME al alta (incluye recuperada)"] = (
        tabla["LME al alta (estricta + recuperada)"] / total
    )

    if orden_prioritario:
        orden_filas = (
            ["Región Metropolitana"]
            + [x for x in orden_prioritario if x in tabla.index and x != "Región Metropolitana"]
            + [x for x in tabla.index if x not in orden_prioritario]
        )
    else:
        otras = sorted([x for x in tabla.index if x != "Región Metropolitana"])
        orden_filas = ["Región Metropolitana"] + otras

    tabla = tabla.loc[orden_filas]
    return tabla[DISPLAY_COLS]


# ------------------------------------------------------------------
# 4. Generar tablas
# ------------------------------------------------------------------
pivot_mat_ss = tabla_dinamica(df, "Maternidad", "nombre_ss", ORDEN_SS)
pivot_neo_ss = tabla_dinamica(df, "Neonatología", "nombre_ss", ORDEN_SS)
pivot_mat_com = tabla_dinamica(df, "Maternidad", "nombre_comuna")
pivot_neo_com = tabla_dinamica(df, "Neonatología", "nombre_comuna")
pivot_mat_est = tabla_dinamica(df, "Maternidad", "nombre_establecimiento")
pivot_neo_est = tabla_dinamica(df, "Neonatología", "nombre_establecimiento")

# ------------------------------------------------------------------
# 5. Exportar a Excel con formato %
# ------------------------------------------------------------------
with pd.ExcelWriter(excel_out, engine="xlsxwriter") as writer:
    pivot_mat_ss.to_excel(writer, sheet_name="Maternidad_SS")
    pivot_neo_ss.to_excel(writer, sheet_name="Neonatologia_SS")
    pivot_mat_com.to_excel(writer, sheet_name="Maternidad_Comuna")
    pivot_neo_com.to_excel(writer, sheet_name="Neonatologia_Comuna")
    pivot_mat_est.to_excel(writer, sheet_name="Maternidad_Establecimiento")
    pivot_neo_est.to_excel(writer, sheet_name="Neonatologia_Establecimiento")

    fmt_pct = writer.book.add_format({"num_format": "0.0%"})
    hojas = {
        "Maternidad_SS": pivot_mat_ss,
        "Neonatologia_SS": pivot_neo_ss,
        "Maternidad_Comuna": pivot_mat_com,
        "Neonatologia_Comuna": pivot_neo_com,
        "Maternidad_Establecimiento": pivot_mat_est,
        "Neonatologia_Establecimiento": pivot_neo_est,
    }
    for sheet_name, tabla in hojas.items():
        ws = writer.sheets[sheet_name]
        for col_name in [c for c in tabla.columns if c.startswith("%")]:
            pct_idx = tabla.columns.get_loc(col_name) + 1  # +1 por índice Excel
            ws.set_column(pct_idx, pct_idx, 16, fmt_pct)

print(f"Archivo Excel creado en: {excel_out.resolve()}")
