"""App Streamlit: cruzar varios Excels por columnas clave y rellenar columnas con IA."""
import io

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.cruce import TIPOS, cruzar_varios  # noqa: E402
from src.ia import rellenar_columna  # noqa: E402

st.set_page_config(page_title="Ferrovías - Excels", layout="wide")
st.title("Cruce de Excels")


@st.cache_data
def leer(nombre: str, contenido: bytes) -> pd.DataFrame:
    if nombre.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(contenido))
    return pd.read_excel(io.BytesIO(contenido))


archivos = st.file_uploader(
    "Subí dos o más archivos", type=["xlsx", "xls", "csv"], accept_multiple_files=True
)

if len(archivos) < 2:
    st.info("Subí al menos dos archivos para empezar.")
    st.stop()

tablas = [(a.name.rsplit(".", 1)[0], leer(a.name, a.getvalue())) for a in archivos]

# --- 1. Columnas de cada archivo, uno al lado del otro ---
st.subheader("Archivos y sus columnas")
for col, (nombre, df) in zip(st.columns(len(tablas)), tablas):
    with col:
        st.markdown(f"**{nombre}**")
        st.caption(f"{len(df)} filas · {len(df.columns)} columnas")
        st.dataframe(
            pd.DataFrame({"Columnas": [str(c) for c in df.columns]}),
            hide_index=True,
            use_container_width=True,
        )

# --- 2. Coincidencias entre archivos ---
st.subheader("Coincidencias")
st.caption(
    "Elegí qué columna de un archivo tiene que coincidir exactamente con cuál del otro. "
    "Los nombres pueden ser distintos. Agregá más de una si se unen por varias columnas "
    "(ej. Fecha de evento + N° INFRA)."
)

uniones = []
for i in range(1, len(tablas)):
    nombre, df = tablas[i]
    # Se puede unir contra cualquier columna de los archivos anteriores
    opciones_izq = [(j, c) for j in range(i) for c in tablas[j][1].columns]

    with st.container(border=True):
        st.markdown(f"**Unir _{nombre}_ con {'_' + tablas[0][0] + '_' if i == 1 else 'los archivos anteriores'}**")

        clave_n = f"n_pares_{i}"
        st.session_state.setdefault(clave_n, 1)

        pares = []
        for k in range(st.session_state[clave_n]):
            c1, c2, c3 = st.columns([5, 1, 5])
            izq = c1.selectbox(
                "Columna de",
                opciones_izq,
                format_func=lambda o: f"{tablas[o[0]][0]} › {o[1]}",
                key=f"izq_{i}_{k}",
                label_visibility="collapsed" if k else "visible",
            )
            c2.markdown("<div style='text-align:center;padding-top:{}'>=</div>".format("8px" if k else "36px"),
                        unsafe_allow_html=True)
            der = c3.selectbox(
                f"Columna de {nombre}",
                list(df.columns),
                key=f"der_{i}_{k}",
                label_visibility="collapsed" if k else "visible",
            )
            pares.append((izq, der))

        b1, b2, _ = st.columns([2, 2, 6])
        if b1.button("➕ Agregar otra coincidencia", key=f"mas_{i}"):
            st.session_state[clave_n] += 1
            st.rerun()
        if st.session_state[clave_n] > 1 and b2.button("➖ Quitar la última", key=f"menos_{i}"):
            st.session_state[clave_n] -= 1
            st.rerun()

        tipo = st.radio("Qué filas conservar", list(TIPOS), horizontal=True, key=f"tipo_{i}")
        uniones.append({"pares": pares, "tipo": TIPOS[tipo]})

if st.button("Cruzar", type="primary"):
    resultado, resumen = cruzar_varios(tablas, uniones)
    st.session_state["resultado"] = resultado
    st.session_state["resumen"] = resumen

# --- 3. Resultado ---
if "resultado" in st.session_state:
    res = st.session_state["resultado"]
    st.subheader("Resultado")
    st.dataframe(pd.DataFrame(st.session_state["resumen"]), hide_index=True)
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
    res.to_excel(buffer, index=False)
    st.download_button("Descargar Excel", buffer.getvalue(), "resultado.xlsx")
