"""Módulo: Transcripciones del LG (PDF escaneado del Libro de Guardia → Excel, con la API de Claude)."""
import copy
import hashlib
import os
import threading
import time

import anthropic
import pandas as pd
import streamlit as st

from src import transcripcion_lg as tl

st.title("Transcripciones del LG")
st.caption("Transcribe a Excel el PDF escaneado del Libro de Guardia de Señalamiento, con la API de "
           "Claude. El PDF se manda en tandas de 3 páginas, una detrás de otra.")

ss = st.session_state
P = "tlg_"  # prefijo de las claves de este módulo en session_state
SECCIONES = ["① Transcribir", "② Revisar y exportar", "⚙️ Configuración"]

# Correcciones a mano: {clave de la fila: {"texto": corregido, "base": texto original al corregir}}.
# Todo vive solo en memoria: si se recarga la página, se pierde (también la transcripción).
ss.setdefault(P + "correcciones", {})
ss.setdefault(P + "seccion", SECCIONES[0])
if siguiente := ss.pop(P + "ir_a", None):
    ss[P + "seccion"] = siguiente
seccion = st.segmented_control("Sección", SECCIONES, key=P + "seccion",
                               label_visibility="collapsed") or SECCIONES[0]


@st.cache_data(show_spinner="Convirtiendo las páginas del PDF en imágenes...", max_entries=2)
def imagenes_pdf(contenido: bytes) -> list[bytes]:
    return tl.paginas_a_imagenes(contenido)


def sesion() -> dict | None:
    return ss.get(P + "sesion")


def procesando() -> bool:
    s = sesion()
    return bool(s and s["procesando"])


def documentos() -> tuple[str, str]:
    return tl.leer_documento("instrucciones"), tl.leer_documento("referencia")


def hay_clave() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


# --------------------------------------------------------------- proceso de fondo
def lanzar(indices: list[int]) -> None:
    """Arranca (en un hilo aparte) el procesamiento de las tandas indicadas, de a una y en orden.

    La pantalla sigue libre: se puede ir a ② y ver las páginas a medida que llegan.
    """
    s = sesion()
    ajustes = tl.leer_ajustes()
    modelo, esfuerzo = ajustes["modelo"], ajustes["esfuerzo"]
    instrucciones, referencia = documentos()
    system = tl.system_prompt(instrucciones, referencia)
    client = anthropic.Anthropic()

    def llamar(system, contenido):
        return tl.llamar_api(client, modelo, system, contenido, esfuerzo)

    for i in indices:
        t = s["tandas"][i]
        t.estado, t.resultado, t.error = "pendiente", None, ""
    # Las correcciones de las tandas que se rehacen ya no corresponden.
    rehechas = {str(i) for i in indices}
    ss[P + "correcciones"] = {k: v for k, v in ss[P + "correcciones"].items()
                              if k.split(":")[0] not in rehechas}
    s.update(procesando=True, actual=None, faltan=len(indices), inicio_tanda=time.time(), duraciones=[],
             latido=time.time(), aviso="", cancelar=False, esfuerzo=esfuerzo)
    ss[P + "version_vista"] = s["version"]
    threading.Thread(target=tl.trabajar, args=(s, indices, llamar, system, modelo), daemon=True).start()


@st.fragment(run_every=2)
def avance(completo: bool) -> None:
    """Se refresca cada 2 s mientras se transcribe: muestra el avance y le avisa al proceso de
    fondo que la página sigue abierta. Cuando llega una tanda nueva, actualiza toda la pantalla."""
    s = sesion()
    if s is None:
        return
    s["latido"] = time.time()
    if s["version"] != ss.get(P + "version_vista"):
        ss[P + "version_vista"] = s["version"]
        if seccion != SECCIONES[2] or not s["procesando"]:  # en ⚙️ no interrumpir la edición
            st.rerun()
    if not s["procesando"]:
        return
    tandas = s["tandas"]
    i = s["actual"] if s["actual"] is not None else 0
    en_curso = time.time() - s["inicio_tanda"]
    hechas = sum(s["duraciones"])
    restante = tl.tiempo_restante(s["duraciones"], s["faltan"], en_curso,
                                  tl.SEGUNDOS_POR_TANDA[s["esfuerzo"]])
    minutos = max(1, round(restante / 60))
    texto = (f"⏳ Transcribiendo la tanda {i + 1} de {len(tandas)} ({tandas[i].nombre}) · "
             f"faltan ≈ {minutos} min")
    if completo:
        st.progress(min((hechas + en_curso) / max(hechas + en_curso + restante, 1), 0.99), text=texto)
        st.caption("Podés ir revisando las páginas que ya llegaron. No recargues la página ni cierres la "
                   "app: se pierde todo y la transcripción se frena.")
    else:
        st.info(texto + ". El avance y las páginas que ya llegaron se ven en ② Revisar y exportar.")


# ================================================================ ① Transcribir
# Enter en las fechas del nombre: de la fecha «de» pasa a la fecha «a»; en la «a», termina.
ENTER_FECHAS = """<script>
(function () {
  if (window.__tlgEnterFechas) return;
  window.__tlgEnterFechas = true;
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    const el = document.activeElement;
    const desde = el && el.closest('.st-key-tlg_desde');
    const hasta = el && el.closest('.st-key-tlg_hasta');
    if (!desde && !hasta) return;
    e.preventDefault();
    e.stopPropagation();
    el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));  // cierra el calendario
    if (desde) {
      const dia = document.querySelector('.st-key-tlg_hasta [role="spinbutton"]');
      if (dia) { dia.focus(); return; }
    }
    el.blur();
  }, true);
})();
</script>"""


def pantalla_transcribir():
    ocupado = procesando()
    if ocupado:
        avance(False)
        # Todo en gris hasta que termine el PDF actual.
        st.html("<style>.st-key-tlg_carga { opacity: .5; }</style>")
    st.html(ENTER_FECHAS, unsafe_allow_javascript=True)

    with st.container(key=P + "carga"):
        st.header("1. PDF del Libro de Guardia")
        archivo = st.file_uploader("Subí el PDF escaneado del LG", type=["pdf"], key=P + "pdf",
                                   disabled=ocupado)

        st.markdown("**Nombre del documento final (Excel)**")
        c = st.columns([1.35, 2, .25, 2, .5], vertical_alignment="center")
        c[0].markdown("Transcripciones de")
        desde = c[1].date_input("Desde", value=None, format="DD/MM/YYYY", key=P + "desde",
                                label_visibility="collapsed", disabled=ocupado, persist_state="session")
        c[2].markdown("a")
        hasta = c[3].date_input("Hasta", value=None, format="DD/MM/YYYY", key=P + "hasta",
                                label_visibility="collapsed", disabled=ocupado, persist_state="session")
        c[4].markdown(".xlsx")
        st.caption("Escribí día, mes y año seguidos; con **Enter** pasás a la segunda fecha y con otro "
                   "**Enter** terminás. La primera fecha también se le pasa a Claude como la del primer "
                   "turno, por si la primera página no la muestra.")
        if desde and hasta and hasta < desde:
            st.warning("La segunda fecha es anterior a la primera.")

        if archivo is None:
            if not ocupado:
                st.info("Subí el PDF para empezar.")
            return

        contenido = archivo.getvalue()
        try:
            imagenes = imagenes_pdf(contenido)
        except Exception as e:  # PDF dañado o con contraseña
            st.error(f"No se pudo leer el PDF: {e}")
            return
        pdf_id = hashlib.sha1(contenido).hexdigest()
        n_tandas = len(tl.armar_tandas(len(imagenes)))
        instrucciones, referencia = documentos()
        ajustes = tl.leer_ajustes()
        modelo, esfuerzo = ajustes["modelo"], ajustes["esfuerzo"]
        estimado = tl.estimar_costo(len(imagenes), tl.tokens_aprox(instrucciones + referencia), modelo, esfuerzo)
        minutos = round(n_tandas * tl.SEGUNDOS_POR_TANDA[esfuerzo] / 60)
        st.markdown(f"**{len(imagenes)} páginas** → **{n_tandas} tandas** de hasta {tl.PAGINAS_POR_TANDA} "
                    f"páginas. Modelo: `{modelo}` · esfuerzo **{tl.ESFUERZOS[esfuerzo].split(' (')[0].lower()}**. "
                    f"Costo estimado: **≈ US\\$ {estimado:.2f}** · tiempo ≈ {max(minutos, 1)} min (a ojo). "
                    "Modelo y esfuerzo se cambian en ⚙️ Configuración.")
        with st.expander("Ver las páginas"):
            n = st.number_input("Página", 1, len(imagenes), 1, key=P + "ver_pag")
            st.image(imagenes[n - 1], width=450)

        if ocupado:
            return
        if not hay_clave():
            st.error("Falta la clave de Anthropic. Creá el archivo `.env` en la carpeta de la app (copiando "
                     "`.env.example`), poné tu clave en `ANTHROPIC_API_KEY=...` y volvé a abrir la app.")
            return

        s = sesion()
        if s is not None and s["pdf_id"] == pdf_id:
            pendientes = [i for i, t in enumerate(s["tandas"]) if t.estado == "pendiente"]
            if pendientes:
                st.warning(f"La transcripción de este PDF quedó a medias: faltan {len(pendientes)} tanda(s).")
                if st.button("▶️ Continuar con las que faltan", type="primary"):
                    lanzar(pendientes)
                    ss[P + "ir_a"] = SECCIONES[1]
                    st.rerun()
            else:
                st.success("Este PDF ya está transcripto. Revisalo en ② Revisar y exportar.")
            texto_boton, tipo = "🔁 Transcribir de nuevo desde cero", "secondary"
        else:
            if s is not None:
                st.warning(f"Hay otra transcripción en memoria ({s['nombre']}). Si empezás esta, se pierde: "
                           "descargá antes su Excel si lo necesitás.")
            texto_boton, tipo = "▶️ Transcribir", "primary"

        if st.button(texto_boton, type=tipo):
            ss[P + "sesion"] = {
                "pdf_id": pdf_id, "nombre": archivo.name, "imagenes": imagenes,
                "fecha_contexto": desde.strftime("%d/%m/%Y") if desde else "",
                "tandas": [tl.Tanda(p) for p in tl.armar_tandas(len(imagenes))],
                "version": 0, "procesando": False,
            }
            ss[P + "correcciones"] = {}
            lanzar(list(range(n_tandas)))
            ss[P + "ir_a"] = SECCIONES[1]
            st.rerun()


# ======================================================== ② Revisar y exportar
def filas_finales(unidas: list[tl.Fila]) -> list[dict]:
    """Filas unidas, con las correcciones a mano aplicadas."""
    correcciones = ss[P + "correcciones"]
    return [{"Folio": f.folio, "Fecha": f.fecha, "Hora": f.hora,
             "Transcripción": tl.aplicar_correccion(f.transcripcion, correcciones.get(f.clave)),
             "Revisar": "; ".join(f.revisar), "clave": f.clave, "original": f.transcripcion}
            for f in unidas]


def al_guardar_correcciones(campos: list[tuple[str, str, str]]) -> None:
    """campos: (clave de la fila, clave del cuadro de texto, texto original de la fila)."""
    cambios = 0
    for clave, widget, original in campos:
        texto = tl._limpiar(ss[widget]).strip()
        actual = tl.aplicar_correccion(original, ss[P + "correcciones"].get(clave))
        if texto != actual:
            ss[P + "correcciones"][clave] = {"texto": texto, "base": original}
            cambios += 1
    ss[P + "msg_corr"] = ("success", "Corrección guardada.") if cambios else ("info", "No había cambios.")


def reintentar(i: int, hasta_el_final: bool) -> None:
    tandas = sesion()["tandas"]
    ss.pop(P + "reintentar", None)
    lanzar(list(range(i, len(tandas))) if hasta_el_final else [i])


def seccion_proceso(s: dict) -> None:
    tandas = s["tandas"]
    st.header("Proceso")
    if s["procesando"]:
        avance(True)
        return
    if s.get("aviso"):
        st.error(s["aviso"] + " Se frenó la transcripción: cuando esté resuelto, reintentá abajo.")
    fallidas = [i for i, t in enumerate(tandas) if t.estado == "error"]
    pendientes = [i for i, t in enumerate(tandas) if t.estado == "pendiente"]
    if not fallidas and not pendientes:
        st.success(f"✅ Listo: se transcribieron las {len(s['imagenes'])} páginas.")
        return
    for i in fallidas:
        c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
        c1.error(f"Tanda {i + 1} ({tandas[i].nombre}): {tandas[i].error or 'error'}", icon="❌")
        if c2.button("🔁 Reintentar", key=f"{P}reint_{i}", width="stretch"):
            ss[P + "reintentar"] = i
    if pendientes:
        c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
        c1.warning(f"Faltan {len(pendientes)} tanda(s) sin transcribir.", icon="⏳")
        if c2.button("▶️ Continuar", key=P + "continuar", width="stretch"):
            lanzar(pendientes)
            st.rerun()

    if (i := ss.get(P + "reintentar")) is not None and i < len(tandas):
        with st.container(border=True):
            siguientes = i + 1 < len(tandas) and any(t.estado == "ok" for t in tandas[i + 1:])
            if siguientes:
                st.warning(
                    f"Vas a reintentar la **tanda {i + 1}**. Las tandas van en fila: la {i + 2} usó el final "
                    f"de esta como contexto, así que si la {i + 1} cambia, la {i + 2} (y las que siguen) "
                    "pueden quedar desalineadas: filas repetidas o un párrafo partido en dos.")
            b1, b2, b3 = st.columns(3)
            if b1.button(f"Reintentar solo la tanda {i + 1}", type="primary", width="stretch"):
                reintentar(i, hasta_el_final=False)
                st.rerun()
            if i + 1 < len(tandas) and b2.button(f"Reintentar de la {i + 1} hasta el final", width="stretch"):
                reintentar(i, hasta_el_final=True)
                st.rerun()
            if b3.button("Cancelar", width="stretch"):
                ss.pop(P + "reintentar")
                st.rerun()


def seccion_comparar(s: dict, tandas: list[tl.Tanda], unidas: list[tl.Fila], filas: list[dict]) -> None:
    st.header("Comparar con el libro")
    paginas = tl.paginas_revisables(tandas, unidas)
    if not paginas:
        st.info("Todavía no llegó ninguna página. Aparecen acá a medida que Claude las transcribe.")
        return
    st.caption("Elegí un folio: a la izquierda su transcripción (se puede corregir) y a la derecha la "
               "página escaneada.")

    def etiqueta(k):
        pag = paginas[k]
        folio = f"folio {pag['folio']:02d}" if pag["folio"] is not None else f"pág. {pag['pagina'] + 1} del PDF"
        fechas = pag["fechas"]
        fecha = (fechas[0] if len(fechas) == 1 else f"{fechas[0]} al {fechas[-1]}") if fechas else "sin fecha"
        return f"{folio} · {fecha}"

    k = st.selectbox("Folio", range(len(paginas)), format_func=etiqueta, key=P + "folio")
    pag = paginas[min(k or 0, len(paginas) - 1)]
    izq, der = st.columns([1, 1], gap="medium")
    with izq:
        if msg := ss.pop(P + "msg_corr", None):
            getattr(st, msg[0])(msg[1])
        if not pag["filas"]:
            st.info("Esta página no tiene texto transcripto.")
        else:
            campos = []
            with st.form(P + "form_corr", border=False):
                for n in pag["filas"]:
                    f = filas[n]
                    # La clave cambia si el texto cambia (p. ej. llegó la continuación): el cuadro se renueva.
                    widget = f"{P}corr_{f['clave']}_{hashlib.sha1(f['Transcripción'].encode()).hexdigest()[:8]}"
                    campos.append((f["clave"], widget, f["original"]))
                    etiqueta_fila = f"{f['Folio']} · {f['Fecha'] or 'sin fecha'}"
                    if f["Revisar"]:
                        etiqueta_fila += f" · ⚠️ revisar: {f['Revisar']}"
                    st.text_area(etiqueta_fila, value=f["Transcripción"], key=widget,
                                 height=520 if len(pag["filas"]) == 1 else 300)
                st.form_submit_button("💾 Guardar corrección", type="primary",
                                      on_click=al_guardar_correcciones, args=(campos,))
    with der:
        st.image(s["imagenes"][pag["pagina"]], width="stretch")


def pantalla_revisar():
    s = sesion()
    if s is None:
        st.info("Todavía no hay ninguna transcripción. Empezá en ① Transcribir.")
        return
    # Foto fija de las tandas: el proceso de fondo las puede cambiar mientras se dibuja la pantalla.
    tandas = [copy.copy(t) for t in s["tandas"]]
    unidas = tl.unir_tandas(tandas)
    filas = filas_finales(unidas)
    seccion_proceso(s)

    res = tl.resumen(unidas, tandas)
    res["dudosos"] = sum(f["Transcripción"].count("[?]") for f in filas)
    res["ilegibles"] = sum(f["Transcripción"].lower().count("[ilegible]") for f in filas)
    uso = tl.uso_total(tandas)
    st.header("Resumen")
    st.caption(f"Archivo: {s['nombre']} · {len(s['imagenes'])} páginas · {len(tandas)} tandas")
    c = st.columns(6)
    c[0].metric("Filas", res["filas"])
    c[1].metric("[?] dudosos", res["dudosos"])
    c[2].metric("[ilegible]", res["ilegibles"])
    c[3].metric("Tandas con error", len(res["tandas_error"]))
    c[4].metric("Filas para revisar", res["para_revisar"])
    c[5].metric("Costo (US$)", f"{uso['costo']:.2f}",
                help=f"{uso['llamadas']} llamadas · {uso['entrada']:,} tokens de entrada · "
                     f"{uso['salida']:,} de salida (incluye reintentos)".replace(",", "."))

    seccion_comparar(s, tandas, unidas, filas)
    if not filas:
        return

    st.header("Vista previa del Excel")
    st.dataframe(pd.DataFrame(filas)[["Folio", "Fecha", "Hora", "Transcripción", "Revisar"]],
                 hide_index=True, width="stretch", height=min(35 * len(filas) + 38, 420),
                 column_config={"Folio": st.column_config.TextColumn(width=130),
                                "Fecha": st.column_config.TextColumn(width=95),
                                "Hora": st.column_config.TextColumn(width=60),
                                "Transcripción": st.column_config.TextColumn(width="large"),
                                "Revisar": st.column_config.TextColumn(
                                    width="medium", help="Solo para mirar: no va al Excel.")})

    st.header("Exportar")
    nombre = tl.nombre_excel(ss.get(P + "desde"), ss.get(P + "hasta"), filas)
    if s["procesando"]:
        st.button(f"⬇️ Descargar {nombre}", disabled=True, key=P + "descargar_off")
        st.caption("Se puede descargar cuando termine la transcripción.")
        return
    if res["tandas_error"] or res["tandas_pendientes"]:
        st.warning("Ojo: faltan tandas (" + ", ".join(res["tandas_error"] + res["tandas_pendientes"])
                   + "). El Excel sale sin esas páginas.")
    exportables = [{k: f[k] for k in tl.COLUMNAS} for f in filas]
    st.download_button(f"⬇️ Descargar {nombre}", tl.exportar_excel(exportables), nombre,
                       type="primary", key=P + "descargar")
    st.caption(f"Una hoja con Folio, Fecha, Hora y Transcripción · {res['filas']} filas · "
               f"{res['dudosos']} [?] · {res['ilegibles']} [ilegible] · "
               f"tandas con error: {', '.join(res['tandas_error']) or 'ninguna'}. "
               "El nombre se elige en ① Transcribir.")


# ============================================================ ⚙️ Configuración
NOMBRES = {"instrucciones": "Instrucciones (system prompt)", "referencia": "Documento de referencia"}
LIMITE_TOKENS = {"instrucciones": 2000, "referencia": 6000}


def al_guardar(clave: str) -> None:
    if tl.guardar_documento(clave, ss[f"{P}doc_{clave}"]):
        ss[P + "msg"] = ("success", f"{NOMBRES[clave]}: guardado. La versión anterior quedó en el historial.")
    else:
        ss[P + "msg"] = ("info", f"{NOMBRES[clave]}: no había cambios para guardar.")


def al_restaurar(clave: str, texto: str, que: str) -> None:
    tl.guardar_documento(clave, texto)
    ss[f"{P}doc_{clave}"] = tl.leer_documento(clave)
    ss[P + "msg"] = ("success", f"{NOMBRES[clave]}: se restauró {que}. La versión que había quedó en el historial.")


def al_descartar(clave: str) -> None:
    ss[f"{P}doc_{clave}"] = tl.leer_documento(clave)


def al_probar_conexion() -> None:
    modelo = tl.leer_ajustes()["modelo"]
    if not hay_clave():
        ss[P + "conexion"] = ("error", "No se encontró la clave: falta la línea ANTHROPIC_API_KEY=... en el "
                                  "archivo .env de la carpeta de la app (después de crearla, volvé a abrir la app).")
        return
    try:
        nombre = tl.probar_conexion(anthropic.Anthropic(), modelo)
    except anthropic.APIError as e:
        ss[P + "conexion"] = ("error", tl.explicar_error(e, modelo)[0])
    except Exception as e:  # p. ej. clave con formato raro
        ss[P + "conexion"] = ("error", f"No se pudo probar la conexión: {e}")
    else:
        ss[P + "conexion"] = ("success", f"Conexión OK: la clave funciona, la red deja llegar a Anthropic y el "
                                    f"modelo {nombre} está disponible. (El crédito que queda se ve en la consola.)")


def al_guardar_ajustes() -> None:
    ajustes = tl.leer_ajustes()
    ajustes.update(modelo=ss[P + "modelo"], esfuerzo=ss[P + "esfuerzo"])
    tl.guardar_ajustes(ajustes)
    ss[P + "msg_ajustes"] = f"Guardado: {tl.MODELOS[ajustes['modelo']].split(' (')[0]} con esfuerzo " \
                            f"{tl.ESFUERZOS[ajustes['esfuerzo']].split(' (')[0].lower()}."


def al_descartar_ajustes() -> None:
    ajustes = tl.leer_ajustes()
    ss[P + "modelo"], ss[P + "esfuerzo"] = ajustes["modelo"], ajustes["esfuerzo"]


def pantalla_configuracion():
    if procesando():
        avance(False)
    # Editores en letra monoespaciada: con Overpass los ` de los documentos se montan sobre la letra anterior.
    st.html("<style>.st-key-tlg_doc_instrucciones textarea, .st-key-tlg_doc_referencia textarea "
            "{ font-family: ui-monospace, Consolas, Menlo, monospace; font-size: .85rem; }</style>")
    if msg := ss.pop(P + "msg", None):
        getattr(st, msg[0])(msg[1])
    st.caption("Lo que se guarda acá queda en la carpeta `config/transcripcion_lg/` del proyecto: sigue "
               "ahí aunque cierres la app. Para llevarlo a la otra compu, subilo a GitHub (ver la guía).")

    st.header("Modelo y esfuerzo")
    ajustes = tl.leer_ajustes()
    ss.setdefault(P + "modelo", ajustes["modelo"])
    ss.setdefault(P + "esfuerzo", ajustes["esfuerzo"])
    c1, c2 = st.columns(2)
    c1.selectbox("Modelo de Claude", list(tl.MODELOS), format_func=lambda m: f"{tl.MODELOS[m]} · {m}",
                 key=P + "modelo")
    c2.selectbox("Esfuerzo", list(tl.ESFUERZOS), format_func=lambda e: tl.ESFUERZOS[e], key=P + "esfuerzo")
    sin_guardar = (ss[P + "modelo"], ss[P + "esfuerzo"]) != (ajustes["modelo"], ajustes["esfuerzo"])
    b = st.columns([1, 1, 2], vertical_alignment="center")
    b[0].button("💾 Guardar", key=P + "guardar_ajustes", type="primary", width="stretch",
                on_click=al_guardar_ajustes)
    b[1].button("↩️ Descartar cambios", key=P + "descartar_ajustes", width="stretch",
                on_click=al_descartar_ajustes, disabled=not sin_guardar)
    if sin_guardar:
        b[2].markdown("✏️ **cambios sin guardar**")
    if msg := ss.pop(P + "msg_ajustes", None):
        st.success(msg)
    entrada, salida, _, _ = tl.PRECIOS[ss[P + "modelo"]]
    st.caption(f"Precio: US\\$ {entrada:g} por millón de tokens de entrada y US\\$ {salida:g} por millón de "
               f"salida. Las tandas son siempre de {tl.PAGINAS_POR_TANDA} páginas.")
    st.caption("**Esfuerzo**: cuánto analiza Claude cada página antes de responder. Con más esfuerzo lee "
               "la letra con más cuidado (menos [?] y menos errores en números), pero tarda más y cuesta "
               "más, porque ese análisis se cobra como texto de salida. Con «Guardar» queda para las "
               "próximas transcripciones (una que ya está en curso sigue con lo que tenía).")

    st.header("Conexión con Claude")
    clave = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if clave:
        st.markdown(f"Clave de Anthropic: ✅ encontrada en el `.env` (termina en `…{clave[-4:]}`).")
    else:
        st.markdown("Clave de Anthropic: ❌ **no encontrada**. Creá el archivo `.env` (copiando `.env.example`) "
                    "con la línea `ANTHROPIC_API_KEY=...` y volvé a abrir la app.")
    st.button("🔌 Probar la conexión con Claude", key=P + "probar", on_click=al_probar_conexion)
    st.caption("Comprueba la clave, que la red deje llegar a api.anthropic.com y que el modelo esté "
               "disponible. No gasta crédito.")
    if resultado := ss.pop(P + "conexion", None):
        getattr(st, resultado[0])(resultado[1])

    for clave in ("instrucciones", "referencia"):
        st.header(NOMBRES[clave])
        guardado = tl.leer_documento(clave)
        ss.setdefault(f"{P}doc_{clave}", guardado)
        texto = st.text_area(NOMBRES[clave], key=f"{P}doc_{clave}", height=420,
                             label_visibility="collapsed")
        tokens = tl.tokens_aprox(texto)
        sin_guardar = tl._limpiar(texto) != guardado
        info = f"≈ **{tokens:,} tokens**".replace(",", ".") + f" · {len(texto):,} caracteres".replace(",", ".")
        if sin_guardar:
            info += " · ✏️ **cambios sin guardar**"
        st.markdown(info)
        if tokens > LIMITE_TOKENS[clave]:
            st.warning(f"Está creciendo: pasa de ≈ {LIMITE_TOKENS[clave]:,} tokens. ".replace(",", ".")
                       + "Cada tanda lo manda entero (aunque con caché sale más barato desde la 2.ª).")
        b = st.columns(3)
        b[0].button("💾 Guardar", key=f"{P}guardar_{clave}", type="primary", width="stretch",
                    on_click=al_guardar, args=(clave,))
        b[1].button("↩️ Descartar cambios", key=f"{P}descartar_{clave}", width="stretch",
                    on_click=al_descartar, args=(clave,), disabled=not sin_guardar)
        original = tl.leer_original(clave)
        b[2].button("⏮️ Restaurar original", key=f"{P}original_{clave}", width="stretch",
                    on_click=al_restaurar, args=(clave, original, "el original"),
                    disabled=guardado == original and not sin_guardar)
        versiones = tl.historial(clave)
        with st.expander(f"Historial ({len(versiones)} versiones anteriores)"):
            if not versiones:
                st.caption("Todavía no hay versiones anteriores: aparecen al guardar.")
            else:
                elegida = st.selectbox(
                    "Versión", range(len(versiones)), key=f"{P}hist_{clave}",
                    format_func=lambda k: f"Reemplazada el {versiones[k][0]:%d/%m/%Y %H:%M:%S} "
                                          f"(≈ {tl.tokens_aprox(versiones[k][1].read_text(encoding='utf-8')):,} tokens)".replace(",", "."))
                anterior = versiones[elegida][1].read_text(encoding="utf-8")
                st.code(anterior, language="markdown", wrap_lines=True, height=300)
                st.button("Restaurar esta versión", key=f"{P}rest_{clave}", on_click=al_restaurar,
                          args=(clave, anterior, f"la versión del {versiones[elegida][0]:%d/%m/%Y %H:%M}"))


if seccion == SECCIONES[0]:
    pantalla_transcribir()
elif seccion == SECCIONES[1]:
    pantalla_revisar()
else:
    pantalla_configuracion()
