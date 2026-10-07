"""Punto de entrada: menú con los módulos de la app."""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ferrovías - Excels", layout="wide")

pagina = st.navigation([
    st.Page("modulos/cruce.py", title="Cruce de Excels", icon="🔗", default=True),
    st.Page("modulos/relleno_pdf.py", title="Relleno de Excel mediante PDF", icon="📄"),
])
pagina.run()
