import pandas as pd
import locale

# Ajustar colación a español
try:
    locale.setlocale(locale.LC_COLLATE, 'es_ES.UTF-8')
except locale.Error:
    pass

# Cargar archivo
df_a04_l = pd.read_csv("output/2024_A04_SECCION_L.csv")

# Filtrar consultas por profesional
df_profesionales = df_a04_l[df_a04_l['descripcion_prestacion'].str.contains("Consulta de Lactancia por profesional", na=False)]

# Columnas de interés
columnas_interes = [
    "De 0 a 29 días", "De 1 mes a 2 meses 29 días", "De 3 meses a 5 meses 29 días",
    "De 6 meses a 11 meses 29 días", "De 1 a 2 años", "Gestantes", "Pueblos Originarios", "Migrantes"
]

# Agrupaciones
agrupaciones = {
    "SS": "nombre_ss",
    "Comuna": "nombre_comuna",
    "Establecimiento": "nombre_establecimiento"
}

# Diccionario de reemplazo de columnas
renombres = {
    "Consulta de Lactancia por profesional  - Enfermera/o": "Enfermera/o",
    "Consulta de Lactancia por profesional  - Matrona/ón": "Matrona/ón",
    "Consulta de Lactancia por profesional  - Médico/a": "Médico/a",
    "Consulta de Lactancia por profesional  - Nutricionista ": "Nutricionista"
}

tablas_por_categoria = {}

for tipo, agrupador in agrupaciones.items():
    for categoria in columnas_interes:
        if tipo == "Establecimiento":
            df_categoria = df_profesionales[[agrupaciones["Comuna"], agrupador, "descripcion_prestacion", categoria]].copy()
            df_categoria = df_categoria.dropna(subset=[categoria])
            df_categoria["comuna_estab"] = list(zip(df_categoria[agrupaciones["Comuna"]], df_categoria[agrupador]))

            tabla_pivot = df_categoria.pivot_table(
                index="comuna_estab",
                columns="descripcion_prestacion",
                values=categoria,
                aggfunc="sum",
                fill_value=0
            )
            tabla_pivot.index = pd.MultiIndex.from_tuples(tabla_pivot.index, names=["Comuna", "Establecimiento"])
        else:
            df_categoria = df_profesionales[[agrupador, "descripcion_prestacion", categoria]].copy()
            df_categoria = df_categoria.dropna(subset=[categoria])
            tabla_pivot = df_categoria.pivot_table(
                index=agrupador,
                columns="descripcion_prestacion",
                values=categoria,
                aggfunc="sum",
                fill_value=0
            )

        # Renombrar columnas según diccionario
        tabla_pivot = tabla_pivot.rename(columns=renombres)

        # Crear MultiIndex con encabezado general
        tabla_pivot.columns = pd.MultiIndex.from_product(
            [["Consulta de Lactancia por profesional"], tabla_pivot.columns]
        )

        nombre_hoja = f"{categoria[:20]}_{tipo}"
        tablas_por_categoria[nombre_hoja] = tabla_pivot

# Exportar a Excel
with pd.ExcelWriter("output/2024_A04_SECCION_L_TABLAS.xlsx") as writer:
    for nombre_hoja, tabla in tablas_por_categoria.items():
        tabla.to_excel(writer, sheet_name=nombre_hoja[:31])

print("Archivo Excel exportado con éxito.")
