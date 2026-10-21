"""Módulo: asociación manual de filas del Libro de Guardia (LG) con novedades del PCZ."""
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src import asociacion_lg_pcz as a

st.title("Asociación LG ↔ PCZ")

ss = st.session_state
P = "lgpcz_"  # prefijo de las claves de este módulo en session_state
PASOS = ["1. Carga", "2. Asociación", "3. Exportar"]


@st.cache_data(show_spinner="Leyendo archivo...")
def leer(nombre: str, contenido: bytes) -> pd.DataFrame:
    return a.leer_tabla(nombre, contenido)


@st.cache_data(show_spinner=False)
def preparar(nombre_lg, bytes_lg, nombre_pcz, bytes_pcz, mapa_lg, mapa_pcz):
    lg = a.preparar_lg(leer(nombre_lg, bytes_lg), mapa_lg)
    pcz = a.preparar_pcz(leer(nombre_pcz, bytes_pcz), mapa_pcz)
    return lg, pcz


def ir_a_paso(paso: str):
    ss[P + "paso"] = paso


paso = st.radio("Paso", PASOS, horizontal=True, key=P + "paso", label_visibility="collapsed")
st.caption("⚠️ El progreso **no se guarda**: si cerrás la app o recargás la página, se pierde. "
           "Antes de cerrar, descargá el Excel en **3. Exportar**.")

if msg := ss.pop(P + "msg", None):
    getattr(st, msg[0])(msg[1])

# ===================================================================== 1. Carga
SIN_HORA = "— no tiene hora —"
FILA_EXCEL = "— usar el número de fila del Excel —"
ARCHIVOS = [
    # clave, título, columnas, ayuda por columna, opción especial de las opcionales
    ("lg", "Libro de Guardia (LG)", a.COLUMNAS_LG, {
        "Fecha": "Se usa para buscar las novedades de PCZ del mismo día.",
        "Transcripción": "Texto del libro: cada renglón es un aviso.",
        "Hora": "Opcional. Suma puntos a las novedades de PCZ con hora cercana "
                "(además de las horas escritas en el texto).",
    }, {"Hora": SIN_HORA}),
    ("pcz", "Novedades PCZ", a.COLUMNAS_PCZ, {
        "Fecha": "Se compara con la fecha de LG.",
        "Descripción": "Texto de la novedad: se compara con los avisos de LG.",
        "N° Novedad": "Identifica cada novedad. En la hoja «Asociaciones», si una asociación tiene varias "
                      "novedades, sus N° se juntan en la misma celda separados por « | ».",
        "Hora": "Opcional. Suma puntos a las novedades con hora cercana a la de LG "
                "(además de las horas escritas en la descripción).",
    }, {"N° Novedad": FILA_EXCEL, "Hora": SIN_HORA}),
]


def elegir_columnas(clave: str, df: pd.DataFrame, esperadas: dict, ayudas: dict, especiales: dict,
                    firma: str, mostrar: bool) -> dict:
    """{dato: columna del archivo}, elegido con desplegables (en el paso 1).

    Los desplegables arrancan con lo que se reconoce por nombre. Las columnas opcionales tienen
    una opción especial (sin hora / usar número de fila) que deja el dato afuera del mapa.
    """
    guardado = ss.get(P + "mapa_" + clave, {})
    if guardado.get("_firma") != firma:  # archivo nuevo: arrancar con lo reconocido por nombre
        guardado = {"_firma": firma, **a.mapear_columnas(df, esperadas)[0]}
        for canon, especial in especiales.items():
            guardado.setdefault(canon, especial)
    if mostrar:
        columnas = list(df.columns)
        mapa = {"_firma": firma}
        cols = st.columns(2)
        for k, canon in enumerate(ayudas):
            opciones = ([especiales[canon]] if canon in especiales else []) + columnas
            actual = guardado.get(canon)
            elegida = cols[k % 2].selectbox(
                canon + (" (opcional)" if canon == "Hora" else ""), opciones,
                index=opciones.index(actual) if actual in opciones else None,
                placeholder="Elegí la columna", help=ayudas[canon], key=f"{P}col_{clave}_{canon}_{firma}",
            )
            if elegida is not None:
                mapa[canon] = elegida
        ss[P + "mapa_" + clave] = guardado = mapa
    return {k: v for k, v in guardado.items() if k != "_firma" and v not in especiales.values()}


def archivo(clave: str, titulo: str, esperadas: dict, ayudas: dict, especiales: dict, mostrar: bool):
    """Sube (solo en el paso 1), lee el archivo y resuelve sus columnas.

    Devuelve (tabla original, {dato: columna}) o None si falta algo.
    """
    if mostrar:
        st.markdown(f"**{titulo}**")
        subido = st.file_uploader(titulo, type=["xlsx", "xls", "csv"], key=P + "up_" + clave,
                                  label_visibility="collapsed")
        if subido is not None:
            ss[P + clave] = {"nombre": subido.name, "bytes": subido.getvalue()}
        elif P + clave in ss:
            st.success(f"Cargado: {ss[P + clave]['nombre']}")
    if P + clave not in ss:
        return None
    arch = ss[P + clave]
    try:
        df = leer(arch["nombre"], arch["bytes"])
    except Exception as e:  # archivo dañado o con formato raro
        st.error(f"No se pudo leer el archivo {arch['nombre']}: {e}")
        return None
    firma = a.huella(arch["bytes"])[:12]
    if mostrar:
        st.caption("Indicá qué columna del archivo es cada dato:")
    mapa = elegir_columnas(clave, df, esperadas, ayudas, especiales, firma, mostrar)

    if faltan := [c for c in ayudas if c not in mapa and c not in especiales]:
        if mostrar:
            st.warning("Falta elegir: " + ", ".join(f"**{c}**" for c in faltan) + ".")
        return None
    if repetidas := sorted({c for c in mapa.values() if list(mapa.values()).count(c) > 1}):
        st.error("Elegiste la misma columna para dos datos distintos: " + ", ".join(f"«{c}»" for c in repetidas))
        return None
    if mostrar:
        st.caption("Así se ven las primeras filas:")
        orden = [c for c in ["N° Novedad", "Fecha", "Hora", "Transcripción", "Descripción"] if c in mapa]
        vista = df[[mapa[c] for c in orden]].head(3).set_axis(orden, axis=1)
        vista.insert(orden.index("Fecha") + 1, "Fecha (cómo la entiende la app)",
                     vista["Fecha"].map(lambda v: a.formatear_fecha(a.parsear_fecha(v)) if a.parsear_fecha(v)
                                        else "⚠️ no se entiende"))
        if "Hora" in vista:
            vista["Hora"] = vista["Hora"].map(lambda v: a.formatear_hora(a.parsear_hora(v)) or "⚠️ no se entiende")
        st.dataframe(vista.astype(str), hide_index=True, use_container_width=True)
    return df, mapa


if paso == PASOS[0]:
    st.caption(
        "Subí los dos Excel y elegí qué columna es cada dato. Los originales **no se modifican**: "
        "la app trabaja sobre una copia y el resultado se descarga en un Excel nuevo."
    )
    columnas_pantalla = st.columns(2)
cargados = {}
for k, (clave, titulo, esperadas, ayudas, especiales) in enumerate(ARCHIVOS):
    if paso == PASOS[0]:
        with columnas_pantalla[k], st.container(border=True):
            cargados[clave] = archivo(clave, titulo, esperadas, ayudas, especiales, mostrar=True)
    else:
        cargados[clave] = archivo(clave, titulo, esperadas, ayudas, especiales, mostrar=False)

if not all(cargados.values()):
    if paso == PASOS[0]:
        st.info("Subí los dos archivos y elegí sus columnas para seguir.")
    else:
        st.info("Primero cargá los dos Excel y elegí sus columnas en el paso **1. Carga**.")
    st.stop()

(lg_original, mapa_lg), (pcz_original, mapa_pcz) = cargados["lg"], cargados["pcz"]
lg, pcz = preparar(ss[P + "lg"]["nombre"], ss[P + "lg"]["bytes"],
                   ss[P + "pcz"]["nombre"], ss[P + "pcz"]["bytes"], mapa_lg, mapa_pcz)
archivos = {"lg": ss[P + "lg"], "pcz": ss[P + "pcz"]}
if lg.empty:
    st.error("El archivo de LG no tiene filas.")
    st.stop()

# ------------------------------------------- estado del trabajo (en memoria)
# No se guarda en disco: si se cargan otros archivos, se cierra la app o se recarga la página,
# se empieza de cero.
huella = a.huella(archivos["lg"]["bytes"], archivos["pcz"]["bytes"])
if ss.get(P + "trabajo", {}).get("huella") != huella:
    ss[P + "trabajo"] = a.trabajo_nuevo(huella, len(lg))
    ss[P + "ver"] = ss.get(P + "ver", 0) + 1
    st.rerun()
trabajo = ss[P + "trabajo"]
ss.setdefault(P + "ver", 0)

if paso == PASOS[0]:
    st.header("Archivos")
    c1, c2 = st.columns(2)
    for col, titulo, t in [(c1, "LG", lg), (c2, "PCZ", pcz)]:
        with col:
            fechas = t["fecha"].dropna()
            rango = f"del {a.formatear_fecha(fechas.min())} al {a.formatear_fecha(fechas.max())}" if len(fechas) else ""
            st.markdown(f"**{titulo}**: {len(t)} filas {rango}")
            malas = a.fechas_invalidas(t)
            if len(malas):
                st.warning(f"{len(malas)} fila(s) de {titulo} con fecha que no se pudo interpretar. "
                           "No se descartan: " + ("se muestran igual al asociar, con aviso."
                                                  if titulo == "LG" else
                                                  "aparecen en la sección «sin fecha» de los candidatos."))
                st.dataframe(malas, hide_index=True, use_container_width=True)
    if rep := a.ids_repetidos(pcz):
        st.warning("Hay N° de Novedad repetidos en PCZ (se tratan como una sola novedad): " + ", ".join(rep[:20]))

    st.button("Ir a asociar ➡️", type="primary", on_click=ir_a_paso, args=(PASOS[1],))
    st.stop()

n_avisos_por_fila = [len(x) for x in lg["avisos"]]

# ================================================================== 3. Exportar
if paso == PASOS[2]:
    st.header("Exportar a Excel", anchor=False)
    lg_resto = a.lg_sin_asociar(lg_original, lg, trabajo, mapa_lg)
    pcz_resto = a.pcz_sin_asociar(pcz_original, pcz, trabajo)
    p = a.progreso(trabajo, n_avisos_por_fila)
    m1, m2, m3 = st.columns(3)
    m1.metric("Asociaciones", p["asociaciones"])
    m2.metric("Filas de LG sin asociar", len(lg_resto))
    m3.metric("Novedades de PCZ sin asociar", len(pcz_resto))
    if p["pendientes"]:
        st.info(f"Quedan {p['pendientes']} aviso(s) sin revisar: van a la hoja «LG sin asociar».")
    st.caption("El Excel trae 3 hojas: **Asociaciones** (con las columnas que elijas abajo), **LG sin "
               "asociar** y **PCZ sin asociar** (estas dos con las mismas columnas que los archivos originales).")

    st.subheader("Columnas de la hoja «Asociaciones»", anchor=False)
    opciones = a.columnas_disponibles(lg_original, pcz_original)
    clave_cols = f"{P}cols_{trabajo['huella']}"
    ss.setdefault(P + "cols_elegidas", {})
    defecto = ss[P + "cols_elegidas"].get(trabajo["huella"]) or a.columnas_por_defecto(mapa_lg, mapa_pcz)
    columnas = st.multiselect(
        "Columnas, en el orden en que van a aparecer", opciones, default=[c for c in defecto if c in opciones],
        key=clave_cols, placeholder="Elegí columnas",
        help="El orden de la hoja es el orden en que las elegís: para mover una, sacala (✕) y volvé a "
             "agregarla. Cuando una asociación tiene varios avisos o varias novedades, sus valores se "
             "juntan en la misma celda separados por « | ». «Descripción combinada» = descripción de PCZ + "
             "texto de LG en minúsculas.",
    )
    ss[P + "cols_elegidas"][trabajo["huella"]] = columnas
    if not columnas:
        st.warning("Elegí al menos una columna.")
        st.stop()
    tabla = a.tabla_asociaciones(lg_original, pcz_original, lg, pcz, trabajo, mapa_lg, mapa_pcz, columnas)
    st.caption(f"Vista previa ({len(tabla)} asociación(es)):")
    st.dataframe(tabla.head(20).map(a._texto_celda), hide_index=True, use_container_width=True)

    nombre = st.text_input("Nombre del archivo a descargar", value="asociacion_LG_PCZ")
    # Sacar caracteres que Windows no acepta en nombres de archivo
    nombre = re.sub(r'[\\/:*?"<>|]', "", nombre).strip().removesuffix(".xlsx") or "asociacion_LG_PCZ"
    st.download_button(f"⬇️ Descargar {nombre}.xlsx",
                       a.exportar(lg_original, pcz_original, lg, pcz, trabajo, mapa_lg, mapa_pcz, columnas),
                       f"{nombre}.xlsx", type="primary")
    st.stop()

# ================================================================ 2. Asociación
# Cada fila de LG se trabaja en dos pasos:
#   A) elegir qué aviso(s) del párrafo se van a asociar,
#   B) elegir la(s) novedad(es) de PCZ para esos avisos.
# Cada asociación (avisos -> novedades) se guarda al instante. Los avisos sin novedad se
# descartan. Cuando todos los avisos de la fila están asociados o descartados, se pasa a la siguiente.
n = len(lg)
asociadas_a = a.asociaciones_por_novedad(trabajo)


def _escapar(texto: str) -> str:
    """Evita que el texto del aviso se interprete como markdown en las etiquetas."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|~$<>])", r"\\\1", str(texto))


def borrador() -> dict:
    """Elección en curso de la fila actual (paso, avisos y novedades tildados)."""
    pos, ver = trabajo["posicion"], ss[P + "ver"]
    b = ss.get(P + "borrador")
    if not b or b["fila"] != pos or b["ver"] != ver:
        n_avisos = len(lg.loc[pos, "avisos"])
        pendiente = a.pendientes_de_fila(trabajo["filas"][str(pos)], n_avisos)
        if n_avisos <= 1 and pendiente:  # un solo aviso sin resolver: directo a elegir novedades
            b = {"fila": pos, "ver": ver, "etapa": "pcz", "avisos": list(range(n_avisos)), "novedades": []}
        else:
            b = {"fila": pos, "ver": ver, "etapa": "avisos", "avisos": [], "novedades": []}
        ss[P + "borrador"] = b
    return b


def fila_actual() -> dict:
    return trabajo["filas"][str(trabajo["posicion"])]


def mover(destino: int):
    trabajo["posicion"] = max(0, min(n - 1, destino))
    ss[P + "ver"] += 1


def tildar(lista: str, valor, clave: str):
    elegidos = borrador()[lista]
    if ss[clave] and valor not in elegidos:
        elegidos.append(valor)
    elif not ss[clave] and valor in elegidos:
        elegidos.remove(valor)


def todos_los_avisos():
    b = borrador()
    b["avisos"] = list(range(len(lg.loc[trabajo["posicion"], "avisos"])))
    ss[P + "ver"] += 1
    ss[P + "borrador"] = {**b, "ver": ss[P + "ver"]}


def ir_a_novedades():
    b = borrador()
    if not b["avisos"]:
        ss[P + "msg"] = ("error", "Tildá al menos un aviso.")
        return
    b["etapa"] = "pcz"


def volver_a_avisos():
    borrador()["etapa"] = "avisos"


def siguiente_fila():
    pos = trabajo["posicion"]
    if pos < n - 1:
        mover(pos + 1)
        return
    # Última fila: si no queda nada sin revisar, directo a exportar
    quedan = a.progreso(trabajo, n_avisos_por_fila)["pendientes"]
    if quedan:
        ss[P + "msg"] = ("info", f"Llegaste a la última fila. Quedan {quedan} aviso(s) sin revisar en otras "
                                 "filas; si igual querés terminar, tocá «📥 Exportar».")
        ss[P + "ver"] += 1
    else:
        ir_a_paso(PASOS[2])


def seguir_si_completa(mensaje: str):
    """Si la fila ya no tiene avisos pendientes pasa a la siguiente; si no, vuelve al paso 1."""
    pos = trabajo["posicion"]
    quedan = len(a.pendientes_de_fila(fila_actual(), n_avisos_por_fila[pos]))
    if quedan:
        ss[P + "msg"] = ("success", f"{mensaje} Quedan {quedan} aviso(s) en esta fila: asocialos o descartalos.")
        ss[P + "ver"] += 1
    else:
        siguiente_fila()


def asociar():
    """Guarda la asociación avisos -> novedades elegida."""
    pos, b, d = trabajo["posicion"], borrador(), fila_actual()
    if not b["novedades"]:
        return
    grupos = d["grupos"] + [{"avisos": b["avisos"], "novedades": b["novedades"]}]
    a.registrar(trabajo, pos, grupos, set(d["descartados"]) - set(b["avisos"]))
    seguir_si_completa("Asociado.")


def descartar():
    """Marca los avisos tildados como sin novedad en PCZ."""
    pos, b, d = trabajo["posicion"], borrador(), fila_actual()
    if not b["avisos"]:
        return
    a.registrar(trabajo, pos, d["grupos"], set(d["descartados"]) | set(b["avisos"]))
    seguir_si_completa("Descartado.")


def recuperar(aviso: int):
    d = fila_actual()
    a.registrar(trabajo, trabajo["posicion"], d["grupos"], set(d["descartados"]) - {aviso})
    ss[P + "ver"] += 1


def quitar_grupo(i: int):
    d = fila_actual()
    a.registrar(trabajo, trabajo["posicion"], d["grupos"][:i] + d["grupos"][i + 1:], d["descartados"])
    ss[P + "ver"] += 1


st.html("""<style>
/* Tarjetas que se eligen con un clic (avisos en el paso 1, novedades en el paso 2) */
[class*="st-key-tarjeta_"] { cursor: pointer; }
[class*="st-key-tarjeta_"]:has(input:checked) { background: rgba(27, 74, 122, 0.10); border-color: #1B4A7A; }
mark { background: #FFE27A; color: inherit; padding: 0 .1em; border-radius: 2px; }
/* Tarjetas fijas de la tabla LG ↔ PCZ */
.tj { border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 0.5rem; padding: 0.6rem 0.8rem;
      margin-bottom: 0.5rem; line-height: 1.45; }
.tj-lg, [class*="st-key-tarjeta_a_"] { border-left: 4px solid #1D2A33 !important; }
.tj-lg { font-size: 0.9rem; }
.tj-pcz { border-left: 4px solid #1B4A7A; background: rgba(27, 74, 122, 0.07); }
.tj-vacia { border-style: dashed; opacity: 0.55; text-align: center; font-size: 0.9rem; }
.tj-num { font-size: 0.78rem; font-weight: 600; opacity: 0.7; margin-bottom: 0.15rem; }
.tj-aviso { font-size: 0.8rem; color: #8A5E00; margin-top: 0.25rem; }
.col-titulo { font-size: 0.85rem; font-weight: 600;
              opacity: 0.55; margin-bottom: 0.3rem; }
.flecha { text-align: center; font-size: 1.4rem; opacity: 0.45; padding-top: 0.6rem; }
.pasos { font-size: 0.95rem; margin: 0.2rem 0 0.6rem 0; }
.pasos .off { opacity: 0.4; }
</style>""")

pos = trabajo["posicion"]
fila = lg.loc[pos]
guardada = fila_actual()
b = borrador()
ver = ss[P + "ver"]
grupos = guardada["grupos"]
n_avisos = len(fila["avisos"])
pendientes = a.pendientes_de_fila(guardada, n_avisos)
desc_por_id = dict(zip(pcz["id"], pcz["descripcion"]))
fecha_por_id = dict(zip(pcz["id"], pcz["fecha"]))
hora_por_id = dict(zip(pcz["id"], pcz["hora"]))


def html_lg(texto: str) -> str:
    return f"<div class='tj tj-lg'>{a.resaltar(texto, set())}</div>"


def html_pcz(nov: str) -> str:
    otras = [f + 1 for f in asociadas_a.get(nov, []) if f != pos]
    aviso_otras = (f"<div class='tj-aviso'>⚠️ también asociada a LG fila {', '.join(map(str, otras))}</div>"
                   if otras else "")
    return (f"<div class='tj tj-pcz'><div class='tj-num'>N° {nov} · {a.formatear_fecha(fecha_por_id.get(nov))}"
            f"{' · ' + a.formatear_hora(hora_por_id.get(nov)) if a.formatear_hora(hora_por_id.get(nov)) else ''}"
            f"</div>{a.resaltar(desc_por_id.get(nov, '(no está en el archivo de PCZ)'), set())}{aviso_otras}</div>")


def html_vacia(texto: str) -> str:
    return f"<div class='tj tj-vacia'>{texto}</div>"


def fila_tabla(izquierda, derecha, flecha: bool = True):
    """Una fila de la tabla: tarjetas de LG a la izquierda y de PCZ a la derecha, a la misma altura."""
    c1, c2, c3 = st.columns([10, 1, 10])
    with c1:
        izquierda()
    c2.markdown(f"<div class='flecha'>{'→' if flecha else ''}</div>", unsafe_allow_html=True)
    with c3:
        derecha()


def titulos_tabla(derecha: str):
    c1, _, c3 = st.columns([10, 1, 10])
    c1.markdown("<div class='col-titulo'>📘 Libro de Guardia</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='col-titulo'>📋 {derecha}</div>", unsafe_allow_html=True)


# ----------------------------------------------------------- barra superior
p = a.progreso(trabajo, n_avisos_por_fila)
nav = st.columns([1, 4, 1], vertical_alignment="center")
nav[0].button("⬅️ Anterior", on_click=mover, args=(pos - 1,), disabled=pos == 0, use_container_width=True)
with nav[1]:
    st.markdown(
        f"<div style='text-align:center'><b>Fila {pos + 1} de {n}</b> &nbsp;·&nbsp; Avisos: ✅ {p['asociados']} "
        f"asociados &nbsp;·&nbsp; 🗑️ {p['descartados']} descartados</div>", unsafe_allow_html=True)
    st.progress((p["avisos"] - p["pendientes"]) / p["avisos"] if p["avisos"] else 1.0)
if pos < n - 1:
    nav[2].button("➡️ Siguiente", on_click=mover, args=(pos + 1,), use_container_width=True)
else:
    nav[2].button("📥 Exportar", type="primary", on_click=ir_a_paso, args=(PASOS[2],), use_container_width=True)

# --------------------------------------------------------------- fila de LG
with st.container(border=True):
    hora = a.formatear_hora(fila["hora"]) if pd.notna(fila["hora"]) else (
        "" if pd.isna(fila["hora_original"]) else str(fila["hora_original"]))
    h1, h2 = st.columns([4, 1], vertical_alignment="center")
    h1.subheader(f"LG fila {pos + 1}", anchor=False)
    h1.caption(f"{a.formatear_fecha(fila['fecha'])} · {hora or 'sin hora'}")
    estado = f"⏳ {len(pendientes)} aviso(s) pendiente(s)" if pendientes else "✅ Fila completa"
    h2.markdown(f"<div style='text-align:right'>{estado}</div>", unsafe_allow_html=True)
    en_paso_1 = b["etapa"] == "avisos"
    st.markdown(
        "<div class='pasos'>"
        + ("<b>① Elegí los avisos</b>" if en_paso_1 else "<span class='off'>① Elegí los avisos</span>")
        + " &nbsp;›&nbsp; "
        + ("<b>② Elegí las novedades de PCZ</b>" if not en_paso_1
           else "<span class='off'>② Elegí las novedades de PCZ</span>")
        + "</div>", unsafe_allow_html=True)
    if fila["fecha"] is None:
        st.error(
            f"La fecha de esta fila no se pudo interpretar (viene como «{fila['fecha_original']}»). "
            "No se pueden proponer candidatos por fecha: usá el buscador para buscar en todas las novedades."
        )
    if not n_avisos:
        st.warning("Esta fila no tiene transcripción.")

    def tabla_guardada(elegibles: bool):
        """Tabla LG ↔ PCZ con lo guardado. Con elegibles=True, los avisos son tarjetas para tildar."""
        dibujados = set()
        for k, f in enumerate(a.filas_de_tabla(grupos, n_avisos, guardada["descartados"])):
            grupo = f["novedades"] and next(i for i, g in enumerate(grupos) if g["avisos"] == f["avisos"]
                                           and g["novedades"] == f["novedades"])

            def izquierda(f=f):
                for i in f["avisos"]:
                    if elegibles and i not in dibujados:
                        dibujados.add(i)
                        with st.container(border=True, key=f"tarjeta_a_{ver}_{pos}_{i}"):
                            clave = f"{P}aviso_{ver}_{pos}_{i}"
                            st.checkbox(f"\\[{i + 1}\\] {_escapar(fila['avisos'][i])}", value=i in b["avisos"],
                                        key=clave, on_change=tildar, args=("avisos", i, clave))
                    else:
                        st.markdown(html_lg(f"[{i + 1}] {fila['avisos'][i]}"), unsafe_allow_html=True)

            def derecha(f=f, k=k, grupo=grupo):
                if f["descartado"]:
                    st.markdown(html_vacia("🗑️ descartado (sin novedad en PCZ)"), unsafe_allow_html=True)
                    st.button("↩️ Recuperar", key=f"{P}recuperar_{ver}_{pos}_{k}", on_click=recuperar,
                              args=(f["avisos"][0],))
                    return
                if not f["novedades"]:
                    st.markdown(html_vacia("pendiente"), unsafe_allow_html=True)
                    return
                st.markdown("".join(html_pcz(nv) for nv in f["novedades"]), unsafe_allow_html=True)
                st.button("🗑️ Quitar esta asociación", key=f"{P}quitar_{ver}_{pos}_{k}",
                          on_click=quitar_grupo, args=(grupo,))

            fila_tabla(izquierda, derecha, flecha=bool(f["novedades"]))

    if en_paso_1:
        # ------------------------------------------- Paso 1: elegir avisos
        st.caption("Tocá uno o varios avisos (las tarjetas de la izquierda) y después «Elegir novedades», "
                   "o «Descartar» si no tienen novedad en PCZ.")
        titulos_tabla("Novedades PCZ asociadas")
        tabla_guardada(elegibles=True)
        c = st.columns([1.3, 1.3, 1, 2])
        c[0].button("➡️ Elegir novedades", type="primary", on_click=ir_a_novedades,
                    disabled=not b["avisos"], use_container_width=True)
        c[1].button("🗑️ Descartar", on_click=descartar, disabled=not b["avisos"], use_container_width=True,
                    help="Los avisos tildados no tienen novedad en PCZ: van a la hoja «LG sin asociar».")
        if n_avisos > 1:
            c[2].button("☑ Todos", on_click=todos_los_avisos, use_container_width=True,
                        help="Tilda todos los avisos del párrafo.")
    else:
        # ------------------------------------- Paso 2: nueva asociación
        st.caption("Tildá abajo una o varias novedades: van apareciendo a la derecha. Después tocá «Asociar».")
        titulos_tabla("Novedades elegidas")

        def izquierda_nueva():
            for i in b["avisos"]:
                st.markdown(html_lg(f"[{i + 1}] {fila['avisos'][i]}"), unsafe_allow_html=True)

        def derecha_nueva():
            if b["novedades"]:
                st.markdown("".join(html_pcz(nv) for nv in b["novedades"]), unsafe_allow_html=True)
            else:
                st.markdown(html_vacia("todavía ninguna ↓ elegila en la lista de abajo"), unsafe_allow_html=True)

        fila_tabla(izquierda_nueva, derecha_nueva)
        c = st.columns([1.3, 1.3, 1.3, 1.7])
        c[0].button("✅ Asociar", type="primary", on_click=asociar, disabled=not b["novedades"],
                    use_container_width=True)
        c[1].button("🗑️ Descartar", on_click=descartar, disabled=not b["avisos"], use_container_width=True,
                    help="Estos avisos no tienen novedad en PCZ: van a la hoja «LG sin asociar».")
        c[2].button("⬅️ Volver a los avisos", on_click=volver_a_avisos, use_container_width=True)
        if grupos:
            with st.expander(f"Asociaciones ya guardadas en esta fila ({len(grupos)})"):
                titulos_tabla("Novedades PCZ asociadas")
                tabla_guardada(elegibles=False)

# -------------------------------------------------------------- candidatos
if b["etapa"] == "pcz":
    st.subheader("Novedades de PCZ " + (f"del {a.formatear_fecha(fila['fecha'])}" if fila["fecha"] else ""),
                 anchor=False)
    f1, f2 = st.columns([3, 2], vertical_alignment="bottom")
    busqueda = f1.text_input("🔎 Buscar en las novedades", key=f"{P}buscar_{pos}",
                             placeholder="Ej.: Boulogne 14  (filtra por N° o descripción)",
                             label_visibility="collapsed")
    vecinos = f2.toggle("Ver también día anterior / siguiente", key=P + "vecinos",
                        help="Para eventos que cruzan la medianoche. Se muestran marcados como OTRO DÍA.")

    # El puntaje se calcula solo con el texto de los avisos elegidos
    fila_sel = a.fila_con_avisos(fila, b["avisos"])
    if fila["fecha"] is None:
        # Sin fecha en LG: se busca en todas las novedades, solo si el usuario escribe algo
        cands = a.todas_las_novedades(fila_sel, pcz[pcz["fecha"].notna()])
    else:
        cands = a.candidatos(fila_sel, pcz, vecinos)
    del_dia = int((~cands["otro_dia"]).sum())
    cands = a.buscar(cands, busqueda)
    sin_fecha = a.buscar(a.pcz_sin_fecha(fila_sel, pcz), busqueda)

    if fila["fecha"] is not None:
        st.caption(f"{del_dia} novedad(es) ese día"
                   + (f" · {len(cands)} coinciden con la búsqueda" if busqueda else "")
                   + " · ordenadas por parecido con los avisos elegidos (en amarillo, lo que coincide)",
                   help="Puntaje: número compartido 3 (1 si es de una cifra) · palabra compartida 1 · "
                        "hora cercana hasta 3.")

    en_esta_fila = {nv: g["avisos"] for g in grupos for nv in g["novedades"]}

    # Se dibujan de a tandas (las de mayor puntaje primero): dibujar cientos de tarjetas en
    # cada clic hace lenta la pantalla. El buscador sigue buscando entre todas.
    POR_TANDA = 15
    clave_limite = f"{P}limite_{pos}"
    limite = ss.get(clave_limite, POR_TANDA)

    def ampliar(cantidad: int):
        ss[clave_limite] = cantidad

    def mostrar(c: pd.DataFrame, inicio: int, etiqueta: str | None, seccion: str) -> int:
        """Dibuja las tarjetas de `c` (hasta el límite, más las ya tildadas). Devuelve cuántas dibujó."""
        visibles = c.head(limite)
        tildadas = c[c["id"].isin(b["novedades"]) & ~c.index.isin(visibles.index)]
        visibles = pd.concat([visibles, tildadas])
        for k, (_, cand) in enumerate(visibles.iterrows(), start=inicio):
            nov = cand["id"]
            elegida = nov in b["novedades"]
            otras = [f + 1 for f in asociadas_a.get(nov, []) if f != pos]
            with st.container(border=True, key=f"tarjeta_n_{ver}_{pos}_{cand['fila_pcz']}"):
                c1, c2 = st.columns([1, 5])
                clave = f"{P}sel_{ver}_{pos}_{cand['fila_pcz']}"
                c1.checkbox(f"\\[{k}\\] N° {nov}", value=elegida, key=clave, on_change=tildar,
                            args=("novedades", nov, clave))
                hora_cand = a.formatear_hora(cand["hora"])
                c1.caption(f"Puntaje **{cand['puntaje']}**" + (f" · 🕒 {hora_cand}" if hora_cand else ""))
                marcas = []
                if etiqueta:
                    marcas.append(f"<span style='background:#E8B400;color:#1D2A33;padding:1px 6px;border-radius:4px;"
                                  f"font-weight:600'>{etiqueta} · {a.formatear_fecha(cand['fecha'])}</span>")
                if otras:
                    marcas.append(f"<span style='background:#1B4A7A;color:#fff;padding:1px 6px;border-radius:4px'>"
                                  f"🔗 ya asociada a LG fila {', '.join(map(str, otras))}</span>")
                if nov in en_esta_fila:
                    marcas.append("<span style='background:#2F7D4A;color:#fff;padding:1px 6px;border-radius:4px'>"
                                  "ya asociada en esta fila (aviso "
                                  + ", ".join(str(x + 1) for x in en_esta_fila[nov]) + ")</span>")
                c2.markdown(
                    (" ".join(marcas) + "<br>" if marcas else "")
                    + a.resaltar(cand["descripcion"], cand["comunes"], cand["hora_suma"])
                    + f"<br><span style='opacity:0.6;font-size:0.85rem'>{cand['detalle']}</span>",
                    unsafe_allow_html=True,
                )
                if elegida and otras:
                    c2.warning(f"Ya asociada a LG fila {', '.join(map(str, otras))}.")
        if len(c) > len(visibles):
            resto = len(c) - len(visibles)
            st.caption(f"Se muestran {len(visibles)} de {len(c)}. Quedan {resto} con menor puntaje.")
            k1, k2, _ = st.columns([1, 1, 3])
            k1.button(f"⬇️ Mostrar {min(POR_TANDA, resto)} más", key=f"{P}mas_{seccion}_{ver}_{pos}",
                      on_click=ampliar, args=(limite + POR_TANDA,), use_container_width=True)
            k2.button(f"Mostrar todas ({len(c)})", key=f"{P}todas_{seccion}_{ver}_{pos}",
                      on_click=ampliar, args=(len(c),), use_container_width=True)
        return len(visibles)

    mismo = cands[~cands["otro_dia"]]
    otro = cands[cands["otro_dia"]]
    if fila["fecha"] is None:
        if not busqueda:
            st.info("Escribí en el buscador para buscar entre todas las novedades de PCZ.")
            dibujadas = 0
        else:
            dibujadas = mostrar(cands, 1, "SIN FECHA EN LG", "todas")
    else:
        if mismo.empty:
            st.info("No hay novedades de PCZ " + ("que coincidan con la búsqueda " if busqueda else "")
                    + f"con fecha {a.formatear_fecha(fila['fecha'])}.")
        dibujadas = mostrar(mismo, 1, None, "mismo")
        if vecinos:
            st.markdown("##### 🌙 OTRO DÍA (día anterior / siguiente)")
            if otro.empty:
                st.caption("No hay novedades del día anterior ni del siguiente.")
            dibujadas += mostrar(otro, dibujadas + 1, "OTRO DÍA", "otro")
    if len(sin_fecha):
        with st.expander(f"Novedades de PCZ sin fecha reconocible ({len(sin_fecha)})"):
            mostrar(sin_fecha, dibujadas + 1, "SIN FECHA", "sin_fecha")

# Atajos de teclado: se engancha un único listener en la página (se reemplaza en cada recarga)
# y solo actúa si los botones de esta pantalla están visibles.
components.html("""
<script>
const doc = window.parent.document;
if (window.parent.__lgpczTeclas) doc.removeEventListener('keydown', window.parent.__lgpczTeclas);
window.parent.__lgpczTeclas = function (e) {
  const t = e.target;
  const escribe = t && (t.tagName === 'TEXTAREA' || t.isContentEditable ||
    (t.tagName === 'INPUT' && !['checkbox', 'radio', 'button'].includes(t.type)));
  if (escribe || e.ctrlKey || e.altKey || e.metaKey || e.repeat) return;
  const boton = (txt) => Array.from(doc.querySelectorAll('button'))
    .find(b => b.innerText.trim().endsWith(txt) && !b.disabled);
  if (!Array.from(doc.querySelectorAll('button')).some(b => b.innerText.trim().endsWith('Anterior'))) return;
  if (/^[1-9]$/.test(e.key)) {
    const marca = '[' + e.key + ']';
    const label = Array.from(doc.querySelectorAll('[data-testid="stCheckbox"] label'))
      .find(l => l.innerText.trim().startsWith(marca));
    const casilla = label && label.querySelector('input');
    if (casilla) { e.preventDefault(); casilla.click(); }
    return;
  }
  let b = null;
  if (e.key === 'Enter') {
    b = boton('Asociar') || boton('Elegir novedades');
  } else {
    const mapa = {'ArrowLeft': 'Anterior', 'ArrowRight': 'Siguiente', 'd': 'Descartar', 'D': 'Descartar'};
    if (!mapa[e.key]) return;
    b = boton(mapa[e.key]);
  }
  e.preventDefault();
  if (b) b.click();
};
doc.addEventListener('keydown', window.parent.__lgpczTeclas);

// Tarjetas (avisos y novedades): un clic en cualquier parte de la tarjeta la tilda o destilda.
if (window.parent.__lgpczClic) doc.removeEventListener('click', window.parent.__lgpczClic);
window.parent.__lgpczClic = function (e) {
  // La casilla y su texto ya funcionan solos; botones, links y campos tampoco se tocan
  if (e.target.closest('input, label, button, a, textarea, [data-baseweb="select"]')) return;
  const tarjeta = e.target.closest('[class*="st-key-tarjeta_"]');
  const casilla = tarjeta && tarjeta.querySelector('[data-testid="stCheckbox"] input');
  if (casilla) casilla.click();
};
doc.addEventListener('click', window.parent.__lgpczClic);
</script>
""", height=0)
