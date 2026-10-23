"""Módulo: Informes PowerPoint (etapa 1: plantillas; etapa 2: configuraciones de informe)."""
import copy
import hashlib
import json
from html import escape

import pandas as pd
import streamlit as st

from src.informes_pptx import configuraciones as cf
from src.informes_pptx import esquema, excel, office
from src.informes_pptx import excel_zip as ez
from src.informes_pptx import plantillas as pl

st.title("Informes PowerPoint")
st.caption("Arma el informe mensual en PowerPoint a partir del Excel. Se trabaja en tres niveles: "
           "la **plantilla** (sale de un PowerPoint de ejemplo), la **configuración** (de dónde sale "
           "cada imagen y cada texto) y la **generación** del informe.")

ss = st.session_state
P = "inf_"  # prefijo de las claves de este módulo en session_state
SECCIONES = ["Plantillas", "Configuraciones de informe", "Generar informe"]


@st.cache_resource
def obtener_office():
    return office.obtener()


@st.cache_resource
def obtener_motor():
    return excel.obtener()


OF = obtener_office()
MOTOR = obtener_motor()

st.html("""<style>
mark { background: #FFE27A; color: inherit; padding: 0 .1em; border-radius: 2px; }
.inf-contenido { border-left: 4px solid #8C8682; background: rgba(140,134,130,.08); border-radius: .3rem;
                 padding: .45rem .7rem; white-space: pre-wrap; line-height: 1.4; font-size: .95rem; }
.inf-contenido.variable { border-left-color: #C98A00; background: rgba(255,226,122,.25); }
.inf-vacio { opacity: .55; font-style: italic; }
.inf-etiqueta { display: inline-block; min-width: 2.2rem; text-align: center; color: #FFFFFF; font-weight: 700;
                font-size: .8rem; border-radius: .25rem; padding: .05rem .35rem; margin-right: .4rem; }
.inf-leyenda { font-size: .85rem; opacity: .85; margin-top: .3rem; }
.inf-valor { border-left: 4px solid #2F7D4A; background: rgba(47,125,74,.08); border-radius: .3rem;
             padding: .35rem .7rem; font-size: .92rem; }
.inf-leyenda span { display: inline-block; width: .8rem; height: .8rem; border-radius: 2px;
                    vertical-align: -1px; margin: 0 .25rem 0 .7rem; }
</style>""")

seccion = st.radio("Sección", SECCIONES, horizontal=True, key=P + "seccion", label_visibility="collapsed")
if seccion == SECCIONES[2]:
    st.info("Esta sección llega en la etapa 3. Por ahora se pueden armar las plantillas y las configuraciones.")
    st.stop()

if msg := ss.pop(P + "msg", None):
    getattr(st, msg[0])(msg[1])


def miniaturas(pid: str) -> str | None:
    """Genera las miniaturas con PowerPoint. Devuelve el error (o None). Nunca frena nada."""
    if not OF.hace_miniaturas:
        return None
    try:
        with st.spinner("Generando miniaturas con PowerPoint..."):
            OF.miniaturas(pl.carpeta(pid) / "base.pptx", pl.carpeta_miniaturas(pid))
    except Exception as e:  # PowerPoint cerrado, ocupado, sin permisos...: se sigue sin miniaturas
        return f"No se pudieron generar las miniaturas ({e}). Se muestra el esquema con los recuadros."
    return None


def abrir(pid: str):
    ss[P + "edit"] = pl.cargar(pid)
    ss[P + "original"] = copy.deepcopy(ss[P + "edit"])
    ss[P + "ver"] = ss.get(P + "ver", 0) + 1  # claves nuevas para los campos del editor
    ss[P + "diap"] = 1
    ss.pop(P + "prueba", None)


def cerrar():
    ss.pop(P + "edit", None)


def ligar(obj: dict, campo: str, key: str, despues=None):
    """El valor del widget `key` queda guardado en obj[campo] (aunque se cambie de diapositiva o de
    pestaña y el widget deje de mostrarse). `despues(valor_viejo)` corre después de copiarlo."""
    if key not in ss:
        ss[key] = obj[campo]

    def copiar():
        viejo = obj[campo]
        obj[campo] = ss[key]
        if despues:
            despues(viejo)
    return copiar


# ====================================================================== lista
def pantalla_lista():
    plantillas, rotas = pl.listar()
    st.header("Plantillas")
    if OF.hace_miniaturas:
        st.caption("Las miniaturas de las diapositivas se generan con PowerPoint.")
    else:
        st.caption(f"Sin miniaturas de las diapositivas ({OF.motivo}): se muestra un esquema con los "
                   "recuadros a escala.")

    with st.expander("➕ Nueva plantilla a partir de un PowerPoint", expanded=not plantillas):
        st.caption("Subí un informe ya armado. La app detecta los textos y los lugares de imagen de cada "
                   "diapositiva; después marcás qué textos cambian cada mes y le ponés nombre a cada imagen.")
        archivo = st.file_uploader("PowerPoint de ejemplo (.pptx)", type=["pptx"], key=P + "subida")
        nombre = st.text_input("Nombre de la plantilla", key=P + "nombre_nueva",
                               placeholder=archivo.name.removesuffix(".pptx") if archivo else "Ej.: Informe mensual RAMS")
        if st.button("Crear plantilla", type="primary", disabled=archivo is None):
            try:
                nueva = pl.crear(nombre or archivo.name.removesuffix(".pptx"), archivo.name, archivo.getvalue())
            except pl.ErrorPlantilla as e:
                st.error(str(e))
            else:
                error = miniaturas(nueva["id"])
                abrir(nueva["id"])
                ss[P + "msg"] = ("warning", error) if error else (
                    "success", "Plantilla creada. Todos los textos arrancan como **fijos**: marcá los que "
                               "cambian cada mes y guardá.")
                st.rerun()

    if rotas:
        st.warning(f"No se pudieron leer estas carpetas de plantillas: {', '.join(rotas)}.")
    if not plantillas:
        st.info("Todavía no hay plantillas guardadas.")
        return
    for p in plantillas:
        n_var = len(pl.variables(p))
        n_img = sum(len(d["imagenes"]) for d in p["diapositivas"])
        with st.container(border=True):
            c = st.columns([6, 1.2, 1.2, 1.2], vertical_alignment="center")
            c[0].markdown(f"**{escape(p['nombre'])}**")
            c[0].caption(f"{len(p['diapositivas'])} diapositivas – {n_var} variables de texto – {n_img} lugares "
                         f"de imagen – creada desde «{escape(p['archivo_original'])}» – última modificación "
                         f"{p['modificada'].replace('T', ' ')[:16]}")
            c[1].button("✏️ Editar", key=P + "editar_" + p["id"], on_click=abrir, args=(p["id"],),
                        use_container_width=True)
            if c[2].button("📄 Duplicar", key=P + "dup_" + p["id"], use_container_width=True):
                copia = pl.duplicar(p["id"])
                ss[P + "msg"] = ("success", f"Se creó «{copia['nombre']}».")
                st.rerun()
            with c[3].popover("🗑️ Eliminar", use_container_width=True):
                usan = cf.de_plantilla(p["id"])
                if usan:
                    cuantas = "una configuración" if len(usan) == 1 else f"{len(usan)} configuraciones"
                    st.markdown(f"No se puede eliminar: la usa {cuantas} "
                                f"({', '.join('«' + escape(x['nombre']) + '»' for x in usan)}). "
                                "Eliminalas primero en **Configuraciones de informe**.")
                    continue
                st.markdown(f"¿Eliminar **{escape(p['nombre'])}**? No se puede deshacer.")
                if st.button("Sí, eliminar", key=P + "borrar_" + p["id"], type="primary"):
                    pl.eliminar(p["id"])
                    ss[P + "msg"] = ("success", f"Se eliminó «{p['nombre']}».")
                    st.rerun()


# ===================================================================== editor
def pantalla_editor():
    plant = ss[P + "edit"]
    pid, ver = plant["id"], ss[P + "ver"]
    diaps = plant["diapositivas"]
    tam = plant["tamano_diapositiva"]

    def clave(*partes) -> str:
        return f"{P}{ver}_" + "_".join(str(x) for x in partes)

    cambios = plant != ss[P + "original"]
    st.header(f"Plantilla: {plant['nombre']}")
    barra = st.columns([3, 1.3, 1.3, 1.3], vertical_alignment="bottom")
    barra[0].text_input("Nombre de la plantilla", key=clave("nombre"),
                        on_change=ligar(plant, "nombre", clave("nombre")))
    if barra[1].button("💾 Guardar", type="primary", use_container_width=True):
        try:
            ss[P + "edit"] = pl.guardar(plant)
        except pl.ErrorPlantilla as e:
            st.error("No se guardó. Hay que corregir esto:\n\n" + "\n".join(f"- {x}" for x in str(e).split("\n")))
        else:
            ss[P + "original"] = copy.deepcopy(ss[P + "edit"])
            ss[P + "msg"] = ("success", "Plantilla guardada.")
            st.rerun()
    if cambios:
        with barra[2].popover("↩️ Volver a la lista", use_container_width=True):
            st.markdown("Hay cambios sin guardar.")
            st.button("Salir sin guardar", on_click=cerrar, key=clave("salir"))
    else:
        barra[2].button("↩️ Volver a la lista", on_click=cerrar, use_container_width=True)
    if OF.hace_miniaturas and barra[3].button("🖼️ Actualizar miniaturas", use_container_width=True):
        if error := miniaturas(pid):
            st.warning(error)
    st.caption(("🟡 Hay cambios sin guardar – " if cambios else "") +
               f"{len(diaps)} diapositivas de {tam['ancho_cm']} × {tam['alto_cm']} cm – "
               f"creada desde «{plant['archivo_original']}»")

    # --------------------------------------------------- elegir diapositiva
    def titulo(d: dict) -> str:
        primero = next((t["contenido"] for t in d["textos"] if t["contenido"].strip()), "")
        return f"Diapositiva {d['numero']}" + (f" – {pl.corto(primero, 50)}" if primero else "") + \
            (" (oculta)" if d["oculta"] else "")

    def mover(paso: int):
        ss[P + "diap"] = min(max(ss[P + "diap"] + paso, 1), len(diaps))

    nav = st.columns([1, 6, 1], vertical_alignment="bottom")
    nav[0].button("⬅️ Anterior", on_click=mover, args=(-1,), disabled=ss[P + "diap"] == 1, use_container_width=True)
    nav[1].selectbox("Diapositiva", range(1, len(diaps) + 1), format_func=lambda n: titulo(diaps[n - 1]),
                     key=P + "diap", label_visibility="collapsed")
    nav[2].button("Siguiente ➡️", on_click=mover, args=(1,), disabled=ss[P + "diap"] == len(diaps),
                  use_container_width=True)
    d = diaps[ss[P + "diap"] - 1]

    izq, der = st.columns([11, 9], gap="large")
    with izq:
        mini = pl.miniatura(pid, d["numero"])
        st.image(esquema.svg(d, tam, mini.read_bytes() if mini else None), width="stretch")
        st.html("<div class='inf-leyenda'>Recuadros:<span style='background:#8C8682'></span>texto fijo"
                "<span style='background:#C98A00'></span>texto variable"
                "<span style='background:#D41920'></span>lugar de imagen</div>")
        if not mini:
            st.caption("Esquema con los recuadros a escala (sin miniatura de la diapositiva).")
        for aviso in d["avisos"]:
            st.warning(aviso)

    usos = pl.variables(plant)
    with der:
        tab_t, tab_i = st.tabs([f"Textos ({len(d['textos'])})", f"Lugares de imagen ({len(d['imagenes'])})"])
        with tab_t:
            if not d["textos"]:
                st.caption("Esta diapositiva no tiene textos.")
            st.caption("Marcá como **variable** lo que cambia en cada informe. Las celdas vacías de las tablas "
                       "no se listan.")
            for i, t in enumerate(d["textos"], 1):
                editor_texto(i, t, d["numero"], usos, clave)
        with tab_i:
            if not d["imagenes"]:
                st.caption("Esta diapositiva no tiene lugares de imagen.")
            st.caption("Cada lugar de imagen se va a llenar con una captura o un gráfico del Excel. Ponele un "
                       "nombre que lo identifique.")
            for i, img in enumerate(d["imagenes"], 1):
                with st.container(border=True):
                    c = img["caja"]
                    st.html(f"<span class='inf-etiqueta' style='background:#D41920'>I{i}</span>"
                            f"<b>{escape(img['clase'])}</b>")
                    st.text_input("Nombre", key=clave("img", img["id"]),
                                  on_change=ligar(img, "nombre", clave("img", img["id"])),
                                  placeholder="Ej.: Confiabilidad – tabla de eventos")
                    st.caption(f"Identificador: `{img['id']}` – posición {pl.cm(c['x'])} × {pl.cm(c['y'])} cm – "
                               f"tamaño {pl.cm(c['ancho'])} × {pl.cm(c['alto'])} cm")

    # ------------------------------------------------------- resumen general
    with st.expander("📋 Resumen de toda la plantilla"):
        filas_v = [{"Identificador": vid, "Nombre": v["nombre"],
                    "Dónde": ", ".join(f"diap. {n}" for n, _ in v["usos"])} for vid, v in usos.items()]
        st.markdown("**Variables de texto**")
        if filas_v:
            st.dataframe(pd.DataFrame(filas_v), hide_index=True, use_container_width=True)
        else:
            st.caption("Todavía no hay textos variables.")
        st.markdown("**Lugares de imagen**")
        filas_i = [{"Diap.": dd["numero"], "Identificador": img["id"], "Nombre": img["nombre"],
                    "Tipo": img["clase"], "Tamaño (cm)": f"{pl.cm(img['caja']['ancho'])} × {pl.cm(img['caja']['alto'])}"}
                   for dd in diaps for img in dd["imagenes"]]
        if filas_i:
            st.dataframe(pd.DataFrame(filas_i), hide_index=True, use_container_width=True)
        else:
            st.caption("El PowerPoint no tiene imágenes ni gráficos.")

    # ------------------------------------------------- prueba de reemplazo
    with st.expander("🧪 Probar los textos variables"):
        st.caption("Arma una copia del PowerPoint con cada variable reemplazada por «su nombre», para revisar "
                   "que el reemplazo conserve la fuente, el tamaño, el color y la negrita. Usa lo que tenés "
                   "en pantalla, aunque no esté guardado.")
        if st.button("Armar PowerPoint de prueba", disabled=not usos):
            ss[P + "prueba"] = pl.prueba_textos(plant)
        if ss.get(P + "prueba"):
            st.download_button("Descargar prueba.pptx", ss[P + "prueba"], f"{plant['nombre']} - prueba.pptx",
                               type="primary")


def editor_texto(i: int, t: dict, numero: int, usos: dict, clave):
    with st.container(border=True):
        variable = t["tipo"] == pl.VARIABLE
        color = "#C98A00" if variable else "#8C8682"
        st.html(f"<span class='inf-etiqueta' style='background:{color}'>T{i}</span>"
                f"<b>{escape(t['origen'])}</b>")
        contenido = escape(t["contenido"])
        if variable and t["reemplazo"] == pl.FRAGMENTO and t["fragmento"] and t["fragmento"] in t["contenido"]:
            contenido = contenido.replace(escape(t["fragmento"]), f"<mark>{escape(t['fragmento'])}</mark>")
        elif variable and t["reemplazo"] == pl.TODO and contenido:
            contenido = f"<mark>{contenido}</mark>"
        st.html(f"<div class='inf-contenido{' variable' if variable else ''}'>"
                f"{contenido or '<span class=inf-vacio>(vacío)</span>'}</div>")

        k_tipo = clave("tipo", t["id"])
        st.radio("Tipo", [pl.FIJO, pl.VARIABLE], key=k_tipo, horizontal=True, label_visibility="collapsed",
                 format_func=lambda x: "Fijo (no cambia)" if x == pl.FIJO else "Variable (cambia en cada informe)",
                 on_change=ligar(t, "tipo", k_tipo))
        if t["tipo"] != pl.VARIABLE:
            return

        k_rem = clave("rem", t["id"])
        st.radio("Qué se reemplaza", [pl.TODO, pl.FRAGMENTO], key=k_rem, horizontal=True,
                 format_func=lambda x: "Todo el cuadro" if x == pl.TODO else "Solo una parte",
                 on_change=ligar(t, "reemplazo", k_rem))
        if t["reemplazo"] == pl.FRAGMENTO:
            k_frag = clave("frag", t["id"])
            st.text_input("Parte a reemplazar (copiala tal cual aparece arriba)", key=k_frag,
                          on_change=ligar(t, "fragmento", k_frag), placeholder="Ej.: Septiembre 2026")
            if t["fragmento"]:
                veces = t["contenido"].count(t["fragmento"])
                if veces == 0:
                    st.warning("Esa parte no aparece en el texto. Tiene que estar escrita igual, con mayúsculas "
                               "y espacios.")
                elif veces > 1:
                    st.info(f"Aparece {veces} veces en este cuadro: se reemplazan todas.")

        k_id = clave("vid", t["id"])

        def nombre_cambiado(viejo: str):
            # El identificador sigue al nombre mientras no se lo haya cambiado a mano
            if not t["variable_id"] or t["variable_id"] == pl.slug(viejo):
                t["variable_id"] = ss[k_id] = pl.slug(t["variable_nombre"])

        c1, c2 = st.columns(2)
        k_nom = clave("vnom", t["id"])
        c1.text_input("Nombre de la variable", key=k_nom, placeholder="Ej.: Mes del título",
                      on_change=ligar(t, "variable_nombre", k_nom, nombre_cambiado))
        c2.text_input("Identificador", key=k_id, on_change=ligar(t, "variable_id", k_id),
                      help="Se arma solo a partir del nombre. Si dos textos tienen el mismo identificador, "
                           "se completan con el mismo valor (por ejemplo, el mes en la portada y en el pie).")
        otros = [n for n, tid in usos.get(t["variable_id"], {}).get("usos", []) if tid != t["id"]]
        if otros:
            st.caption(f"🔗 Se completa con el mismo valor que en: {', '.join(f'diap. {n}' for n in otros)}.")


# ============================================================ configuraciones
SIN_HOJA = ""
TOMAS = {cf.RANGO: "Un rango de celdas", cf.GRAFICO: "Un gráfico"}
MODOS = {cf.CAPTURA: "Captura (imagen)", cf.GRAFICO: "Gráfico pegado (editable en PowerPoint)"}
FUENTES = {cf.LIBRE: "Texto libre", cf.CELDA: "Celda del Excel"}


@st.cache_data(show_spinner="Leyendo el Excel...", max_entries=3)
def leer_excel(contenido: bytes) -> ez.InfoExcel:
    return ez.leer(contenido)


@st.cache_data(show_spinner=False, max_entries=20)
def valores_guardados(contenido: bytes, refs: tuple) -> dict:
    return ez.leer_celdas(contenido, list(refs))


def caption_motor():
    if MOTOR.real:
        st.caption("Las vistas previas se hacen con el **Excel de Windows** (abre una copia del archivo, "
                   "invisible, sin tocar tus Excel abiertos).")
    else:
        st.caption(f"Motor simulado ({MOTOR.motivo}): las vistas previas son imágenes de relleno con el nombre "
                   "de lo elegido. Las capturas reales se hacen en la compu del trabajo.")


def abrir_config(cid: str):
    config = cf.cargar(cid)
    plant = pl.cargar(config["plantilla"])
    config, avisos = cf.completar(config, plant)
    ss[P + "cfg"], ss[P + "cfg_plant"] = config, plant
    ss[P + "cfg_original"] = copy.deepcopy(config)
    ss[P + "cver"] = ss.get(P + "cver", 0) + 1
    ss[P + "vistas"], ss[P + "textos_excel"] = {}, {}
    if avisos:
        ss[P + "msg"] = ("warning", "La plantilla cambió desde la última vez:\n\n" + "\n".join(f"- {a}" for a in avisos))


def cerrar_config():
    ss.pop(P + "cfg", None)


def pantalla_lista_configs():
    st.header("Configuraciones de informe")
    st.caption("Una configuración dice, para una plantilla, de qué hoja y rango (o gráfico) del Excel sale cada "
               "imagen y de dónde sale cada texto variable. Una plantilla puede tener varias.")
    caption_motor()
    plantillas, _ = pl.listar()
    configs, rotas = cf.listar()
    nombres = {p["id"]: p["nombre"] for p in plantillas}

    with st.expander("➕ Nueva configuración", expanded=not configs):
        if not plantillas:
            st.info("Primero armá una plantilla en la sección **Plantillas**.")
        else:
            pid = st.selectbox("Plantilla", list(nombres), format_func=nombres.get, key=P + "cfg_plantilla")
            nombre = st.text_input("Nombre de la configuración", key=P + "cfg_nombre_nueva",
                                   placeholder="Ej.: Informe mensual Señalamiento")
            if st.button("Crear configuración", type="primary", disabled=not nombre.strip()):
                nueva = cf.crear(nombre, next(p for p in plantillas if p["id"] == pid))
                abrir_config(nueva["id"])
                ss[P + "msg"] = ("success", "Configuración creada. Subí el Excel de referencia para elegir de dónde "
                                            "sale cada imagen y cada texto.")
                st.rerun()

    if rotas:
        st.warning(f"No se pudieron leer estos archivos de configuraciones: {', '.join(rotas)}.")
    if not configs:
        st.info("Todavía no hay configuraciones guardadas.")
        return
    for c in configs:
        n_img = sum(cf.esta_completa_imagen(i) for i in c["imagenes"].values())
        n_txt = sum(cf.esta_completo_texto(t) for t in c["textos"].values())
        plantilla = nombres.get(c["plantilla"])
        with st.container(border=True):
            col = st.columns([6, 1.2, 1.2, 1.2], vertical_alignment="center")
            col[0].markdown(f"**{escape(c['nombre'])}**")
            col[0].caption(
                (f"Plantilla «{escape(plantilla)}»" if plantilla else "⚠️ Su plantilla ya no existe") +
                f" – imágenes {n_img}/{len(c['imagenes'])} – textos {n_txt}/{len(c['textos'])}" +
                (f" – Excel de referencia «{escape(c['excel_referencia'])}»" if c.get("excel_referencia") else "") +
                f" – última modificación {c['modificada'].replace('T', ' ')[:16]}")
            col[1].button("✏️ Editar", key=P + "cfg_editar_" + c["id"], on_click=abrir_config, args=(c["id"],),
                          use_container_width=True, disabled=plantilla is None)
            if col[2].button("📄 Duplicar", key=P + "cfg_dup_" + c["id"], use_container_width=True):
                copia = cf.duplicar(c["id"])
                ss[P + "msg"] = ("success", f"Se creó «{copia['nombre']}».")
                st.rerun()
            with col[3].popover("🗑️ Eliminar", use_container_width=True):
                st.markdown(f"¿Eliminar **{escape(c['nombre'])}**? No se puede deshacer.")
                if st.button("Sí, eliminar", key=P + "cfg_borrar_" + c["id"], type="primary"):
                    cf.eliminar(c["id"])
                    ss[P + "msg"] = ("success", f"Se eliminó «{c['nombre']}».")
                    st.rerun()


def pedido(iid: str, img: dict) -> dict:
    p = {"id": iid, "hoja": img["hoja"]}
    if img["toma"] == cf.GRAFICO:
        p["grafico"] = img["grafico"]
    else:
        p["rango"] = ez.armar_rango(img["desde"], img["hasta"])
    return p


def firma(huella: str, img: dict) -> str:
    """Identifica una vista previa: si cambia el Excel o lo elegido, la vista vieja ya no vale."""
    return huella + json.dumps(cf.imagen_a_json(img), sort_keys=True, ensure_ascii=False)


def hacer_vistas(contenido: bytes, nombre: str, huella: str, elegidos: dict, refs: list, actualizar: bool):
    """Captura las imágenes elegidas ({id: imagen}) y lee las celdas, con una sola apertura de Excel."""
    pedidos = [pedido(iid, img) for iid, img in elegidos.items()]
    texto = "Abriendo Excel, actualizando los datos y capturando..." if MOTOR.real else "Armando vistas previas..."
    try:
        with st.spinner(texto):
            capturas, textos, avisos = excel.exportar(MOTOR, contenido, nombre, pedidos, refs, actualizar)
    except Exception as e:  # noqa: BLE001 - Excel no abrió: se avisa y la pantalla sigue
        ss[P + "msg"] = ("error", f"No se pudo hacer la vista previa: {excel._mensaje(e)}")
        return
    for iid, img in elegidos.items():
        ss[P + "vistas"][iid] = {"firma": firma(huella, img), "captura": capturas[iid]}
    if textos:
        ss[P + "textos_excel"] = {"huella": huella, "valores": textos}
    if avisos:
        ss[P + "msg"] = ("info", "\n\n".join(avisos))


def pantalla_editor_config():
    config, plant = ss[P + "cfg"], ss[P + "cfg_plant"]
    ver = ss[P + "cver"]

    def clave(*partes) -> str:
        return f"{P}c{ver}_" + "_".join(str(x) for x in partes)

    cambios = config != ss[P + "cfg_original"]
    st.header(f"Configuración: {config['nombre']}")
    barra = st.columns([3, 1.3, 1.3], vertical_alignment="bottom")
    barra[0].text_input("Nombre de la configuración", key=clave("nombre"),
                        on_change=ligar(config, "nombre", clave("nombre")))
    if barra[1].button("💾 Guardar", type="primary", use_container_width=True, key=clave("guardar")):
        try:
            ss[P + "cfg"] = cf.guardar(config, plant)
        except cf.ErrorConfiguracion as e:
            st.error("No se guardó. Hay que corregir esto:\n\n" + "\n".join(f"- {x}" for x in str(e).split("\n")))
        else:
            ss[P + "cfg_original"] = copy.deepcopy(ss[P + "cfg"])
            _, pendientes = cf.validar(config, plant)
            ss[P + "msg"] = ("success", "Configuración guardada." + (
                f" Falta completar: {', '.join(pendientes)}." if pendientes else ""))
            st.rerun()
    if cambios:
        with barra[2].popover("↩️ Volver a la lista", use_container_width=True):
            st.markdown("Hay cambios sin guardar.")
            st.button("Salir sin guardar", on_click=cerrar_config, key=clave("salir"))
    else:
        barra[2].button("↩️ Volver a la lista", on_click=cerrar_config, use_container_width=True, key=clave("volver"))
    st.caption(("🟡 Hay cambios sin guardar – " if cambios else "") + f"Sobre la plantilla «{plant['nombre']}»")

    # --------------------------------------------------------- Excel de referencia
    st.subheader("Excel de referencia")
    archivo = st.file_uploader("Subí el Excel con el que se arma el informe (.xlsx o .xlsm)", type=["xlsx", "xlsm"],
                               key=clave("excel"),
                               help="Se usa para elegir hojas, rangos y gráficos y para las vistas previas. "
                                    "No se guarda: en la configuración solo queda su nombre.")
    if archivo is None:
        if config.get("excel_referencia"):
            st.info(f"La última vez se usó «{config['excel_referencia']}». Subilo (o uno igual de otro mes) para "
                    "editar.")
        else:
            st.info("Subí el Excel para elegir de dónde sale cada imagen y cada texto.")
        resumen_config(config, plant)
        return
    contenido = archivo.getvalue()
    try:
        info = leer_excel(contenido)
    except ez.ErrorExcel as e:
        st.error(str(e))
        return
    config["excel_referencia"] = archivo.name
    huella = hashlib.md5(contenido).hexdigest()
    visibles = [h.nombre for h in info.visibles]
    ocultas = [h.nombre for h in info.hojas if not h.visible]
    st.caption(f"{len(visibles)} hojas visibles" + (f" – {len(ocultas)} ocultas (no se usan)" if ocultas else "") +
               f" – {sum(len(h.graficos) for h in info.visibles)} gráficos")

    errores, pendientes = cf.validar(config, plant)
    avisos = cf.avisos_excel(config, info)
    if avisos:
        st.warning("**Hay cosas de la configuración que no están en este Excel:**\n\n" + "\n".join(
            f"- {a}" for lista in avisos.values() for a in lista))

    actualizar = True
    c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
    if MOTOR.real:
        actualizar = c1.checkbox("Actualizar los datos antes de capturar (tablas dinámicas y Modelo de datos)",
                                 value=True, key=clave("actualizar"),
                                 help="Es lo que se hace al generar el informe. Destildalo para que las vistas "
                                      "previas salgan más rápido (usan los datos guardados en el archivo).")
    else:
        c1.caption("")
    variables = pl.variables(plant)
    refs = [ez.ref_celda(t["hoja"], ez.normalizar_celda(t["celda"])) for t in config["textos"].values()
            if t["fuente"] == cf.CELDA and t["hoja"] in visibles and ez.normalizar_celda(t["celda"])]
    completas = {iid: img for iid, img in config["imagenes"].items()
                 if cf.esta_completa_imagen(img) and not cf.errores_imagen(img) and iid not in avisos}
    if c2.button("👁️ Vista previa de todo", use_container_width=True, disabled=not (completas or refs),
                 key=clave("vista_todo"), help="Captura todas las imágenes completas y lee las celdas, abriendo el "
                                               "Excel una sola vez."):
        hacer_vistas(contenido, archivo.name, huella, completas, refs, actualizar)
        st.rerun()

    tab_i, tab_t = st.tabs([f"Imágenes ({len(config['imagenes'])})", f"Textos variables ({len(config['textos'])})"])
    with tab_i:
        if not config["imagenes"]:
            st.caption("La plantilla no tiene lugares de imagen.")
        diap_anterior = None
        for d, lugar in cf.lugares(plant):
            if d["numero"] != diap_anterior:
                st.markdown(f"#### Diapositiva {d['numero']}")
                diap_anterior = d["numero"]
            editor_imagen(lugar, d, plant, config["imagenes"][lugar["id"]], info, visibles, avisos.get(lugar["id"], []),
                          clave, contenido, archivo.name, huella, actualizar)
    with tab_t:
        if not config["textos"]:
            st.caption("La plantilla no tiene textos variables (se marcan en **Plantillas**).")
        guardados = valores_guardados(contenido, tuple(refs))
        de_excel = ss[P + "textos_excel"].get("valores", {}) if ss[P + "textos_excel"].get("huella") == huella else {}
        for vid, t in config["textos"].items():
            editor_fuente_texto(vid, variables.get(vid, {"nombre": vid, "usos": []}), t, plant, visibles,
                                avisos.get(vid, []), clave, guardados, de_excel)

    if pendientes:
        st.caption(f"Falta completar: {', '.join(pendientes)}. Se puede guardar igual y seguir después.")


def editor_imagen(lugar, d, plant, img, info, visibles, avisos, clave, contenido, nombre_archivo, huella, actualizar):
    iid = lugar["id"]
    with st.container(border=True):
        izq, der = st.columns([1, 2.2], gap="medium")
        with izq:
            st.image(esquema.svg(d, plant["tamano_diapositiva"], resaltado=iid), width="stretch")
            c = lugar["caja"]
            st.caption(f"Recuadro de {pl.cm(c['ancho'])} × {pl.cm(c['alto'])} cm")
        with der:
            st.markdown(f"**{escape(lugar['nombre'])}**")
            st.caption(f"{lugar['clase']} – `{iid}`")

            k_hoja = clave("hoja", iid)
            opciones = [SIN_HOJA] + visibles + ([img["hoja"]] if img["hoja"] and img["hoja"] not in visibles else [])

            def hoja_cambiada(_viejo):
                hoja = info.hoja(img["hoja"])
                if img["grafico"] and (hoja is None or img["grafico"] not in [g.nombre for g in hoja.graficos]):
                    img["grafico"] = ss[clave("graf", iid)] = ""

            c1, c2 = st.columns(2)
            c1.selectbox("Hoja", opciones, key=k_hoja, on_change=ligar(img, "hoja", k_hoja, hoja_cambiada),
                         format_func=lambda h: "— elegí una hoja —" if h == SIN_HOJA else
                         (h if h in visibles else f"{h} (no está en este Excel)"))
            k_toma = clave("toma", iid)

            def toma_cambiada(_viejo):
                if img["toma"] == cf.RANGO:  # de un rango solo se puede hacer captura
                    img["modo"] = ss[clave("modo", iid)] = cf.CAPTURA

            c2.radio("Qué toma", list(TOMAS), format_func=TOMAS.get, key=k_toma, horizontal=True,
                     on_change=ligar(img, "toma", k_toma, toma_cambiada))

            hoja = info.hoja(img["hoja"])
            if img["toma"] == cf.RANGO:
                c1, c2 = st.columns(2)
                for col, campo, ejemplo in ((c1, "desde", "A5"), (c2, "hasta", "N41")):
                    k = clave(campo, iid)
                    col.text_input(campo.capitalize(), key=k, placeholder=f"Ej.: {ejemplo}",
                                   on_change=ligar(img, campo, k))
            else:
                graficos = hoja.graficos if hoja else []
                nombres = [g.nombre for g in graficos]
                k_graf = clave("graf", iid)
                ops = [""] + nombres + ([img["grafico"]] if img["grafico"] and img["grafico"] not in nombres else [])
                descripciones = {g.nombre: g.descripcion() for g in graficos}
                st.selectbox("Gráfico", ops, key=k_graf, on_change=ligar(img, "grafico", k_graf),
                             format_func=lambda n: "— elegí un gráfico —" if not n else
                             descripciones.get(n, f"{n} (no está en esta hoja)"),
                             disabled=not img["hoja"])
                if img["hoja"] and not graficos:
                    st.caption("Esta hoja no tiene gráficos.")

            c1, c2 = st.columns(2)
            k_modo = clave("modo", iid)
            if img["toma"] == cf.RANGO:
                c1.radio("Modo", [cf.CAPTURA], format_func=MODOS.get, key=clave("modo_fijo", iid), disabled=True,
                         help="El gráfico pegado solo se puede elegir si se toma un gráfico, no un rango.")
            else:
                c1.radio("Modo", list(MODOS), format_func=MODOS.get, key=k_modo, on_change=ligar(img, "modo", k_modo))
            k_aj = clave("ajuste", iid)
            c2.selectbox("Ajuste en el recuadro", list(cf.AJUSTES), format_func=cf.AJUSTES.get, key=k_aj,
                         on_change=ligar(img, "ajuste", k_aj), help="Siempre queda centrado en el recuadro.")
            st.caption("Estilo visual: se define en la etapa 3.")

            for e in cf.errores_imagen(img) + avisos:
                st.warning(e)

            listo = cf.esta_completa_imagen(img) and not cf.errores_imagen(img) and not avisos
            if st.button("👁️ Vista previa", key=clave("vista", iid), disabled=not listo):
                hacer_vistas(contenido, nombre_archivo, huella, {iid: img}, [], actualizar)
                st.rerun()
            vista = ss[P + "vistas"].get(iid)
            if vista and vista["firma"] == firma(huella, img):
                cap = vista["captura"]
                if isinstance(cap, Exception):
                    st.error(f"No se pudo capturar: {cap}")
                else:
                    st.image(cf.vista_en_recuadro(cap.png, lugar["caja"], img["ajuste"]), width="stretch")
                    ancho, alto = cap.tamano
                    st.caption(f"Así queda en el recuadro (punteado rojo). Captura de {ancho} × {alto} px – "
                               f"{cap.metodo}" + (" – en el informe va como gráfico editable (se pega en la "
                                                  "etapa 3)" if img["modo"] == cf.GRAFICO else ""))
                    for a in cap.avisos:
                        st.caption(f"⚠️ {a}")


def editor_fuente_texto(vid, variable, t, plant, visibles, avisos, clave, guardados, de_excel):
    with st.container(border=True):
        st.markdown(f"**{escape(variable['nombre'])}**")
        textos = {tt["id"]: tt for d in plant["diapositivas"] for tt in d["textos"]}
        donde = [f"diap. {n}: «{pl.corto(textos[tid]['contenido'], 50)}»" for n, tid in variable["usos"] if tid in textos]
        st.caption(f"`{vid}` – " + "; ".join(donde))
        k_f = clave("fuente", vid)
        st.radio("Fuente", list(FUENTES), format_func=FUENTES.get, key=k_f, horizontal=True,
                 on_change=ligar(t, "fuente", k_f))
        if t["fuente"] == cf.LIBRE:
            k = clave("defecto", vid)
            st.text_input("Valor por defecto (opcional)", key=k, on_change=ligar(t, "por_defecto", k),
                          help="Se propone al generar el informe; ahí se puede cambiar.")
            return
        c1, c2 = st.columns([2, 1])
        k_h = clave("thoja", vid)
        opciones = [SIN_HOJA] + visibles + ([t["hoja"]] if t["hoja"] and t["hoja"] not in visibles else [])
        c1.selectbox("Hoja", opciones, key=k_h, on_change=ligar(t, "hoja", k_h),
                     format_func=lambda h: "— elegí una hoja —" if h == SIN_HOJA else
                     (h if h in visibles else f"{h} (no está en este Excel)"))
        k_c = clave("tcelda", vid)
        c2.text_input("Celda", key=k_c, placeholder="Ej.: D32", on_change=ligar(t, "celda", k_c))
        for e in cf.errores_texto(t) + avisos:
            st.warning(e)
        celda = ez.normalizar_celda(t["celda"])
        if t["hoja"] in visibles and celda:
            ref = ez.ref_celda(t["hoja"], celda)
            if ref in de_excel:
                valor, origen = de_excel[ref], "según Excel"
            else:
                valor, origen = guardados.get(ref), "último valor guardado en el archivo"
            texto = escape(valor) if valor else "<span class='inf-vacio'>(celda vacía)</span>"
            st.html(f"<div class='inf-valor'><b>{escape(ref)}</b> = {texto} "
                    f"<span style='opacity:.6;font-size:.85em'>({origen})</span></div>")


def resumen_config(config: dict, plant: dict):
    nombres = {img["id"]: img["nombre"] for _, img in cf.lugares(plant)}
    filas = [{"Lugar de imagen": nombres.get(iid, iid), "Hoja": img["hoja"],
              "Toma": img["grafico"] if img["toma"] == cf.GRAFICO else (ez.armar_rango(img["desde"], img["hasta"]) or ""),
              "Modo": MODOS[img["modo"]], "Ajuste": cf.AJUSTES[img["ajuste"]]}
             for iid, img in config["imagenes"].items()]
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
    variables = pl.variables(plant)
    filas = [{"Texto variable": variables.get(vid, {}).get("nombre", vid), "Fuente": FUENTES[t["fuente"]],
              "De dónde": (ez.ref_celda(t["hoja"], t["celda"]) if t["hoja"] else "") if t["fuente"] == cf.CELDA
              else t["por_defecto"]} for vid, t in config["textos"].items()]
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)


if seccion == SECCIONES[1]:
    if P + "cfg" in ss:
        pantalla_editor_config()
    else:
        pantalla_lista_configs()
elif P + "edit" in ss:
    pantalla_editor()
else:
    pantalla_lista()
