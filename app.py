"""App Streamlit: cruzar Excels por columnas clave y rellenar columnas con IA."""
import io

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.cruce import cruzar  # noqa: E402
from src.ia import rellenar_columna  # noqa: E402

st.set_page_config(page_title="Ferrovías - Excels", layout="wide")
st.title("Cruce de Excels")

col1, col2 = st.columns(2)
archivo_a = col1.file_uploader("Archivo principal", type=["xlsx", "xls", "csv"])
archivo_b = col2.file_uploader("Archivo a cruzar", type=["xlsx", "xls", "csv"])


def leer(archivo) -> pd.DataFrame:
    if archivo.name.endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo)


if archivo_a and archivo_b:
    a, b = leer(archivo_a), leer(archivo_b)
    comunes = [c for c in a.columns if c in b.columns]
    claves = st.multiselect("Columnas clave (deben existir en ambos)", comunes, default=comunes[:1])
    tipo = st.selectbox("Tipo de cruce", ["left", "inner", "outer", "right"])

    if claves and st.button("Cruzar"):
        st.session_state["resultado"] = cruzar(a, b, claves, tipo)

if "resultado" in st.session_state:
    res = st.session_state["resultado"]
    st.subheader("Resultado")
    st.write(res["_merge"].value_counts().rename({"both": "coinciden", "left_only": "solo principal", "right_only": "solo cruzado"}))
    st.dataframe(res)

    with st.expander("Rellenar una columna con IA"):
        columna = st.text_input("Columna a completar (existente o nueva)")
        instruccion = st.text_area("Instrucción para Claude")
        contexto = st.multiselect("Columnas que Claude puede leer", list(res.columns))
        if st.button("Rellenar") and columna and instruccion and contexto:
            with st.spinner("Consultando a Claude..."):
                st.session_state["resultado"] = rellenar_columna(res, columna, instruccion, contexto)
            st.rerun()

    buffer = io.BytesIO()
    res.drop(columns="_merge").to_excel(buffer, index=False)
    st.download_button("Descargar Excel", buffer.getvalue(), "resultado.xlsx")
