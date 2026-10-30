"""Punto de entrada: menú con los módulos de la app."""
import base64
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ferrovías - Ing. de Mantenimiento", layout="wide")

# Marca arriba del menú: logo de Ferrovías sobre placa blanca (sobre el rojo del menú
# las franjas del logo no se verían). Colores y fuente en .streamlit/config.toml.
LOGO = base64.b64encode((Path(__file__).parent / "static" / "marca" / "ferrovias_logo.svg").read_bytes()).decode()
st.sidebar.html(f"""
<style>
/* Menú lateral con degradado del rojo Ferrovías al rojo profundo */
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #E31B22 0%, #C4161D 55%, #9E1219 100%); }}
/* Fondo general apenas degradado (de blanco a gris andén) */
[data-testid="stAppViewContainer"] {{ background: linear-gradient(180deg, #FFFFFF 0%, #F4F3F2 45%, #ECEAE8 100%); }}
[data-testid="stHeader"] {{ background: transparent; }}
/* Contenido de todos los módulos al 90 % (el menú lateral queda igual) */
[data-testid="stMainBlockContainer"] {{ zoom: 0.9; }}
/* Botones principales con el mismo degradado */
[data-testid="stBaseButton-primary"] {{ background: linear-gradient(180deg, #E61D24 0%, #B5131A 100%); border: none; }}
[data-testid="stBaseButton-primary"]:hover {{ background: linear-gradient(180deg, #C8161D 0%, #95101A 100%); }}
.marca {{ margin: .2rem 0 .9rem; }}
.marca-placa {{ background: #FFFFFF; border-radius: 6px; padding: .75rem .9rem;
               box-shadow: 0 2px 10px rgba(80, 8, 12, .35); }}
.marca-placa img {{ display: block; width: 100%; height: auto; }}
.marca-texto {{ color: #FFFFFF; font-size: .95rem; font-weight: 600; line-height: 1.3; margin-top: .6rem; }}
</style>
<div class="marca">
  <div class="marca-placa"><img src="data:image/svg+xml;base64,{LOGO}" alt="Ferrovías"></div>
  <div class="marca-texto">Herramienta de Ing. de Mantenimiento</div>
</div>
""")

# "Cruce de Excels" está oculto por ahora (no se usa). El código sigue en modulos/cruce.py y
# src/cruce.py; para volver a mostrarlo, descomentar esta línea:
# st.Page("modulos/cruce.py", title="Cruce de Excels", icon=":material/join_inner:", default=True),
paginas = [
    st.Page("modulos/transcripcion_lg.py", title="Transcripciones del LG", icon=":material/picture_as_pdf:"),
    st.Page("modulos/asociacion_lg_pcz.py", title="Asociación LG ↔ PCZ", icon=":material/link:"),
    st.Page("modulos/concatenacion.py", title="Concatenación", icon=":material/table_view:"),
]
# El menú se arma a mano para que quede debajo del cartel.
pagina = st.navigation(paginas, position="hidden")
for p in paginas:
    st.sidebar.page_link(p)
pagina.run()
