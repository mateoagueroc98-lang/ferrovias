"""Punto de entrada: menú con los módulos de la app."""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ferrovías - Excels", layout="wide")

# Cartel de estación arriba del menú (colores y fuente en .streamlit/config.toml).
st.sidebar.html("""
<div style="border:2px solid #fff;border-radius:6px;padding:.7rem .9rem .6rem;margin:.2rem 0 .4rem">
  <div style="font-size:1.9rem;font-weight:800;line-height:1;letter-spacing:-.01em">Ferrovías</div>
  <div style="font-size:.95rem;opacity:.85;margin-top:.35rem">Automatización de Excels</div>
</div>
""")

paginas = [
    st.Page("modulos/cruce.py", title="Cruce de Excels", icon=":material/join_inner:", default=True),
    st.Page("modulos/relleno_pdf.py", title="Relleno de Excel mediante PDF", icon=":material/picture_as_pdf:"),
    st.Page("modulos/asociacion_lg_pcz.py", title="Asociación LG ↔ PCZ", icon=":material/link:"),
]
# El menú se arma a mano para que quede debajo del cartel.
pagina = st.navigation(paginas, position="hidden")
for p in paginas:
    st.sidebar.page_link(p)
pagina.run()
