"""Módulo: cruce de varios Excels por coincidencias de columnas."""
import io
import re

import pandas as pd
import streamlit as st

from src.cruce import TIPOS, cruzar

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

tablas: dict[str, pd.DataFrame] = {}
for a in archivos:
    nombre = base = a.name.rsplit(".", 1)[0]
    n = 2
    while nombre in tablas:
        nombre, n = f"{base} ({n})", n + 1
    df = leer(a.name, a.getvalue())
    df.columns = [str(c) for c in df.columns]
    tablas[nombre] = df
docs = list(tablas)

# ---------------------------------------------------------------- 1. Documentos
st.header("1. Documentos")
for col, (nombre, df) in zip(st.columns(len(docs)), tablas.items()):
    with col:
        st.markdown(f"**{nombre}**")
        st.caption(f"{len(df)} filas · {len(df.columns)} columnas")
        st.dataframe(pd.DataFrame({"Columnas": df.columns}), hide_index=True, use_container_width=True)

# ------------------------------------------------------------ 2. Coincidencias
st.header("2. Coincidencias")
st.caption(
    "Cada coincidencia indica columnas que deben tener exactamente el mismo valor en distintos "
    "documentos (pueden llamarse distinto). Si los documentos se unen por más de un dato "
    "(ej. Fecha de evento y N° INFRA), agregá otra coincidencia."
)

# Cada coincidencia: {"id": único, "n": cantidad de documentos que participan}
ss = st.session_state
ss.setdefault("coinc", [{"id": 0, "n": 2}])
ss.setdefault("coinc_sig", 1)

coincidencias = []
for num, c in enumerate(ss["coinc"], start=1):
    cid = c["id"]
    with st.container(border=True):
        st.markdown(f"**Coincidencia {num}**")
        entradas = []
        for k in range(c["n"]):
            c1, c2 = st.columns(2)
            doc = c1.selectbox(
                "Documento", docs, index=min(k, len(docs) - 1), key=f"c{cid}_doc{k}",
                label_visibility="visible" if k == 0 else "collapsed",
            )
            columnas = list(tablas[doc].columns)
            # Si la primera columna elegida existe con el mismo nombre, sugerirla
            sugerida = entradas[0][1] if entradas and entradas[0][1] in columnas else None
            col = c2.selectbox(
                "Columna que debe coincidir", columnas,
                index=columnas.index(sugerida) if sugerida else 0, key=f"c{cid}_col{k}",
                label_visibility="visible" if k == 0 else "collapsed",
            )
            entradas.append((doc, col))

        repetidos = {d for d, _ in entradas if [x for x, _ in entradas].count(d) > 1}
        if repetidos:
            st.warning(f"Un mismo documento aparece dos veces: {', '.join(repetidos)}")
        coincidencias.append(entradas)

        b1, b2, b3, _ = st.columns([3, 3, 3, 3])
        if c["n"] < len(docs) and b1.button("➕ Sumar otro documento", key=f"c{cid}_mas"):
            c["n"] += 1
            st.rerun()
        if c["n"] > 2 and b2.button("➖ Quitar último documento", key=f"c{cid}_menos"):
            c["n"] -= 1
            st.rerun()
        if len(ss["coinc"]) > 1 and b3.button("🗑️ Eliminar coincidencia", key=f"c{cid}_borrar"):
            ss["coinc"] = [x for x in ss["coinc"] if x["id"] != cid]
            st.rerun()

if st.button("➕ Agregar otra coincidencia"):
    ss["coinc"].append({"id": ss["coinc_sig"], "n": 2})
    ss["coinc_sig"] += 1
    st.rerun()

# ------------------------------------------------- 3. Columnas del resultado
st.header("3. Columnas del documento final")
st.caption(
    "Elegí de cada documento qué columnas querés que queden en el resultado. De cada coincidencia "
    "viene tildada una sola columna, porque las otras tendrían los mismos valores."
)

c1, c2 = st.columns(2)
principal = c1.selectbox("Documento principal", docs, help="El cruce arranca desde este documento.")
tipo = c2.radio("Qué filas conservar", list(TIPOS))

usadas = {(d, col) for coinc in coincidencias for d, col in coinc}
# De cada coincidencia se sugiere una sola columna (la del principal si participa,
# si no la primera); el resto vendría con los mismos valores repetidos.
repetidas = set()
for coinc in coincidencias:
    queda = next((e for e in coinc if e[0] == principal), coinc[0])
    repetidas |= {e for e in coinc if e != queda}
# Si cambian las coincidencias o el principal, se recalculan las sugerencias
firma = abs(hash((principal, tuple(sorted(usadas)))))


def marcar_todas(claves: list[str], valor: bool):
    for k in claves:
        ss[k] = valor


columnas_finales = {}
for col, doc in zip(st.columns(len(docs)), docs):
    with col, st.container(border=True):
        st.markdown(f"**{doc}**")
        claves = [f"fin_{firma}_{doc}_{i}" for i in range(len(tablas[doc].columns))]
        b1, b2 = st.columns(2)
        b1.button("☑ Todas", key=f"todas_{doc}", on_click=marcar_todas,
                  args=(claves, True), use_container_width=True)
        b2.button("☐ Ninguna", key=f"ninguna_{doc}", on_click=marcar_todas,
                  args=(claves, False), use_container_width=True)
        columnas_finales[doc] = [
            x for x, clave in zip(tablas[doc].columns, claves)
            if st.checkbox(x, value=(doc, x) not in repetidas, key=clave)
        ]

# ----------------------------------------------------------------- 4. Cruzar
if st.button("Cruzar", type="primary"):
    if repetidos := [i + 1 for i, e in enumerate(coincidencias) if len({d for d, _ in e}) < len(e)]:
        st.error(f"Corregí las coincidencias {repetidos}: un documento aparece dos veces.")
    elif not any(columnas_finales.values()):
        st.error("Elegí al menos una columna para el documento final.")
    else:
        try:
            ss["resultado"], ss["resumen"] = cruzar(
                tablas, coincidencias, principal, TIPOS[tipo], columnas_finales
            )
        except ValueError as e:
            st.error(str(e))

if "resultado" in ss:
    res = ss["resultado"]
    st.header("Resultado")
    st.dataframe(pd.DataFrame(ss["resumen"]), hide_index=True, use_container_width=True)
    st.caption(f"{len(res)} filas · {len(res.columns)} columnas")
    st.dataframe(res, hide_index=True)

    nombre = st.text_input("Nombre del archivo a descargar", value="cruce")
    # Sacar caracteres que Windows no acepta en nombres de archivo
    nombre = re.sub(r'[\\/:*?"<>|]', "", nombre).strip().removesuffix(".xlsx") or "cruce"

    buffer = io.BytesIO()
    res.to_excel(buffer, index=False)
    st.download_button(f"Descargar {nombre}.xlsx", buffer.getvalue(), f"{nombre}.xlsx")
