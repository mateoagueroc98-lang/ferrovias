"""Módulo: asociación manual de filas del Libro de Guardia (LG) con novedades del PCZ."""
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src import asociacion_lg_pcz as a

# Todo el contenido de este módulo al 90 % (el menú lateral y los otros módulos quedan igual)
st.html("<style>[data-testid='stMainBlockContainer'] { zoom: 0.9; }</style>")

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
    ss[P + "trabajo"] = a.trabajo_nuevo(huella)
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
                           "No se descartan: " + ("sus avisos aparecen en la sección «sin fecha» de los candidatos."
                                                  if titulo == "LG" else
                                                  "se recorren igual, con aviso, y se busca a mano en el LG."))
                st.dataframe(malas, hide_index=True, use_container_width=True)
    if rep := a.ids_repetidos(pcz):
        st.warning("Hay N° de Novedad repetidos en PCZ: " + ", ".join(rep[:20]))

    st.button("Ir a asociar ➡️", type="primary", on_click=ir_a_paso, args=(PASOS[1],))
    st.stop()

avisos_lg = a.tabla_avisos(lg)

# ================================================================== 3. Exportar
if paso == PASOS[2]:
    st.header("Exportar a Excel", anchor=False)
    lg_resto = a.lg_sin_asociar(lg_original, lg, trabajo, mapa_lg)
    p = a.progreso(trabajo, len(pcz))
    m1, m2, m3 = st.columns(3)
    m1.metric("Novedades de PCZ asociadas", p["asociadas"])
    m2.metric("Novedades de PCZ sin asociar", p["total"] - p["asociadas"])
    m3.metric("Filas de LG sin asociar", len(lg_resto))
    if p["pendientes"]:
        st.info(f"Quedan {p['pendientes']} novedad(es) de PCZ sin revisar: salen en la hoja «Asociaciones» "
                "solo con su texto de PCZ.")
    st.caption("El Excel trae 2 hojas: **Asociaciones** (todas las novedades de PCZ ordenadas por día: una fila "
               "por asociación y una por cada novedad sin asociar) y **LG sin asociar** (con las mismas "
               "columnas que el archivo original).")

    st.subheader("Hoja «Asociaciones»", anchor=False)
    numero_inicial = st.number_input(
        "N° de la primera fila", min_value=0, value=ss.get(P + "numero_inicial", 1), step=1,
        help="Poné el número que sigue en tu tabla madre: las demás filas siguen de a uno hacia abajo.")
    ss[P + "numero_inicial"] = numero_inicial  # se recuerda si vas y volvés de este paso
    tabla = a.tabla_asociaciones(lg, pcz, trabajo, int(numero_inicial))
    st.caption(f"Vista previa ({len(tabla)} fila(s)):")
    vista = tabla.head(20).copy()
    vista["Fecha"] = vista["Fecha"].map(lambda f: f"{f.day}/{f.month}/{f.year}" if hasattr(f, "day") else f)
    st.dataframe(vista.map(lambda v: "" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v)),
                 hide_index=True, use_container_width=True)

    nombre = st.text_input("Nombre del archivo a descargar", value="asociacion_LG_PCZ")
    # Sacar caracteres que Windows no acepta en nombres de archivo
    nombre = re.sub(r'[\\/:*?"<>|]', "", nombre).strip().removesuffix(".xlsx") or "asociacion_LG_PCZ"
    st.download_button(f"⬇️ Descargar {nombre}.xlsx",
                       a.exportar(lg_original, lg, pcz, trabajo, mapa_lg, int(numero_inicial)),
                       f"{nombre}.xlsx", type="primary")
    st.stop()

# ================================================================ 2. Asociación
# La app recorre los días del PCZ. En cada día se ven todas sus novedades: se eligen una o varias
# (paso 1) y después los avisos del LG que les corresponden (paso 2) para asociarlas, o se descartan
# si no tienen nada en el LG. Lo ya resuelto sigue a la vista en gris hasta cambiar de día.
dias = a.dias_pcz(pcz)
n_dias = len(dias)
trabajo["dia"] = min(trabajo["dia"], n_dias - 1)
asociados_a = a.novedades_por_aviso(trabajo)


def del_dia() -> list[int]:
    return a.novedades_del_dia(pcz, dias[trabajo["dia"]])


def borrador() -> dict:
    """Elección en curso del día actual: paso, novedades y avisos tildados."""
    dia, ver = trabajo["dia"], ss[P + "ver"]
    b = ss.get(P + "borrador")
    if not b or b["dia"] != dia or b["ver"] != ver:
        todas, pend = del_dia(), a.pendientes(trabajo, del_dia())
        if len(todas) == 1 and pend:  # una sola novedad en el día: directo a elegir avisos
            b = {"dia": dia, "ver": ver, "etapa": "lg", "novedades": list(pend), "avisos": []}
        else:
            b = {"dia": dia, "ver": ver, "etapa": "pcz", "novedades": [], "avisos": []}
        ss[P + "borrador"] = b
    return b


def mover(destino: int):
    trabajo["dia"] = max(0, min(n_dias - 1, destino))
    ss[P + "ver"] += 1


def tildar(lista: str, valor, clave: str):
    elegidos = borrador()[lista]
    if ss[clave] and valor not in elegidos:
        elegidos.append(valor)
    elif not ss[clave] and valor in elegidos:
        elegidos.remove(valor)


def todas_las_pendientes():
    b = borrador()
    b["novedades"] = a.pendientes(trabajo, del_dia())
    ss[P + "ver"] += 1
    ss[P + "borrador"] = {**b, "ver": ss[P + "ver"]}


def ir_a_avisos():
    b = borrador()
    if b["novedades"]:
        b["etapa"] = "lg"


def volver_a_novedades():
    borrador()["etapa"] = "pcz"


def seguir():
    """Si el día quedó completo pasa al siguiente (o a exportar); si no, vuelve al paso 1."""
    dia = trabajo["dia"]
    if a.pendientes(trabajo, del_dia()):
        ss[P + "ver"] += 1
    elif dia < n_dias - 1:
        mover(dia + 1)
    elif quedan := a.progreso(trabajo, len(pcz))["pendientes"]:
        ss[P + "msg"] = ("info", f"Llegaste al último día. Quedan {quedan} novedad(es) sin revisar en otros "
                                 "días; si igual querés terminar, tocá «📥 Exportar».")
        ss[P + "ver"] += 1
    else:
        ir_a_paso(PASOS[2])


def asociar():
    b = borrador()
    if b["novedades"] and b["avisos"]:
        a.asociar(trabajo, b["novedades"], b["avisos"])
        seguir()


def descartar():
    b = borrador()
    if b["novedades"]:
        a.descartar(trabajo, b["novedades"])
        seguir()


def desechar(k: int):
    """🗑️ al lado de una tarjeta: descarta solo esa novedad, sin tocar lo tildado en las demás."""
    a.descartar(trabajo, [k])
    b = borrador()
    if k in b["novedades"]:
        b["novedades"].remove(k)
    if not b["novedades"]:
        b["etapa"] = "pcz"
    if not a.pendientes(trabajo, del_dia()):
        seguir()


def marcar(k: int, color: str):
    a.marcar(trabajo, k, color)


def quitar(i: int):
    a.quitar_asociacion(trabajo, i)
    ss[P + "ver"] += 1


def recuperar(k: int):
    a.recuperar(trabajo, k)
    ss[P + "ver"] += 1


st.html("""<style>
/* Tarjetas que se eligen con un clic (novedades de PCZ en el paso 1, avisos del LG en el paso 2) */
[class*="st-key-tarjeta_"] { cursor: pointer; }
[class*="st-key-tarjeta_p"] { border-left: 4px solid #D41920 !important; }
[class*="st-key-tarjeta_l"] { border-left: 4px solid #1C1A19 !important; }
[class*="st-key-tarjeta_"]:has(input:checked) { background: rgba(212, 25, 32, 0.08); border-color: #D41920; }
mark { background: #FFE27A; color: inherit; padding: 0 .1em; border-radius: 2px; }
/* Tarjetas fijas */
.tj { border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 0.5rem; padding: 0.6rem 0.8rem;
      margin-bottom: 0.5rem; line-height: 1.45; }
.tj-lg { border-left: 4px solid #1C1A19; font-size: 0.9rem; }
.tj-pcz { border-left: 4px solid #D41920;
          background: linear-gradient(90deg, rgba(212, 25, 32, 0.08), rgba(212, 25, 32, 0.02)); }
.tj-hecha { opacity: 0.5; filter: grayscale(1); }
/* Marcas: la tarjeta toma el color con el que se va a resaltar su fila en el Excel */
.tj-pcz.tj-amarilla { background: #FFF3B0; }
.tj-pcz.tj-naranja { background: #FFD9A8; }
.tj-hecha.tj-amarilla, .tj-hecha.tj-naranja { filter: none; opacity: 0.6; }
[class*="st-key-tarjeta_p"][class*="_amarilla"]:has(input) { background: #FFF3B0; }
[class*="st-key-tarjeta_p"][class*="_naranja"]:has(input) { background: #FFD9A8; }
/* Botonera chica a la izquierda de cada novedad: 🗑️ descartar · ! amarilla · !! naranja */
[class*="st-key-botonera_"] { gap: 0.25rem; }
[class*="st-key-bt_"], [class*="st-key-bt_"] > div { width: 100% !important; }
[class*="st-key-bt_"] button { min-height: 1.7rem; height: 1.7rem; padding: 0; width: 100%;
                               font-weight: 800; line-height: 1; color: #1C1A19; }
[class*="st-key-bt_tacho"] button { background: #E4E2E0 !important; border: 1px solid #C9C6C3; }
[class*="st-key-bt_amarilla"] button { background: #FFE45C !important; border: 1px solid #C98A00; }
[class*="st-key-bt_naranja"] button { background: #FFA733 !important; border: 1px solid #C46A00; }
[class*="st-key-bt_amarilla"]:not([class*="_on"]) button,
[class*="st-key-bt_naranja"]:not([class*="_on"]) button { opacity: 0.5; }
[class*="st-key-bt_"][class*="_on"] button { box-shadow: inset 0 0 0 2px #1C1A19; }
[class*="st-key-bt_"] button:hover { opacity: 1; color: #1C1A19; filter: brightness(0.95); }
.tj-vacia { border-style: dashed; opacity: 0.55; text-align: center; font-size: 0.9rem; }
.tj-num { font-size: 0.78rem; font-weight: 600; opacity: 0.7; margin-bottom: 0.15rem; }
.tj-aviso { font-size: 0.8rem; color: #8A5E00; margin-top: 0.25rem; }
.col-titulo { font-size: 0.85rem; font-weight: 600; opacity: 0.55; margin-bottom: 0.3rem; }
.flecha { text-align: center; font-size: 1.4rem; opacity: 0.45; padding-top: 0.6rem; }
/* Streamlit envuelve el contenedor en un stLayoutWrapper de su mismo tamaño: lo pegajoso es el envoltorio */
[data-testid="stLayoutWrapper"]:has(> .st-key-barra_acciones) { position: sticky; bottom: 0; z-index: 50; }
.st-key-barra_acciones { padding: 0.7rem 0 0.8rem;
                         background: rgba(244, 243, 242, 0.94); backdrop-filter: blur(4px);
                         border-top: 1px solid rgba(28, 26, 25, 0.15);
                         box-shadow: 0 -8px 14px -10px rgba(28, 26, 25, 0.35); }
.pasos { font-size: 0.95rem; margin: 0.2rem 0 0.6rem 0; }
.pasos .off { opacity: 0.4; }
</style>""")

dia_idx = trabajo["dia"]
dia = dias[dia_idx]
b = borrador()
ver = ss[P + "ver"]
novedades_dia = del_dia()
pend_dia = a.pendientes(trabajo, novedades_dia)
aviso_por_clave = avisos_lg.set_index("clave")
asociacion_de = a.asociacion_de(trabajo)


def titulo_novedad(k: int) -> str:
    hora = a.formatear_hora(pcz.loc[k, "hora"])
    return f"N° {pcz.loc[k, 'id']}" + (f" · {hora}" if hora else "")


def color_de(k: int) -> str:
    return trabajo.get("marcas", {}).get(k) or "sin"


def html_pcz(k: int, hecha: bool = False) -> str:
    return (f"<div class='tj tj-pcz tj-{color_de(k)}{' tj-hecha' if hecha else ''}'><div class='tj-num'>{titulo_novedad(k)}</div>"
            f"{a.resaltar(pcz.loc[k, 'descripcion'] or '(sin descripción)', set())}</div>")


def html_aviso(clave_aviso: str, hecha: bool = False, novedades_propias=()) -> str:
    av = aviso_por_clave.loc[clave_aviso]
    hora = a.formatear_hora(av["hora"])
    otras = [pcz.loc[k, "id"] for k in asociados_a.get(clave_aviso, []) if k not in novedades_propias]
    aviso_otras = (f"<div class='tj-aviso'>⚠️ también asociado a N° {', '.join(otras)}</div>" if otras else "")
    return (f"<div class='tj tj-lg{' tj-hecha' if hecha else ''}'><div class='tj-num'>LG fila {av['fila_lg'] + 1}"
            f" · {a.formatear_fecha(av['fecha'])}{' · ' + hora if hora else ''}</div>"
            f"{a.resaltar(av['texto'], set())}{aviso_otras}</div>")


def con_botonera(k: int, tarjeta, tacho: bool = True):
    """Tarjeta de una novedad con sus botones chicos a la izquierda (🗑️ si está pendiente, ! y !!)."""
    color = color_de(k)
    cb, cc = st.columns([1, 8], gap="small")
    with cb, st.container(key=f"botonera_{ver}_{k}"):
        if tacho:
            st.button("🗑️", key=f"bt_tacho_{ver}_{k}", on_click=desechar, args=(k,),
                      help="Descartar esta novedad: sale en el Excel solo con su texto de PCZ.")
        for marca, texto, nombre in [("amarilla", "!", "amarillo"), ("naranja", "!!", "naranja")]:
            activa = color == marca
            st.button(texto, key=f"bt_{marca}_{ver}_{k}{'_on' if activa else ''}", on_click=marcar, args=(k, marca),
                      help=("Sacar la marca" if activa else f"Resaltar en {nombre} su fila del Excel final"))
    with cc:
        tarjeta()


def html_vacia(texto: str, hecha: bool = False) -> str:
    return f"<div class='tj tj-vacia{' tj-hecha' if hecha else ''}'>{texto}</div>"


def fila_tabla(izquierda, derecha, flecha: bool = True):
    """Una fila de la tabla: PCZ a la izquierda y LG a la derecha, a la misma altura."""
    c1, c2, c3 = st.columns([10, 1, 10])
    with c1:
        izquierda()
    c2.markdown(f"<div class='flecha'>{'→' if flecha else ''}</div>", unsafe_allow_html=True)
    with c3:
        derecha()


def titulos_tabla(derecha: str):
    c1, _, c3 = st.columns([10, 1, 10])
    c1.markdown("<div class='col-titulo'>📋 Novedades PCZ</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='col-titulo'>📘 {derecha}</div>", unsafe_allow_html=True)


# ----------------------------------------------------------- barra superior
p = a.progreso(trabajo, len(pcz))
nav = st.columns([1, 4, 1], vertical_alignment="center")
nav[0].button("⬅️ Anterior", on_click=mover, args=(dia_idx - 1,), disabled=dia_idx == 0, use_container_width=True)
with nav[1]:
    st.markdown(
        f"<div style='text-align:center'><b>Día {dia_idx + 1} de {n_dias}</b> &nbsp;·&nbsp; Novedades: ✅ "
        f"{p['asociadas']} asociadas &nbsp;·&nbsp; 🗑️ {p['descartadas']} descartadas</div>", unsafe_allow_html=True)
    st.progress((p["total"] - p["pendientes"]) / p["total"] if p["total"] else 1.0)
if dia_idx < n_dias - 1:
    nav[2].button("➡️ Siguiente", on_click=mover, args=(dia_idx + 1,), use_container_width=True)
else:
    nav[2].button("📥 Exportar", type="primary", on_click=ir_a_paso, args=(PASOS[2],), use_container_width=True)

# ------------------------------------------------------------------ el día
with st.container(border=True):
    h1, h2 = st.columns([4, 1], vertical_alignment="center")
    h1.subheader(f"Día {a.formatear_fecha(dia)}" if dia else "Novedades con fecha no reconocida", anchor=False)
    h1.caption(f"{len(novedades_dia)} novedad(es) de PCZ")
    h2.markdown(f"<div style='text-align:right'>{f'⏳ {len(pend_dia)} pendiente(s)' if pend_dia else '✅ Día completo'}"
                "</div>", unsafe_allow_html=True)
    en_paso_1 = b["etapa"] == "pcz"
    st.markdown(
        "<div class='pasos'>"
        + ("<b>① Elegí las novedades de PCZ</b>" if en_paso_1 else "<span class='off'>① Elegí las novedades de PCZ</span>")
        + " &nbsp;›&nbsp; "
        + ("<b>② Elegí los avisos del LG</b>" if not en_paso_1 else "<span class='off'>② Elegí los avisos del LG</span>")
        + "</div>", unsafe_allow_html=True)
    if dia is None:
        st.warning("Estas novedades tienen una fecha que no se pudo interpretar: no se proponen avisos por fecha, "
                   "usá el buscador para buscar en todo el LG.")

    if en_paso_1:
        # ------------------------------------- Paso 1: elegir novedades de PCZ
        st.caption("Tocá una o varias novedades pendientes y después «Elegir avisos del LG», o «Descartar» si no "
                   "tienen nada en el LG. Lo ya resuelto queda en gris.")
        titulos_tabla("Avisos del Libro de Guardia")
        hechas = set()
        for k in novedades_dia:
            if k in hechas:
                continue
            if k in asociacion_de:  # asociación (puede tener varias novedades del día)
                i = asociacion_de[k]
                g = trabajo["asociaciones"][i]
                propias = [x for x in g["novedades"] if x in novedades_dia]
                hechas.update(propias)

                def izq(propias=propias):
                    for x in propias:
                        con_botonera(x, lambda x=x: st.markdown(html_pcz(x, hecha=True), unsafe_allow_html=True),
                                     tacho=False)

                def der(g=g, i=i):
                    st.markdown("".join(html_aviso(c, True, g["novedades"]) for c in g["avisos"]
                                        if c in aviso_por_clave.index), unsafe_allow_html=True)
                    st.button("🗑️ Quitar asociación", key=f"{P}quitar_{ver}_{i}", on_click=quitar, args=(i,))

                fila_tabla(izq, der)
            elif k in trabajo["descartadas"]:
                def izq(k=k):
                    con_botonera(k, lambda: st.markdown(html_pcz(k, hecha=True), unsafe_allow_html=True), tacho=False)

                def der(k=k):
                    st.markdown(html_vacia("🗑️ descartada (sin aviso en el LG)", hecha=True), unsafe_allow_html=True)
                    st.button("↩️ Recuperar", key=f"{P}recuperar_{ver}_{k}", on_click=recuperar, args=(k,))

                fila_tabla(izq, der, flecha=False)
            else:
                orden = pend_dia.index(k) + 1

                def tarjeta(k=k, orden=orden):
                    with st.container(border=True, key=f"tarjeta_p_{ver}_{k}_{color_de(k)}"):
                        clave = f"{P}nov_{ver}_{k}"
                        st.checkbox(f"\\[{orden}\\] {titulo_novedad(k)}", value=k in b["novedades"], key=clave,
                                    on_change=tildar, args=("novedades", k, clave))
                        st.markdown(a.resaltar(pcz.loc[k, "descripcion"] or "(sin descripción)", set()),
                                    unsafe_allow_html=True)

                def izq(k=k, tarjeta=tarjeta):
                    con_botonera(k, tarjeta)

                def der():
                    st.markdown(html_vacia("pendiente"), unsafe_allow_html=True)

                fila_tabla(izq, der, flecha=False)

    else:
        # ------------------------------------- Paso 2: elegir avisos del LG
        st.caption("Tildá abajo uno o varios avisos del LG: van apareciendo a la derecha. Después tocá «Asociar».")
        titulos_tabla("Avisos elegidos")

        def izq_nueva():
            for k in list(b["novedades"]):
                con_botonera(k, lambda k=k: st.markdown(html_pcz(k), unsafe_allow_html=True))

        def der_nueva():
            if b["avisos"]:
                st.markdown("".join(html_aviso(c, novedades_propias=b["novedades"]) for c in b["avisos"]
                                    if c in aviso_por_clave.index), unsafe_allow_html=True)
            else:
                st.markdown(html_vacia("todavía ninguno ↓ tildalos en la lista de abajo"), unsafe_allow_html=True)

        fila_tabla(izq_nueva, der_nueva)

# ---------------------------------------------------------- avisos del LG
if b["etapa"] == "lg":
    nov = a.novedad_combinada(pcz, b["novedades"])
    st.subheader("Avisos del LG " + (f"del {a.formatear_fecha(dia)}" if dia else ""), anchor=False)
    f1, f2 = st.columns([3, 2], vertical_alignment="bottom")
    busqueda = f1.text_input("🔎 Buscar en los avisos", key=f"{P}buscar_{dia_idx}",
                             placeholder="Ej.: Boulogne 14  (filtra por texto)", label_visibility="collapsed")
    vecinos = f2.toggle("Ver también día anterior / siguiente", key=P + "vecinos",
                        help="Para eventos que cruzan la medianoche. Se muestran marcados como OTRO DÍA.")

    if dia is None:
        # Sin fecha en PCZ: se busca en todo el LG, solo si el usuario escribe algo
        cands = a.todos_los_avisos(nov, avisos_lg[avisos_lg["fecha"].notna()])
    else:
        cands = a.candidatos(nov, avisos_lg, vecinos)
    cant_dia = int((~cands["otro_dia"]).sum())
    cands = a.buscar(cands, busqueda)
    sin_fecha = a.buscar(a.avisos_sin_fecha(nov, avisos_lg), busqueda)

    if dia is not None:
        st.caption(f"{cant_dia} aviso(s) ese día"
                   + (f" · {len(cands)} coinciden con la búsqueda" if busqueda else "")
                   + " · ordenados por parecido con las novedades elegidas (en amarillo, lo que coincide)",
                   help="Puntaje: número compartido 3 (1 si es de una cifra) · palabra compartida 1 · "
                        "hora cercana hasta 3.")

    # Se dibujan de a tandas (los de mayor puntaje primero): dibujar cientos de tarjetas en
    # cada clic hace lenta la pantalla. El buscador sigue buscando entre todos.
    POR_TANDA = 15
    clave_limite = f"{P}limite_{dia_idx}"
    limite = ss.get(clave_limite, POR_TANDA)

    def ampliar(cantidad: int):
        ss[clave_limite] = cantidad

    def mostrar(c: pd.DataFrame, inicio: int, etiqueta: str | None, seccion: str) -> int:
        """Dibuja las tarjetas de `c` (hasta el límite, más las ya tildadas). Devuelve cuántas dibujó."""
        visibles = c.head(limite)
        tildadas = c[c["clave"].isin(b["avisos"]) & ~c.index.isin(visibles.index)]
        visibles = pd.concat([visibles, tildadas])
        for k, (_, cand) in enumerate(visibles.iterrows(), start=inicio):
            clave_aviso = cand["clave"]
            otras = [pcz.loc[x, "id"] for x in asociados_a.get(clave_aviso, []) if x not in b["novedades"]]
            with st.container(border=True, key=f"tarjeta_l_{ver}_{clave_aviso.replace(':', '_')}"):
                c1, c2 = st.columns([1, 5])
                clave = f"{P}av_{ver}_{clave_aviso}"
                c1.checkbox(f"\\[{k}\\] LG fila {cand['fila_lg'] + 1}", value=clave_aviso in b["avisos"], key=clave,
                            on_change=tildar, args=("avisos", clave_aviso, clave))
                hora_cand = a.formatear_hora(cand["hora"])
                c1.caption(f"Puntaje **{cand['puntaje']}**" + (f" · 🕒 {hora_cand}" if hora_cand else ""))
                marcas = []
                if etiqueta:
                    marcas.append(f"<span style='background:#E8B400;color:#1C1A19;padding:1px 6px;border-radius:4px;"
                                  f"font-weight:600'>{etiqueta} · {a.formatear_fecha(cand['fecha'])}</span>")
                if otras:
                    marcas.append(f"<span style='background:#4A4543;color:#fff;padding:1px 6px;border-radius:4px'>"
                                  f"🔗 ya asociado a N° {', '.join(otras)}</span>")
                c2.markdown(
                    (" ".join(marcas) + "<br>" if marcas else "")
                    + a.resaltar(cand["texto"], cand["comunes"], cand["hora_suma"])
                    + f"<br><span style='opacity:0.6;font-size:0.85rem'>{cand['detalle']}</span>",
                    unsafe_allow_html=True,
                )
        if len(c) > len(visibles):
            resto = len(c) - len(visibles)
            st.caption(f"Se muestran {len(visibles)} de {len(c)}. Quedan {resto} con menor puntaje.")
            k1, k2, _ = st.columns([1, 1, 3])
            k1.button(f"⬇️ Mostrar {min(POR_TANDA, resto)} más", key=f"{P}mas_{seccion}_{ver}",
                      on_click=ampliar, args=(limite + POR_TANDA,), use_container_width=True)
            k2.button(f"Mostrar todos ({len(c)})", key=f"{P}todas_{seccion}_{ver}",
                      on_click=ampliar, args=(len(c),), use_container_width=True)
        return len(visibles)

    mismo = cands[~cands["otro_dia"]]
    otro = cands[cands["otro_dia"]]
    if dia is None:
        if not busqueda:
            st.info("Escribí en el buscador para buscar entre todos los avisos del LG.")
            dibujadas = 0
        else:
            dibujadas = mostrar(cands, 1, "SIN FECHA EN PCZ", "todas")
    else:
        if mismo.empty:
            st.info("No hay avisos del LG " + ("que coincidan con la búsqueda " if busqueda else "")
                    + f"con fecha {a.formatear_fecha(dia)}. Si no tienen evento en el LG, tocá «Descartar».")
        dibujadas = mostrar(mismo, 1, None, "mismo")
        if vecinos:
            st.markdown("##### 🌙 OTRO DÍA (día anterior / siguiente)")
            if otro.empty:
                st.caption("No hay avisos del día anterior ni del siguiente.")
            dibujadas += mostrar(otro, dibujadas + 1, "OTRO DÍA", "otro")
    if len(sin_fecha):
        with st.expander(f"Avisos del LG sin fecha reconocible ({len(sin_fecha)})"):
            mostrar(sin_fecha, dibujadas + 1, "SIN FECHA", "sin_fecha")

# ------------------------------------------------- botones de acción
# Van al final de la página y quedan pegados abajo de la pantalla mientras se hace scroll
# (position: sticky), así siempre están a mano.
with st.container(key="barra_acciones"):
    if b["etapa"] == "pcz":
        bc = st.columns([1.4, 1.2, 1, 1.4])
        bc[0].button("➡️ Elegir avisos del LG", type="primary", on_click=ir_a_avisos, disabled=not b["novedades"],
                     use_container_width=True)
        bc[1].button("🗑️ Descartar", on_click=descartar, disabled=not b["novedades"], use_container_width=True,
                     help="Las novedades tildadas no tienen aviso en el LG: salen en el Excel solo con su texto de PCZ.")
        if len(pend_dia) > 1:
            bc[2].button("☑ Todas", on_click=todas_las_pendientes, use_container_width=True,
                         help="Tilda todas las novedades pendientes del día.")
    else:
        bc = st.columns([1.3, 1.3, 1.3, 1.7])
        bc[0].button("✅ Asociar", type="primary", on_click=asociar, disabled=not b["avisos"],
                     use_container_width=True)
        bc[1].button("🗑️ Descartar", on_click=descartar, use_container_width=True,
                     help="Estas novedades no tienen aviso en el LG: salen en el Excel solo con su texto de PCZ.")
        bc[2].button("⬅️ Volver a las novedades", on_click=volver_a_novedades, use_container_width=True)

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
    b = boton('Asociar') || boton('Elegir avisos del LG');
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
