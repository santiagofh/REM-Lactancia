import pandas as pd
import streamlit as st
from io import BytesIO
from pathlib import Path

st.set_page_config(page_title="REM Lactancia - Explorador", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

SECTIONS = {
    "A03_SECCION_A5": "A03 - Lactancia Exclusiva",
    "A04_SECCION_L": "A04 - Consultas y Consejerías",
    "A24_SECCION_E": "A24 - Egresos Hospitalarios",
}


def list_years() -> list[str]:
    years = sorted(
        {
            p.name.split("_", 1)[0]
            for p in OUTPUT_DIR.glob("*_TABLAS.xlsx")
            if p.name[:4].isdigit()
        },
        reverse=True,
    )
    return years or ["2025", "2024"]


def get_file(year: str, section: str) -> Path:
    return OUTPUT_DIR / f"{year}_{section}_TABLAS.xlsx"


@st.cache_data(show_spinner=False)
def get_sheets(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []
    return pd.ExcelFile(file_path).sheet_names


def _flatten_columns(cols) -> list[str]:
    flat = []
    for c in cols:
        if isinstance(c, tuple):
            parts = []
            for p in c:
                if p is None:
                    continue
                s = str(p)
                if s.lower().startswith("unnamed") or s == "nan":
                    continue
                parts.append(s)
            flat.append(" - ".join(parts).strip() if parts else "")
        else:
            flat.append(str(c))
    return flat


@st.cache_data(show_spinner=False)
def load_sheet(file_path: Path, sheet_name: str, section_key: str, tipo: str | None) -> pd.DataFrame:
    if section_key == "A03_SECCION_A5":
        df = pd.read_excel(file_path, sheet_name=sheet_name, index_col=0)
        return df.reset_index().rename(columns={"index": "Nombre"})

    if section_key == "A04_SECCION_L":
        index_cols = [0, 1] if tipo == "Establecimiento" else [0]
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=[0, 1], index_col=index_cols)
        df = df.reset_index()
        df.columns = _flatten_columns(df.columns)
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name)

    df = df.loc[:, [c for c in df.columns if c and not str(c).lower().startswith("unnamed")]]
    return df.dropna(axis=1, how="all")


@st.cache_data(show_spinner=False)
def load_entities(year: str, section_key: str) -> pd.DataFrame:
    csv_path = OUTPUT_DIR / f"{year}_{section_key}.csv"
    if not csv_path.exists():
        return pd.DataFrame(columns=["ss", "comuna", "est"])

    raw = pd.read_csv(csv_path, dtype=str, low_memory=False)
    cols = {}
    if "nombre_ss" in raw.columns:
        cols["ss"] = "nombre_ss"
    if "nombre_comuna" in raw.columns:
        cols["comuna"] = "nombre_comuna"
    if "nombre_establecimiento" in raw.columns:
        cols["est"] = "nombre_establecimiento"

    if not cols:
        return pd.DataFrame(columns=["ss", "comuna", "est"])

    df = pd.DataFrame()
    for out_col in ["ss", "comuna", "est"]:
        src = cols.get(out_col)
        if src:
            df[out_col] = raw[src].astype(str).str.strip()
        else:
            df[out_col] = ""

    for c in ["ss", "comuna", "est"]:
        df.loc[df[c].str.lower().isin(["", "nan", "none"]), c] = ""
    return df.drop_duplicates()


def split_sheet(name: str) -> tuple[str, str] | None:
    if "_" not in name:
        return None
    return name.rsplit("_", 1)


def normalize_tipo(raw: str) -> str:
    r = raw.strip()
    if r.lower().startswith("establec"):
        return "Establecimiento"
    if r.lower().startswith("comuna"):
        return "Comuna"
    if r.upper() == "SS":
        return "SS"
    return r


def find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def is_ratio_series(series: pd.Series) -> bool:
    s = as_numeric(series).dropna()
    if s.empty:
        return False
    return bool((s.min() >= 0) and (s.max() <= 1.2))


def find_rate_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if "TASA" in str(c).upper() or "%" in str(c)]


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Datos", index=False)
    return buffer.getvalue()


def style_rate_table(df: pd.DataFrame, rate_cols: list[str]):
    cols = [c for c in rate_cols if c in df.columns]
    styler = df.style
    if cols:
        fmt = {c: ("{:.2%}" if is_ratio_series(df[c]) else "{:.2f}%") for c in cols}
        styler = styler.format(fmt, na_rep="-")

        def _style_col(col: pd.Series):
            if col.name in cols:
                return ["font-weight: 700"] * len(col)
            return [""] * len(col)

        styler = styler.apply(_style_col, axis=0)

    return styler.set_table_styles(
        [{"selector": "th", "props": [("font-weight", "700")]}]
    )


def build_maps(entities: pd.DataFrame) -> dict:
    ss_options = sorted([x for x in entities["ss"].unique() if x])
    comuna_options = sorted([x for x in entities["comuna"].unique() if x])
    est_options = sorted([x for x in entities["est"].unique() if x])

    comuna_by_ss = {}
    est_by_ss = {}
    est_by_comuna = {}

    for ss in ss_options:
        comuna_by_ss[ss] = sorted(
            [x for x in entities.loc[entities["ss"] == ss, "comuna"].unique() if x]
        )
        est_by_ss[ss] = sorted(
            [x for x in entities.loc[entities["ss"] == ss, "est"].unique() if x]
        )

    for comuna in comuna_options:
        est_by_comuna[comuna] = sorted(
            [x for x in entities.loc[entities["comuna"] == comuna, "est"].unique() if x]
        )

    est_info = {}
    for est in est_options:
        sub = entities.loc[entities["est"] == est]
        ss_vals = sorted([x for x in sub["ss"].unique() if x])
        com_vals = sorted([x for x in sub["comuna"].unique() if x])
        est_info[est] = {
            "ss": ss_vals[0] if len(ss_vals) == 1 else ("Multiples SS" if ss_vals else ""),
            "comuna": com_vals[0] if len(com_vals) == 1 else ("Multiples comunas" if com_vals else ""),
        }

    comuna_to_ss = {}
    for comuna in comuna_options:
        sub = entities.loc[entities["comuna"] == comuna, "ss"]
        vals = sorted([x for x in sub.unique() if x])
        if len(vals) == 1:
            comuna_to_ss[comuna] = vals[0]

    return {
        "ss_options": ss_options,
        "comuna_options": comuna_options,
        "est_options": est_options,
        "comuna_by_ss": comuna_by_ss,
        "est_by_ss": est_by_ss,
        "est_by_comuna": est_by_comuna,
        "est_info": est_info,
        "comuna_to_ss": comuna_to_ss,
    }


def enrich_df(df: pd.DataFrame, maps: dict) -> pd.DataFrame:
    out = df.copy()
    col_ss = find_col(out, ["Servicio de Salud"])
    col_comuna = find_col(out, ["Comuna"])
    col_est = find_col(out, ["Establecimiento"])

    if col_est and not col_comuna:
        comuna_map = {k: v["comuna"] for k, v in maps["est_info"].items() if v["comuna"]}
        temp = out[col_est].astype(str).map(comuna_map)
        if temp.notna().any():
            out.insert(out.columns.get_loc(col_est) + 1, "Comuna", temp)
            col_comuna = "Comuna"

    if col_comuna and not col_ss:
        temp = out[col_comuna].astype(str).map(maps["comuna_to_ss"])
        if temp.notna().any():
            out.insert(0, "Servicio de Salud", temp)

    return out


st.title("Dashboard REM Lactancia - Explorador")
st.caption("Versión extendida para navegar por red asistencial sin tocar el dashboard principal.")

with st.sidebar:
    st.header("Filtros")
    year = st.selectbox("Año", list_years(), index=0)
    section_label = st.selectbox("Sección", list(SECTIONS.values()))
    section = {v: k for k, v in SECTIONS.items()}[section_label]

file_path = get_file(year, section)
if not file_path.exists():
    st.error(f"No se encontró el archivo esperado: {file_path.name}")
    st.stop()

sheets = get_sheets(file_path)
if not sheets:
    st.warning("El archivo existe, pero no contiene hojas de datos.")
    st.stop()

if section == "A03_SECCION_A5":
    meses = ["1° mes", "3° mes", "6° mes"]
    niveles = ["Servicio", "Comuna", "Establecimiento"]
    meses_ok = [m for m in meses if any(s.endswith(f" {m}") for s in sheets)]
    niveles_ok = [n for n in niveles if any(s.startswith(f"{n} ") for s in sheets)]
    with st.sidebar:
        mes = st.selectbox("Mes", meses_ok)
        nivel = st.selectbox("Desagregación", niveles_ok)
    sheet = f"{nivel} {mes}"
    tipo = nivel
else:
    parsed = [p for p in (split_sheet(s) for s in sheets) if p is not None]
    categorias = sorted({p[0] for p in parsed})
    tipos_raw = {normalize_tipo(p[1]) for p in parsed}
    orden_tipos = [t for t in ["SS", "Comuna", "Establecimiento"] if t in tipos_raw]
    tipos = orden_tipos + [t for t in sorted(tipos_raw) if t not in orden_tipos]
    with st.sidebar:
        categoria = st.selectbox("Categoría", categorias)
        tipo = st.selectbox("Desagregación", tipos)

    posibles = []
    for s in sheets:
        sp = split_sheet(s)
        if sp is None:
            continue
        cat, raw_tipo = sp
        if cat == categoria and normalize_tipo(raw_tipo) == tipo:
            posibles.append(s)
    sheet = posibles[0] if posibles else f"{categoria}_{tipo}"
    if sheet not in sheets:
        st.warning("La combinación elegida no existe en el archivo.")
        st.stop()

df = load_sheet(file_path, sheet, section, tipo)

if section == "A03_SECCION_A5" and "Nombre" in df.columns:
    label_map = {"Servicio": "Servicio de Salud", "Comuna": "Comuna", "Establecimiento": "Establecimiento"}
    if tipo in label_map:
        df = df.rename(columns={"Nombre": label_map[tipo]})

entities = load_entities(year, section)
maps = build_maps(entities)
df = enrich_df(df, maps)

col_ss = find_col(df, ["Servicio de Salud"])
col_comuna = find_col(df, ["Comuna"])
col_est = find_col(df, ["Establecimiento"])

with st.sidebar:
    st.markdown("---")
    mode = st.radio("Modo de navegación", ["Explorar red", "Búsqueda directa"], index=0)

df_view = df.copy()
selected_ss = "(Todos)"
selected_comuna = "(Todos)"
selected_est = "(Todos)"

if mode == "Explorar red":
    with st.sidebar:
        ss_options = ["(Todos)"] + maps["ss_options"]
        selected_ss = st.selectbox("Servicio de Salud", ss_options, index=0)

        if selected_ss != "(Todos)":
            comuna_base = maps["comuna_by_ss"].get(selected_ss, [])
        else:
            comuna_base = maps["comuna_options"]
        selected_comuna = st.selectbox("Comuna", ["(Todos)"] + comuna_base, index=0)

        if selected_comuna != "(Todos)":
            est_base = maps["est_by_comuna"].get(selected_comuna, [])
        elif selected_ss != "(Todos)":
            est_base = maps["est_by_ss"].get(selected_ss, [])
        else:
            est_base = maps["est_options"]
        selected_est = st.selectbox("Establecimiento", ["(Todos)"] + est_base, index=0)

    if selected_ss != "(Todos)":
        if col_ss:
            df_view = df_view[df_view[col_ss].astype(str) == selected_ss]
        elif col_comuna:
            allowed_comunas = set(maps["comuna_by_ss"].get(selected_ss, []))
            df_view = df_view[df_view[col_comuna].astype(str).isin(allowed_comunas)]
        elif col_est:
            allowed_est = set(maps["est_by_ss"].get(selected_ss, []))
            df_view = df_view[df_view[col_est].astype(str).isin(allowed_est)]

    if selected_comuna != "(Todos)":
        if col_comuna:
            df_view = df_view[df_view[col_comuna].astype(str) == selected_comuna]
        elif col_est:
            allowed_est = set(maps["est_by_comuna"].get(selected_comuna, []))
            df_view = df_view[df_view[col_est].astype(str).isin(allowed_est)]

    if selected_est != "(Todos)" and col_est:
        df_view = df_view[df_view[col_est].astype(str) == selected_est]

else:
    with st.sidebar:
        search_scope = st.selectbox("Buscar en", ["Todo", "Servicio de Salud", "Comuna", "Establecimiento"], index=0)
        q = st.text_input("Texto a buscar")

    if q:
        q = q.strip()
        if search_scope == "Servicio de Salud" and col_ss:
            df_view = df_view[df_view[col_ss].astype(str).str.contains(q, case=False, na=False)]
        elif search_scope == "Comuna" and col_comuna:
            df_view = df_view[df_view[col_comuna].astype(str).str.contains(q, case=False, na=False)]
        elif search_scope == "Establecimiento" and col_est:
            df_view = df_view[df_view[col_est].astype(str).str.contains(q, case=False, na=False)]
        else:
            mask = pd.Series(False, index=df_view.index)
            for c in [col_ss, col_comuna, col_est]:
                if c:
                    mask = mask | df_view[c].astype(str).str.contains(q, case=False, na=False)
            df_view = df_view[mask]

        if col_est and search_scope in ["Todo", "Establecimiento"]:
            est_matches = sorted(
                {e for e in maps["est_options"] if q.lower() in e.lower()}
            )
            if len(est_matches) == 1:
                info = maps["est_info"].get(est_matches[0], {})
                st.info(
                    f"Establecimiento: {est_matches[0]} | Comuna: {info.get('comuna', '-')}"
                    f" | Servicio: {info.get('ss', '-')}"
                )

if selected_est != "(Todos)":
    info = maps["est_info"].get(selected_est, {})
    st.info(
        f"Establecimiento seleccionado: {selected_est} | "
        f"Comuna: {info.get('comuna', '-')} | Servicio: {info.get('ss', '-')}"
    )

st.subheader(f"{year} · {section_label}")
st.caption(f"Vista activa: {sheet}")

rate_cols = find_rate_cols(df_view)
if rate_cols:
    st.dataframe(style_rate_table(df_view, rate_cols), use_container_width=True, height=620)
else:
    st.dataframe(style_rate_table(df_view, []), use_container_width=True, height=620)

st.caption(f"Filas mostradas: {len(df_view):,} de {len(df):,}")

excel_bytes = dataframe_to_excel_bytes(df_view)
st.download_button(
    label="Descargar vista en Excel",
    data=excel_bytes,
    file_name=f"{year}_{section}_{sheet}_explorador.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
