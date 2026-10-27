"""Módulo: Transcripciones del LG (PDF escaneado del Libro de Guardia → Excel, con la API de Claude)."""
import hashlib
import json
import os
import re

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
ICONO = {"ok": "✅", "error": "❌", "pendiente": "⏳"}

ss.setdefault(P + "correcciones", {})   # {n° de fila: {"Folio"/"Fecha"/"Hora"/"Transcripción": texto}}
ss.setdefault(P + "version", 0)         # sube cuando cambian las filas (resetea los editores)
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


def documentos() -> tuple[str, str]:
    return tl.leer_documento("instrucciones"), tl.leer_documento("referencia")


def hay_clave() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


# --------------------------------------------------------------- procesamiento
def procesar(indices: list[int]) -> None:
    """Procesa las tandas indicadas de a una, en orden, mostrando el progreso."""
    s = sesion()
    tandas = s["tandas"]
    instrucciones, referencia = documentos()
    system = tl.system_prompt(instrucciones, referencia)
    ajustes = tl.leer_ajustes()
    modelo, esfuerzo = ajustes["modelo"], ajustes["esfuerzo"]
    client = anthropic.Anthropic()

    def llamar(system, contenido):
        return tl.llamar_api(client, modelo, system, contenido, esfuerzo)

    barra = st.progress(0.0)
    for k, i in enumerate(indices):
        t = tandas[i]
        barra.progress(k / len(indices), text=f"Tanda {i + 1} de {len(tandas)} ({t.nombre}): "
                                              "esperando la respuesta de Claude (puede tardar 1-2 minutos)...")
        contexto = tl.contexto_para(tandas, i, s["fecha_contexto"])
        contenido = tl.mensaje_usuario([s["imagenes"][p] for p in t.paginas], t.paginas, contexto)
        try:
            tl.procesar_tanda(t, llamar, system, contenido, contexto)
        except anthropic.APIError as e:
            mensaje, frenar = tl.explicar_error(e, modelo)
            t.estado, t.error = "error", mensaje
            t.intentos.append({"cruda": "", "uso": [], "error": mensaje, "contexto": contexto})
            if frenar:  # las demás tandas fallarían igual: se frena y se avisa
                ss[P + "aviso"] = (mensaje + " Se frenó la transcripción. Cuando esté resuelto, tocá "
                                   "«🔁 Reintentar» en la tanda con ❌ y elegí «hasta el final».")
                break
    barra.progress(1.0, text="Listo.")
    # Cambiaron las filas: las correcciones a mano ya no corresponden.
    ss[P + "correcciones"] = {}
    ss[P + "version"] += 1


def reintentar(i: int, hasta_el_final: bool) -> None:
    tandas = sesion()["tandas"]
    indices = list(range(i, len(tandas))) if hasta_el_final else [i]
    for j in indices:
        tandas[j].estado, tandas[j].resultado, tandas[j].error = "pendiente", None, ""
    ss.pop(P + "reintentar", None)
    procesar(indices)


# ================================================================ ① Transcribir
def pantalla_transcribir():
    st.header("1. PDF del Libro de Guardia")
    archivo = st.file_uploader("Subí el PDF escaneado del LG", type=["pdf"], key=P + "pdf")
    fecha = st.date_input(
        "Fecha de contexto (opcional)", value=None, format="DD/MM/YYYY", key=P + "fecha",
        help="La fecha del primer turno, por si la primera página no la muestra.")
    if archivo is None:
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
    st.markdown(f"**{len(imagenes)} páginas** → **{n_tandas} tandas** de hasta {tl.PAGINAS_POR_TANDA} "
                f"páginas. Modelo: `{modelo}` · esfuerzo **{tl.ESFUERZOS[esfuerzo].split(' (')[0].lower()}**. "
                f"Costo estimado: **≈ US\\$ {estimado:.2f}** (a ojo; el real se ve al terminar). "
                "Modelo y esfuerzo se cambian en ⚙️ Configuración.")
    with st.expander("Ver las páginas"):
        n = st.number_input("Página", 1, len(imagenes), 1, key=P + "ver_pag")
        st.image(imagenes[n - 1], width=450)

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
                procesar(pendientes)
                ss[P + "ir_a"] = SECCIONES[1]
                st.rerun()
        else:
            st.success("Este PDF ya está transcripto. Revisalo en ② Revisar y exportar.")
        texto_boton = "🔁 Transcribir de nuevo desde cero"
    else:
        if s is not None:
            st.warning(f"Hay otra transcripción en memoria ({s['nombre']}). Si empezás esta, se pierde: "
                       "descargá antes su Excel si lo necesitás.")
        texto_boton = "▶️ Transcribir"

    st.caption("Mientras transcribe no toques nada ni cambies de módulo: se cortaría la tanda en curso "
               "(lo ya hecho queda y se puede continuar).")
    if st.button(texto_boton, type="primary" if s is None or s["pdf_id"] != pdf_id else "secondary"):
        ss[P + "sesion"] = {
            "pdf_id": pdf_id, "nombre": archivo.name, "imagenes": imagenes,
            "fecha_contexto": fecha.strftime("%d/%m/%Y") if fecha else "",
            "tandas": [tl.Tanda(p) for p in tl.armar_tandas(len(imagenes))],
        }
        procesar(list(range(n_tandas)))
        ss[P + "ir_a"] = SECCIONES[1]
        st.rerun()


# ======================================================== ② Revisar y exportar
def filas_finales(s: dict) -> list[dict]:
    """Filas unidas con las correcciones a mano aplicadas."""
    filas = []
    for n, f in enumerate(tl.unir_tandas(s["tandas"])):
        fila = {"Folio": f.folio, "Fecha": f.fecha, "Hora": f.hora, "Transcripción": f.transcripcion,
                "Tanda": f.tanda + 1, "Revisar": "; ".join(f.revisar)}
        fila.update(ss[P + "correcciones"].get(n, {}))
        filas.append(fila)
    return filas


def corregir(n: int, campo: str, valor: str) -> None:
    ss[P + "correcciones"].setdefault(n, {})[campo] = valor


def al_editar_tabla(clave: str) -> None:
    for n, cambios in ss[clave]["edited_rows"].items():
        for campo, valor in cambios.items():
            corregir(int(n), campo, "" if valor is None else str(valor))
    ss[P + "version"] += 1  # resetea el editor (los cambios ya están en las correcciones)


def al_editar_texto(n: int, campo: str, clave: str) -> None:
    corregir(n, campo, ss[clave])
    ss[P + "version"] += 1


def pagina_probable(s: dict, filas: list[dict], n: int) -> list[int]:
    """Páginas para mirar al lado de la fila n: las de su tanda (+ la 1.ª de la siguiente)."""
    tandas = s["tandas"]
    t = filas[n]["Tanda"] - 1
    paginas = list(tandas[t].paginas)
    if t + 1 < len(tandas):
        paginas.append(tandas[t + 1].paginas[0])
    return paginas


def pantalla_revisar():
    s = sesion()
    if s is None:
        st.info("Todavía no hay ninguna transcripción. Empezá en ① Transcribir.")
        return
    if aviso := ss.pop(P + "aviso", None):
        st.error(aviso)
    tandas = s["tandas"]
    filas = filas_finales(s)
    res = tl.resumen(tl.unir_tandas(tandas), tandas)
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

    # ------------------------------------------------------------ tandas
    st.header("Tandas")
    for i, t in enumerate(tandas):
        c1, c2, c3 = st.columns([1.3, 4, 1.2], vertical_alignment="center")
        c1.markdown(f"{ICONO[t.estado]} **Tanda {i + 1}** · {t.nombre}")
        if t.estado == "ok":
            r = t.resultado
            extra = []
            if r["continuacion_del_anterior"]:
                extra.append("trae continuación de la anterior")
            if r["cortado_al_final"]:
                extra.append("termina cortada")
            c2.caption(f"{len(r['filas'])} filas" + (f" · {' · '.join(extra)}" if extra else "")
                       + (f" · {len(t.intentos)} intentos" if len(t.intentos) > 1 else ""))
        elif t.estado == "error":
            c2.error(t.error or "Error", icon="❌")
        else:
            c2.caption("Pendiente")
        if c3.button("🔁 Reintentar", key=f"{P}reint_{i}", width="stretch"):
            ss[P + "reintentar"] = i

    if (i := ss.get(P + "reintentar")) is not None and i < len(tandas):
        with st.container(border=True):
            if i + 1 < len(tandas):
                st.warning(
                    f"Vas a reintentar la **tanda {i + 1}**. Las tandas van en fila: la tanda {i + 2} "
                    f"usó el final de esta como contexto, así que si la {i + 1} cambia, la {i + 2} "
                    "(y las que siguen) pueden quedar desalineadas: filas repetidas o un párrafo "
                    "partido en dos.")
            if ss[P + "correcciones"]:
                st.warning("Las correcciones que hiciste a mano en la tabla se van a perder.")
            b1, b2, b3 = st.columns(3)
            if b1.button(f"Reintentar solo la tanda {i + 1}", type="primary", width="stretch"):
                reintentar(i, hasta_el_final=False)
                st.rerun()
            if i + 1 < len(tandas) and b2.button(f"Reintentar de la {i + 1} hasta el final",
                                                 width="stretch"):
                reintentar(i, hasta_el_final=True)
                st.rerun()
            if b3.button("Cancelar", width="stretch"):
                ss.pop(P + "reintentar")
                st.rerun()

    if not filas:
        st.info("No hay filas transcriptas todavía.")
        respuestas_crudas(tandas)
        return

    # --------------------------------------------- comparar fila con página
    st.header("Comparar con el libro")
    st.caption("Elegí una fila: a la izquierda su texto (se puede corregir) y a la derecha la página "
               "escaneada. Las correcciones se aplican al Excel.")
    v = ss[P + "version"]

    def etiqueta(n):
        f = filas[n]
        marca = " ⚠️" if f["Revisar"] else ""
        return f"Fila {n + 1} · {f['Folio']} · {f['Fecha']} {f['Hora']}{marca}"

    n = st.selectbox("Fila", range(len(filas)), format_func=etiqueta, key=P + "fila")
    n = min(n or 0, len(filas) - 1)
    fila = filas[n]
    izq, der = st.columns([1, 1], gap="medium")
    with izq:
        if fila["Revisar"]:
            st.warning(f"Revisar: {fila['Revisar']}")
        a, b, c = st.columns([2, 1.3, 1])
        for col, campo in ((a, "Folio"), (b, "Fecha"), (c, "Hora")):
            clave = f"{P}{campo}_{n}_{v}"
            col.text_input(campo, value=fila[campo], key=clave,
                           on_change=al_editar_texto, args=(n, campo, clave))
        clave = f"{P}texto_{n}_{v}"
        st.text_area("Transcripción", value=fila["Transcripción"], key=clave, height=560,
                     on_change=al_editar_texto, args=(n, "Transcripción", clave))
    with der:
        paginas = pagina_probable(s, filas, n)
        tanda = s["tandas"][fila["Tanda"] - 1]
        # Página donde probablemente está la fila: por su folio, respecto del primero de la tanda.
        folios = [tl.numero_folio(f["folio"]) for f in (tanda.resultado or {}).get("filas", [])]
        folios = [x for x in folios if x is not None]
        propio = tl.numero_folio(fila["Folio"])
        desplazamiento = (propio - min(folios)) if folios and propio is not None else 0
        sugerida = paginas[max(0, min(desplazamiento, len(tanda.paginas) - 1))]
        pagina = st.pills("Página del PDF", paginas, default=sugerida, format_func=lambda p: f"Pág. {p + 1}",
                          key=f"{P}pag_{n}_{v}")
        pagina = sugerida if pagina is None else pagina
        st.image(s["imagenes"][pagina], width="stretch")

    # ------------------------------------------------------------ tabla
    st.header("Tabla completa")
    st.caption("También se puede corregir acá con doble clic en la celda. «Tanda» y «Revisar» son "
               "solo para mirar: no van al Excel.")
    clave = f"{P}tabla_{v}"
    st.data_editor(
        pd.DataFrame(filas), key=clave, hide_index=True, width="stretch", num_rows="fixed",
        height=min(35 * len(filas) + 38, 500), on_change=al_editar_tabla, args=(clave,),
        disabled=["Tanda", "Revisar"],
        column_config={
            "Folio": st.column_config.TextColumn(width=130),
            "Fecha": st.column_config.TextColumn(width=95),
            "Hora": st.column_config.TextColumn(width=60),
            "Transcripción": st.column_config.TextColumn(width="large"),
            "Tanda": st.column_config.NumberColumn(width=55, format="%d"),
            "Revisar": st.column_config.TextColumn(width="medium"),
        },
    )

    # ------------------------------------------------------------ exportar
    st.header("Exportar")
    if res["tandas_error"] or res["tandas_pendientes"]:
        st.warning("Ojo: faltan tandas (" + ", ".join(res["tandas_error"] + res["tandas_pendientes"])
                   + "). El Excel sale sin esas páginas.")
    exportables = [{k: f[k] for k in tl.COLUMNAS} for f in filas]
    nombre = st.text_input("Nombre del archivo", value=tl.nombre_archivo(exportables), key=f"{P}nombre_{v}")
    nombre = re.sub(r'[\\/:*?"<>|]', "", nombre).strip().removesuffix(".xlsx") or "LG_transcripcion"
    st.download_button(f"⬇️ Descargar {nombre}.xlsx", tl.exportar_excel(exportables), f"{nombre}.xlsx",
                       type="primary", key=P + "descargar")
    st.caption(f"Una hoja con Folio, Fecha, Hora y Transcripción · {res['filas']} filas · "
               f"{res['dudosos']} [?] · {res['ilegibles']} [ilegible] · "
               f"tandas con error: {', '.join(res['tandas_error']) or 'ninguna'}.")

    respuestas_crudas(tandas)


def respuestas_crudas(tandas: list[tl.Tanda]) -> None:
    st.header("Respuestas crudas del modelo")
    st.caption("Lo que devolvió Claude en cada intento, tal cual, y el contexto que se le pasó.")
    for i, t in enumerate(tandas):
        with st.expander(f"{ICONO[t.estado]} Tanda {i + 1} · {t.nombre} · {len(t.intentos)} intento(s)"):
            for k, intento in enumerate(t.intentos, 1):
                costo = tl.costo(intento["uso"])
                tokens = sum(u["entrada"] + u["cache_escritura"] + u["cache_lectura"] for u in intento["uso"])
                salida = sum(u["salida"] for u in intento["uso"])
                modelos = ", ".join(sorted({u["modelo"] for u in intento["uso"]})) or "—"
                esfuerzos = {u.get("esfuerzo") for u in intento["uso"]} - {None}
                if esfuerzos:
                    modelos += " · esfuerzo " + ", ".join(sorted(esfuerzos))
                st.markdown(f"**Intento {k}** · {modelos} · {tokens:,} tokens de entrada · {salida:,} de "
                            f"salida · US\\$ {costo:.3f}".replace(",", "."))
                if intento["error"]:
                    st.error(intento["error"])
                ctx = intento["contexto"]
                st.caption(f"Contexto enviado: fecha «{ctx['ultima_fecha'] or '—'}»"
                           + (" · con el último párrafo de la tanda anterior" if ctx["ultimo_parrafo"] else ""))
                st.code(intento["cruda"] or "(vacía)", language="json", wrap_lines=True)
    crudas = [{"tanda": i + 1, "paginas": [p + 1 for p in t.paginas], "estado": t.estado,
               "intentos": t.intentos} for i, t in enumerate(tandas)]
    st.download_button("⬇️ Descargar respuestas crudas (.json)",
                       json.dumps(crudas, ensure_ascii=False, indent=2), "LG_respuestas_crudas.json",
                       mime="application/json", key=P + "crudas")


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


def al_cambiar_esfuerzo() -> None:
    ajustes = tl.leer_ajustes()
    ajustes["esfuerzo"] = ss[P + "esfuerzo"]
    tl.guardar_ajustes(ajustes)
    ss[P + "msg"] = ("success", f"Esfuerzo guardado: {tl.ESFUERZOS[ss[P + 'esfuerzo']]}.")


def al_cambiar_modelo() -> None:
    ajustes = tl.leer_ajustes()
    ajustes["modelo"] = ss[P + "modelo"]
    tl.guardar_ajustes(ajustes)
    ss[P + "msg"] = ("success", f"Modelo guardado: {ss[P + 'modelo']}.")


def pantalla_configuracion():
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
                 key=P + "modelo", on_change=al_cambiar_modelo)
    c2.selectbox("Esfuerzo", list(tl.ESFUERZOS), format_func=lambda e: tl.ESFUERZOS[e],
                 key=P + "esfuerzo", on_change=al_cambiar_esfuerzo)
    entrada, salida, _, _ = tl.PRECIOS[ss[P + "modelo"]]
    st.caption(f"Precio: US\\$ {entrada:g} por millón de tokens de entrada y US\\$ {salida:g} por millón de "
               f"salida. Las tandas son siempre de {tl.PAGINAS_POR_TANDA} páginas.")
    st.caption("**Esfuerzo**: cuánto analiza Claude cada página antes de responder. Con más esfuerzo lee "
               "la letra con más cuidado (menos [?] y menos errores en números), pero tarda más y cuesta "
               "más, porque ese análisis se cobra como texto de salida. Se guarda y queda para las "
               "próximas transcripciones.")

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
