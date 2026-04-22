from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_DEIS_PATH = BASE_DIR / "data_DEIS" / "20250424_est_deis.csv"

SECTIONS = {
    "A03_SECCION_A5": "A03 - Lactancia Exclusiva",
    "A04_SECCION_L": "A04 - Consultas y Consejerías",
    "A24_SECCION_E": "A24 - Egresos Hospitalarios",
}


def list_years() -> list[str]:
    years = []
    for p in OUTPUT_DIR.glob("*_TABLAS.xlsx"):
        token = p.name.split("_", 1)[0]
        if token.isdigit() and len(token) == 4:
            years.append(token)
    years = sorted(set(years), reverse=True)
    return years or ["2025", "2024"]


@st.cache_data(show_spinner=False)
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
    df = df.rename(
        columns={
            "nombre_ss": "Servicio de Salud",
            "nombre_comuna": "Comuna",
            "nombre_establecimiento": "Establecimiento",
            "Servicio de Salud -": "Servicio de Salud",
            "Comuna -": "Comuna",
            "Establecimiento -": "Establecimiento",
        }
    )
    return df.dropna(axis=1, how="all")


@st.cache_data(show_spinner=False)
def load_establecimiento_comuna_map(year: str, section_key: str) -> dict[str, str]:
    csv_path = OUTPUT_DIR / f"{year}_{section_key}.csv"
    if not csv_path.exists():
        return {}
    try:
        raw = pd.read_csv(
            csv_path,
            usecols=["nombre_establecimiento", "nombre_comuna"],
            dtype=str,
        )
    except Exception:
        return {}

    raw = raw.dropna(subset=["nombre_establecimiento"]).copy()
    raw["nombre_establecimiento"] = raw["nombre_establecimiento"].astype(str).str.strip()
    raw["nombre_comuna"] = raw["nombre_comuna"].astype(str).str.strip()
    raw = raw[raw["nombre_establecimiento"] != ""]

    def choose_comuna(values) -> str | None:
        comunas = sorted(
            {
                v
                for v in values
                if isinstance(v, str) and v and v.lower() != "nan"
            }
        )
        if not comunas:
            return None
        if len(comunas) == 1:
            return comunas[0]
        return "Multiples comunas"

    mapped = raw.groupby("nombre_establecimiento")["nombre_comuna"].apply(choose_comuna)
    return mapped.dropna().to_dict()


@st.cache_data(show_spinner=False)
def load_deis_hierarchy(deis_path: str):
    path = Path(deis_path)
    if not path.exists():
        return None, None

    df = pd.read_csv(path, sep=";")
    need_cols = [
        "Nombre Comuna",
        "Nombre Dependencia Jerárquica (SEREMI / Servicio de Salud)",
        "Nombre Oficial",
    ]
    if any(c not in df.columns for c in need_cols):
        return None, None

    d = df[need_cols].copy()
    d.columns = ["Comuna", "Servicio de Salud", "Establecimiento"]
    for c in d.columns:
        d[c] = d[c].astype(str).str.strip().replace("nan", pd.NA)

    d = d[d["Servicio de Salud"].str.contains("Servicio de Salud", case=False, na=False)]

    comuna_ss = (
        d.dropna(subset=["Comuna", "Servicio de Salud"])
        .groupby(["Comuna", "Servicio de Salud"], as_index=False)
        .size()
        .sort_values(["Comuna", "size"], ascending=[True, False])
        .drop_duplicates(subset=["Comuna"])
        .loc[:, ["Comuna", "Servicio de Salud"]]
    )

    est_hierarchy = (
        d.dropna(subset=["Establecimiento", "Comuna", "Servicio de Salud"])
        .groupby(["Establecimiento", "Comuna", "Servicio de Salud"], as_index=False)
        .size()
        .sort_values(["Establecimiento", "size"], ascending=[True, False])
        .drop_duplicates(subset=["Establecimiento"])
        .loc[:, ["Establecimiento", "Comuna", "Servicio de Salud"]]
    )

    return comuna_ss, est_hierarchy


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Datos", index=False)
    return buffer.getvalue()


def render_provisional_badge():
    st.markdown(
        """
        <div class="provisional-badge">Datos Provisorios</div>
        """,
        unsafe_allow_html=True,
    )


def shorten_a04_prof_headers(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    pattern = re.compile(r"(?i)^consulta de lactancia por profesional\s*-\s*")
    renamed = {}
    changed = False
    for c in df.columns:
        name = str(c)
        short = pattern.sub("", name).strip()
        if short != name:
            renamed[c] = short
            changed = True
    if renamed:
        df = df.rename(columns=renamed)
    return df, changed


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
        return "Servicio de Salud"
    return r


def pick_geo_col(df: pd.DataFrame) -> str | None:
    for col in ["Servicio de Salud", "Comuna", "Establecimiento", "Nombre"]:
        if col in df.columns:
            return col
    return None


def find_rate_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if "TASA" in str(c).upper() or "%" in str(c)]


def as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def is_ratio_series(series: pd.Series) -> bool:
    s = as_numeric(series).dropna()
    if s.empty:
        return False
    return bool((s.min() >= 0) and (s.max() <= 1.2))


def fmt_percent_value(value: float, ratio: bool) -> str:
    if pd.isna(value):
        return "-"
    return f"{value * 100:.1f}%" if ratio else f"{value:.1f}%"


def fmt_int(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{int(round(value)):,}".replace(",", ".")


def get_rm_row(df: pd.DataFrame) -> pd.Series | None:
    needles = {
        "región metropolitana",
        "region metropolitana",
        "total región metropolitana",
        "total region metropolitana",
    }
    geo_col = pick_geo_col(df)
    if not geo_col:
        return None
    s = df[geo_col].astype(str).str.strip().str.lower()
    match = df[s.isin(needles)]
    return match.iloc[0] if not match.empty else None


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


def build_column_config(df: pd.DataFrame, rate_cols: list[str], compact: bool = False):
    config = {}
    rate_set = set(rate_cols)
    for col in df.columns:
        label = prettify_column_label(col)
        if col == "Servicio de Salud":
            config[col] = st.column_config.TextColumn(label, width="large", pinned=True)
        elif col == "Comuna":
            config[col] = st.column_config.TextColumn(label, width="medium", pinned=True)
        elif col == "Establecimiento":
            config[col] = st.column_config.TextColumn(label, width="large", pinned=True)
        elif col == "Nombre":
            config[col] = st.column_config.TextColumn(label, width="large", pinned=True)
        elif col in rate_set:
            config[col] = st.column_config.NumberColumn(label, width="small")
        else:
            config[col] = st.column_config.NumberColumn(
                label,
                width="small" if compact else "medium",
            )
    return config


def prettify_column_label(label: str) -> str:
    text = str(label).strip()
    if not text:
        return text

    explicit_map = {
        "nombre_ss": "Servicio de Salud",
        "nombre_ss -": "Servicio de Salud",
        "nombre_comuna": "Comuna",
        "nombre_comuna -": "Comuna",
        "nombre_establecimiento": "Establecimiento",
        "nombre_establecimiento -": "Establecimiento",
    }
    if text in explicit_map:
        return explicit_map[text]

    protected = {"Servicio de Salud", "Comuna", "Establecimiento", "Nombre"}
    if text in protected:
        return text

    def _sentence_case(part: str) -> str:
        p = str(part).strip()
        if not p:
            return p
        for idx, ch in enumerate(p):
            if ch.isalpha():
                return p[:idx] + ch.upper() + p[idx + 1 :].lower()
        return p

    return " - ".join(_sentence_case(part) for part in text.split(" - "))


def prepare_a03_frame(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    df = df.rename(
        columns={
            "nombre_ss": "Servicio de Salud",
            "nombre_comuna": "Comuna",
            "nombre_establecimiento": "Establecimiento",
        }
    )
    if "Nombre" in df.columns:
        label_map = {
            "Servicio": "Servicio de Salud",
            "Comuna": "Comuna",
            "Establecimiento": "Establecimiento",
        }
        if tipo in label_map:
            df = df.rename(columns={"Nombre": label_map[tipo]})
    return df


def merge_a03_months(file_path: Path, selected_sheets: list[str], tipo: str) -> pd.DataFrame:
    merged = None
    geo_label_map = {
        "Servicio": "Servicio de Salud",
        "Comuna": "Comuna",
        "Establecimiento": "Establecimiento",
    }
    geo_col = geo_label_map[tipo]

    for sh in selected_sheets:
        month_label = sh.replace(f"{tipo} ", "", 1)
        tmp = load_sheet(file_path, sh, "A03_SECCION_A5", tipo)
        tmp = prepare_a03_frame(tmp, tipo)

        rename_map = {}
        for col in tmp.columns:
            if col != geo_col:
                rename_map[col] = f"{month_label} - {col}"
        tmp = tmp.rename(columns=rename_map)

        if merged is None:
            merged = tmp
        else:
            merged = merged.merge(tmp, on=geo_col, how="outer")

    return merged if merged is not None else pd.DataFrame()


def enrich_hierarchy_by_level(df: pd.DataFrame, tipo: str):
    comuna_ss_map, est_hierarchy = load_deis_hierarchy(str(DEFAULT_DEIS_PATH))
    out = df.copy()

    if tipo == "Comuna":
        if "Servicio de Salud" not in out.columns:
            out["Servicio de Salud"] = pd.NA
        if comuna_ss_map is not None and "Comuna" in out.columns:
            map_df = comuna_ss_map.rename(columns={"Servicio de Salud": "Servicio de Salud DEIS"})
            out = out.merge(map_df, on="Comuna", how="left")
            out["Servicio de Salud"] = out["Servicio de Salud"].fillna(out["Servicio de Salud DEIS"])
            out = out.drop(columns=["Servicio de Salud DEIS"])
        ordered = [c for c in ["Servicio de Salud", "Comuna"] if c in out.columns]
        rest = [c for c in out.columns if c not in ordered]
        return out[ordered + rest]

    if tipo == "Establecimiento":
        if "Comuna" not in out.columns:
            out["Comuna"] = pd.NA
        if "Servicio de Salud" not in out.columns:
            out["Servicio de Salud"] = pd.NA
        if est_hierarchy is not None and "Establecimiento" in out.columns:
            map_df = est_hierarchy.rename(
                columns={
                    "Comuna": "Comuna DEIS",
                    "Servicio de Salud": "Servicio de Salud DEIS",
                }
            )
            out = out.merge(map_df, on="Establecimiento", how="left")
            out["Comuna"] = out["Comuna"].fillna(out["Comuna DEIS"])
            out["Servicio de Salud"] = out["Servicio de Salud"].fillna(out["Servicio de Salud DEIS"])
            out = out.drop(columns=["Comuna DEIS", "Servicio de Salud DEIS"])
        ordered = [c for c in ["Servicio de Salud", "Comuna", "Establecimiento"] if c in out.columns]
        rest = [c for c in out.columns if c not in ordered]
        return out[ordered + rest]

    return out


def render_section_page(section: str):
    if section not in SECTIONS:
        st.error(f"Sección no reconocida: {section}")
        st.stop()

    section_label = SECTIONS[section]
    years = list_years()

    st.title(f"Dashboard REM Lactancia · {section_label}")
    render_provisional_badge()
    st.caption("Explora resultados por desagregación y descarga la vista filtrada.")

    with st.sidebar:
        st.header("Filtros")
        year = st.selectbox("Año", years, index=0)

    file_path = get_file(year, section)
    if not file_path.exists():
        st.error(f"No se encontró el archivo esperado: {file_path.name}")
        st.stop()

    sheets = get_sheets(file_path)
    if not sheets:
        st.warning("El archivo existe, pero no contiene hojas de datos.")
        st.stop()

    show_only_pct = False
    sheet_label = ""
    selected_meses = []

    if section == "A03_SECCION_A5":
        meses = ["1° mes", "3° mes", "6° mes"]
        niveles_map = {
            "Servicio de Salud": "Servicio",
            "Comuna": "Comuna",
            "Establecimiento": "Establecimiento",
        }
        meses_ok = [m for m in meses if any(s.endswith(f" {m}") for s in sheets)]
        niveles_ok = [label for label, prefix in niveles_map.items() if any(s.startswith(f"{prefix} ") for s in sheets)]
        with st.sidebar:
            selected_mes = st.selectbox("Mes", meses_ok, index=0)
            nivel = st.selectbox("Desagregación", niveles_ok)
            show_only_pct = st.checkbox("Mostrar solo porcentajes", value=False)

        tipo = niveles_map[nivel]
        selected_meses = [selected_mes]
        selected_sheets = [f"{tipo} {selected_mes}"] if f"{tipo} {selected_mes}" in sheets else []
        if not selected_sheets:
            st.warning("No se encontraron hojas para la combinación seleccionada.")
            st.stop()

        df = merge_a03_months(file_path, selected_sheets, tipo)
        sheet_label = f"{nivel} · {selected_mes}"
    else:
        parsed = [p for p in (split_sheet(s) for s in sheets) if p is not None]
        categorias = sorted({p[0] for p in parsed})
        tipos_raw = {normalize_tipo(p[1]) for p in parsed}
        orden_tipos = [t for t in ["Servicio de Salud", "Comuna", "Establecimiento"] if t in tipos_raw]
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
        sheet_label = sheet
        if section == "A24_SECCION_E":
            with st.sidebar:
                show_only_pct = st.checkbox("Mostrar solo porcentajes", value=False)

    headers_shortened = False

    if section == "A04_SECCION_L":
        df, headers_shortened = shorten_a04_prof_headers(df)

    if section == "A03_SECCION_A5":
        df = prepare_a03_frame(df, tipo)
        df = enrich_hierarchy_by_level(df, tipo)
    elif section in {"A04_SECCION_L", "A24_SECCION_E"}:
        df = enrich_hierarchy_by_level(df, tipo)

    if tipo == "Establecimiento":
        est_col = "Establecimiento" if "Establecimiento" in df.columns else None
        if est_col and "Comuna" not in df.columns:
            comuna_map = load_establecimiento_comuna_map(year, section)
            if comuna_map:
                comuna_series = df[est_col].astype(str).map(comuna_map)
                if comuna_series.notna().any():
                    insert_pos = df.columns.get_loc(est_col) + 1
                    df.insert(insert_pos, "Comuna", comuna_series)

    geo_col = pick_geo_col(df)
    rate_cols = find_rate_cols(df)
    rm = get_rm_row(df)

    st.subheader(f"{year} · {section_label}")
    st.caption(f"Vista activa: {sheet_label}")
    if headers_shortened:
        st.caption("Encabezados abreviados: categoría base `Consulta de lactancia por profesional`.")

    k1, k2, k3 = st.columns(3)
    if rm is not None:
        if section == "A03_SECCION_A5" and len(selected_meses) == 1:
            month_label = selected_meses[0]
            rate_col = f"{month_label} - TASA LACTANCIA MATERNA EXCLUSIVA"
            total_col = f"{month_label} - TOTAL NIÑOS CONTROLADOS"
            excl_col = f"{month_label} - CON LACTANCIA MATERNA EXCLUSIVA"
            if rate_col in df.columns:
                k1.metric("Tasa LME", fmt_percent_value(float(rm[rate_col]), ratio=False))
            if total_col in df.columns:
                k2.metric("Niños controlados", fmt_int(float(rm[total_col])))
            if excl_col in df.columns:
                k3.metric("Niños con LME", fmt_int(float(rm[excl_col])))
        elif "TASA LACTANCIA MATERNA EXCLUSIVA" in df.columns:
            k1.metric("Tasa LME", fmt_percent_value(float(rm["TASA LACTANCIA MATERNA EXCLUSIVA"]), ratio=False))
            k2.metric("Niños controlados", fmt_int(float(rm["TOTAL NIÑOS CONTROLADOS"])))
            k3.metric("Niños con LME", fmt_int(float(rm["CON LACTANCIA MATERNA EXCLUSIVA"])))
        elif "% Lactancia Exclusiva" in df.columns:
            ratio = is_ratio_series(df["% Lactancia Exclusiva"])
            if section != "A24_SECCION_E":
                k1.metric("Lactancia Exclusiva", fmt_percent_value(float(rm["% Lactancia Exclusiva"]), ratio=ratio))
            if "Total de Egresos" in df.columns:
                k2.metric("Total egresos", fmt_int(float(rm["Total de Egresos"])))
            if "Egresados con lactancia materna exclusiva" in df.columns:
                k3.metric("Egresados LME", fmt_int(float(rm["Egresados con lactancia materna exclusiva"])))

    df_view = df.copy()

    if tipo == "Establecimiento" and "Comuna" in df_view.columns:
        st.caption("Incluye la comuna de cada establecimiento cuando está disponible.")

    if show_only_pct:
        id_cols = [c for c in ["Servicio de Salud", "Comuna", "Establecimiento", "Nombre"] if c in df_view.columns]
        pct_cols = [c for c in rate_cols if c in df_view.columns]
        keep_cols = id_cols + pct_cols
        if keep_cols:
            df_view = df_view[keep_cols]

    if section == "A24_SECCION_E":
        fixed_cols = [c for c in ["Servicio de Salud", "Comuna", "Establecimiento", "Nombre"] if c in df_view.columns]
        data_cols = [c for c in df_view.columns if c not in fixed_cols]
        if data_cols:
            selected_cols = st.multiselect(
                "Columnas a mostrar",
                data_cols,
                default=data_cols,
                help="Las columnas territoriales se mantienen visibles.",
            )
            df_view = df_view[fixed_cols + selected_cols]

    display_df = df_view.rename(columns={c: prettify_column_label(c) for c in df_view.columns})
    display_rate_cols = find_rate_cols(display_df)
    column_config = build_column_config(display_df, display_rate_cols, compact=(section == "A24_SECCION_E"))

    if display_rate_cols:
        st.dataframe(
            style_rate_table(display_df, display_rate_cols),
            width="stretch",
            height=620,
            column_config=column_config,
        )
    else:
        st.dataframe(
            style_rate_table(display_df, []),
            width="stretch",
            height=620,
            column_config=column_config,
        )

    st.caption(f"Filas mostradas: {len(df_view):,} de {len(df):,}")

    excel_bytes = dataframe_to_excel_bytes(display_df)
    download_token = sheet_label.replace(" ", "_").replace(",", "").replace("·", "-").replace("°", "")
    st.download_button(
        label="Descargar vista en Excel",
        data=excel_bytes,
        file_name=f"{year}_{section}_{download_token}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(f"Origen: {file_path.name}")
