"""Módulo: Informes PowerPoint (etapa 1: plantillas)."""
import copy
from html import escape

import pandas as pd
import streamlit as st

from src.informes_pptx import esquema, office
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


OF = obtener_office()

st.html("""<style>
mark { background: #FFE27A; color: inherit; padding: 0 .1em; border-radius: 2px; }
.inf-contenido { border-left: 4px solid #8C8682; background: rgba(140,134,130,.08); border-radius: .3rem;
                 padding: .45rem .7rem; white-space: pre-wrap; line-height: 1.4; font-size: .95rem; }
.inf-contenido.variable { border-left-color: #C98A00; background: rgba(255,226,122,.25); }
.inf-vacio { opacity: .55; font-style: italic; }
.inf-etiqueta { display: inline-block; min-width: 2.2rem; text-align: center; color: #FFFFFF; font-weight: 700;
                font-size: .8rem; border-radius: .25rem; padding: .05rem .35rem; margin-right: .4rem; }
.inf-leyenda { font-size: .85rem; opacity: .85; margin-top: .3rem; }
.inf-leyenda span { display: inline-block; width: .8rem; height: .8rem; border-radius: 2px;
                    vertical-align: -1px; margin: 0 .25rem 0 .7rem; }
</style>""")

seccion = st.radio("Sección", SECCIONES, horizontal=True, key=P + "seccion", label_visibility="collapsed")
if seccion != "Plantillas":
    etapa = 2 if seccion == SECCIONES[1] else 3
    st.info(f"Esta sección llega en la etapa {etapa}. Por ahora se pueden armar las plantillas.")
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

    def ligar(obj: dict, campo: str, key: str, despues=None):
        """El campo del widget `key` queda guardado en obj[campo] (aunque se cambie de diapositiva)."""
        if key not in ss:
            ss[key] = obj[campo]

        def copiar():
            viejo = obj[campo]
            obj[campo] = ss[key]
            if despues:
                despues(viejo)
        return copiar

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
                editor_texto(i, t, d["numero"], usos, clave, ligar)
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


def editor_texto(i: int, t: dict, numero: int, usos: dict, clave, ligar):
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


if P + "edit" in ss:
    pantalla_editor()
else:
    pantalla_lista()
