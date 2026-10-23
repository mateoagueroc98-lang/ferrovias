"""Módulo: transcripciones del Libro de Guardia (en desarrollo)."""
import streamlit as st

st.title("Transcripciones del Libro de Guardia")
st.info("Módulo en desarrollo.")
# La imagen ocupa el 60 % del ancho, centrada.
_, centro, _ = st.columns([1, 3, 1])
centro.image("static/imagenes/esperando_el_tren.jpg", width="stretch",
             caption="Esperando que llegue este módulo.")
