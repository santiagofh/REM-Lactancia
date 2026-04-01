from pathlib import Path

import streamlit as st

from dashboard_lactancia_pages import SECTIONS, render_section_page

BASE_DIR = Path(__file__).resolve().parent


st.set_page_config(
    page_title="Dashboard REM Lactancia",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp h1, .stApp h2, .stApp h3 {
        color: #006FB3;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.logo(
    str(BASE_DIR / "assets" / "seremi_sidebar_logo.svg"),
    size="large",
    icon_image=str(BASE_DIR / "assets" / "seremi_sidebar_icon.svg"),
)


def home_page():
    st.title("Dashboard REM Lactancia")
    st.caption("Selecciona una seccion en el menu izquierdo para navegar entre A03, A04 y A24.")

    st.markdown("### Secciones")
    st.markdown(f"- **{SECTIONS['A03_SECCION_A5']}**")
    st.markdown(f"- **{SECTIONS['A04_SECCION_L']}**")
    st.markdown(f"- **{SECTIONS['A24_SECCION_E']}**")


def page_a03():
    render_section_page("A03_SECCION_A5")


def page_a04():
    render_section_page("A04_SECCION_L")


def page_a24():
    render_section_page("A24_SECCION_E")


navigation = st.navigation(
    [
        st.Page(home_page, title="Inicio", icon=":material/home:"),
        st.Page(page_a03, title="Lactancia Materna Exclusiva", icon=":material/child_care:"),
        st.Page(page_a04, title="Consultas y Consejerias", icon=":material/forum:"),
        st.Page(page_a24, title="Egresos Hospitalarios", icon=":material/local_hospital:"),
    ],
    position="sidebar",
    expanded=True,
)

navigation.run()
