"""Módulo: Concatenación, del CSV del Libro de Novedades a un Excel con una fila por novedad."""
import re

import streamlit as st

from src import concatenacion as ln

st.title("Concatenación")
st.caption("Convierte el CSV del reporte LibroNovedades (Reportes Grupo Emepa → Ferroviario → "
           "Operaciones → transporte → PCZ) en un Excel con una fila por número de novedad: "
           "fecha, hora de inicio, hora de fin y el detalle completo.")

ss = st.session_state
P = "conc_"  # prefijo de las claves de este módulo en session_state
ss.setdefault(P + "opciones", list(ln.CLAVES_SUGERIDAS))
ss.setdefault(P + "claves", list(ln.CLAVES_DEFECTO))


@st.cache_data(show_spinner="Leyendo archivo...")
def procesar(contenido: bytes, claves: tuple, conectores: tuple, encoding: str | None):
    return ln.procesar(contenido, list(claves), list(conectores), encoding)


# ------------------------------------------------------------------ 1. Archivo
st.header("1. Archivo")
c1, c2 = st.columns([3, 1])
archivo = c1.file_uploader("Subí el CSV del Libro de Novedades", type=["csv"])
encoding = c2.selectbox(
    "Encoding de lectura", list(ln.ENCODINGS), key=P + "encoding",
    help="Automático sirve casi siempre. Si las tildes o la Ñ se ven raras, probá con "
         "Windows-1252 o UTF-8.",
)

# ------------------------------------------------------------ 2. Palabras clave
st.header("2. Palabras clave de fin")
st.caption("La hora fin es la hora del último renglón que contiene alguna de estas palabras. "
           "Se buscan solo en el texto de la novedad, como palabras completas: NORMAL no "
           "coincide con ANORMAL ni con NORMALIZADO. Lo que agregues dura hasta que cierres la app.")


def agregar_clave():
    nueva = " ".join(ss[P + "nueva"].split()).upper()
    ss[P + "nueva"] = ""
    if not ln.normalizar(nueva):
        ss[P + "msg"] = "Escribí una palabra o frase para agregar."
        return
    existente = next((o for o in ss[P + "opciones"] if ln.normalizar(o) == ln.normalizar(nueva)), None)
    if existente is None:
        ss[P + "opciones"].append(nueva)
        existente = nueva
    ss[P + "claves"] = list(dict.fromkeys([*ss[P + "claves"], existente]))


claves = st.pills("Palabras clave", ss[P + "opciones"], selection_mode="multi",
                  key=P + "claves", label_visibility="collapsed")
with st.form(P + "form_clave", clear_on_submit=False, border=False):
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.text_input("Agregar palabra o frase", key=P + "nueva", placeholder="Ej.: RECIBE VIA")
    c2.form_submit_button("Agregar", on_click=agregar_clave, use_container_width=True)
if msg := ss.pop(P + "msg", None):
    st.warning(msg)

with st.expander("Conectores (palabras que se ignoran al comparar)"):
    st.caption("Se quitan del texto y de las palabras clave antes de comparar. Así «NORMAL EL "
               "SECTOR» coincide con la clave «normal sector». Para agregar uno, escribilo en la "
               "lista y apretá Enter. «no» y «sin» nunca son conectores porque cambian el sentido.")
    conectores = st.multiselect("Conectores", ln.CONECTORES_DEFECTO, default=ln.CONECTORES_DEFECTO,
                                accept_new_options=True, key=P + "conectores",
                                label_visibility="collapsed")

conj_conectores, rechazados = ln.preparar_conectores(conectores)
if prohibidos := [c for c in rechazados if ln.normalizar(c) in ln.NUNCA_CONECTORES]:
    st.warning(f"No se usan como conectores: {', '.join(prohibidos)}. «no» y «sin» cambian el "
               "sentido de la frase.")
if frases := [c for c in rechazados if c not in prohibidos]:
    st.warning(f"No se usan como conectores: {', '.join(frases)}. Un conector tiene que ser "
               "una sola palabra.")
_, ignoradas = ln.preparar_claves(claves, conj_conectores)
if ignoradas:
    st.warning(f"Estas palabras clave quedan vacías al quitar los conectores y se ignoran: "
               f"{', '.join(ignoradas)}.")
if not claves:
    st.info("No hay palabras clave elegidas: todas las novedades van a quedar sin hora fin.")

# ---------------------------------------------------------------- 3. Resultado
st.header("3. Resultado")
if archivo is None:
    st.info("Subí el CSV para ver el resultado.")
    st.stop()

try:
    r = procesar(archivo.getvalue(), tuple(claves), tuple(conectores), ln.ENCODINGS[encoding])
except ln.ErrorArchivo as e:
    st.error(str(e))
    st.stop()

tabla = r.tabla
con_fin = int(tabla["Hora fin"].notna().sum())
st.success(f"{len(tabla)} novedades armadas a partir de {r.renglones} renglones "
           f"(leído como {r.encoding}). {con_fin} con hora fin y {len(tabla) - con_fin} sin hora fin.")
for aviso in r.avisos:
    st.warning(aviso)

# Vista previa: fecha y horas como texto para que las vacías no digan "None"
vista = tabla.assign(**{
    "Fecha": tabla["Fecha"].map(lambda f: f"{f:%d/%m/%Y}" if f else ""),
    "Hora inicio": tabla["Hora inicio"].map(lambda h: f"{h:%H:%M}" if h else ""),
    "Hora fin": tabla["Hora fin"].map(lambda h: f"{h:%H:%M}" if h else ""),
    "Renglón que marca el fin": r.renglon_fin,
})
st.dataframe(
    vista, hide_index=True, use_container_width=True, height=min(35 * len(vista) + 38, 600),
    column_config={
        "Nro novedad": st.column_config.NumberColumn(format="%d", width=100),
        "Fecha": st.column_config.TextColumn(width=95),
        "Hora inicio": st.column_config.TextColumn(width=90),
        "Hora fin": st.column_config.TextColumn(width=80),
        "Detalle": st.column_config.TextColumn(width="large"),
        "Renglón que marca el fin": st.column_config.TextColumn(
            help="Solo para revisar: esta columna no va al Excel."),
    },
)
st.caption("La última columna es solo para revisar y no va al Excel. Para leer un detalle "
           "largo, pasá el mouse por la celda o hacé doble clic.")

fechas = tabla["Fecha"].dropna()
sugerido = f"Libro de Novedades {fechas.max():%d-%m-%Y}" if len(fechas) else "Libro de Novedades"
nombre = st.text_input("Nombre del archivo a descargar", value=sugerido)
# Sacar caracteres que Windows no acepta en nombres de archivo
nombre = re.sub(r'[\\/:*?"<>|]', "", nombre).strip().removesuffix(".xlsx") or "Libro de Novedades"

with st.container(border=True):
    st.markdown("**Tal como viene**")
    st.caption("Las cinco columnas una al lado de la otra: Nro novedad, Fecha, Hora inicio, "
               "Hora fin y Detalle.")
    st.download_button(f"Descargar {nombre}.xlsx", ln.exportar_excel(tabla), f"{nombre}.xlsx",
                       type="primary", key=P + "descargar")

with st.container(border=True):
    st.markdown("**Formato de la hoja «Tabla»**")
    st.caption("Las mismas columnas que la hoja «Tabla», en el mismo orden: Fecha, N° Novedad, "
               "Descripción, Comienzo de falla (hora inicio) y Habilitación (hora fin) con datos; "
               "Mes, Sistema, Subsistema, Parte, Elemento, Nombre correcto, Zona, VER y Falla "
               "vacías. Así copiás todo de una vez.")
    st.markdown(
        "Para pegar sin borrar las fórmulas de las columnas vacías:\n"
        "1. En este Excel, seleccioná las filas con datos (desde la fila 2, sin el encabezado) "
        "y copialas con **Ctrl+C**.\n"
        "2. En la hoja «Tabla», hacé clic en la celda de la columna **Fecha** donde va la "
        "primera novedad.\n"
        "3. Apretá **Ctrl+Alt+V** (Pegado especial), tildá **Saltar blancos** y tocá **Aceptar**.\n\n"
        "Las celdas vacías no pisan lo que ya hay en la hoja. Ojo: cuando no hay hora de fin, "
        "Habilitación también queda vacía y se saltea igual."
    )
    st.download_button(f"Descargar {nombre} - Tabla.xlsx",
                       ln.exportar_excel(tabla, ln.FORMATO_TABLA, "Tabla"),
                       f"{nombre} - Tabla.xlsx", type="primary", key=P + "descargar_tabla")
