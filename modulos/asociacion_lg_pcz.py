"""Módulo: asociación manual de filas del Libro de Guardia (LG) con novedades del PCZ."""
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src import asociacion_lg_pcz as a

st.title("Asociación LG ↔ PCZ")

ss = st.session_state
P = "lgpcz_"  # prefijo de las claves de este módulo en session_state
CARPETA_SESIONES = Path(__file__).resolve().parent.parent / "datos" / "sesiones"
PASOS = ["1. Carga", "2. Asociación", "3. Exportar"]


@st.cache_data(show_spinner="Leyendo archivo...")
def leer(nombre: str, contenido: bytes) -> pd.DataFrame:
    return a.leer_tabla(nombre, contenido)


@st.cache_data(show_spinner=False)
def preparar(nombre_lg, bytes_lg, nombre_pcz, bytes_pcz, mapa_lg, mapa_pcz):
    lg = a.preparar_lg(leer(nombre_lg, bytes_lg), mapa_lg)
    pcz = a.preparar_pcz(leer(nombre_pcz, bytes_pcz), mapa_pcz)
    return lg, pcz


def guardar():
    try:
        a.guardar_sesion(ss[P + "sesion"], CARPETA_SESIONES)
    except OSError as e:
        ss[P + "msg"] = ("error", f"No se pudo guardar el progreso: {e}")


def ir_a_paso(paso: str):
    ss[P + "paso"] = paso


paso = st.radio("Paso", PASOS, horizontal=True, key=P + "paso", label_visibility="collapsed")

if msg := ss.pop(P + "msg", None):
    getattr(st, msg[0])(msg[1])

# ===================================================================== 1. Carga
if paso == PASOS[0]:
    st.caption(
        "Subí los dos Excel. Los originales **no se modifican**: la app trabaja sobre una copia y "
        "el resultado se descarga en un Excel nuevo."
    )
    c1, c2 = st.columns(2)
    for col, clave, titulo, columnas in [
        (c1, "lg", "Libro de Guardia (LG)", "Página · Fecha · Hora · Transcripción"),
        (c2, "pcz", "Novedades PCZ", "Descripción · Fecha · N° Novedad"),
    ]:
        with col, st.container(border=True):
            st.markdown(f"**{titulo}**")
            st.caption(f"Columnas necesarias: {columnas}")
            subido = st.file_uploader(titulo, type=["xlsx", "xls", "csv"], key=P + "up_" + clave,
                                      label_visibility="collapsed")
            if subido is not None:
                ss[P + clave] = {"nombre": subido.name, "bytes": subido.getvalue()}
            elif P + clave in ss:
                st.success(f"Cargado: {ss[P + clave]['nombre']}")

if P + "lg" not in ss or P + "pcz" not in ss:
    if paso == PASOS[0]:
        st.info("Subí los dos archivos para empezar.")
    else:
        st.info("Primero cargá los dos Excel en el paso **1. Carga**.")
    st.stop()

# --------------------------------------------------- validación de columnas
archivos = {"lg": ss[P + "lg"], "pcz": ss[P + "pcz"]}
mapas, hay_error = {}, False
for clave, esperadas, titulo in [("lg", a.COLUMNAS_LG, "LG"), ("pcz", a.COLUMNAS_PCZ, "PCZ")]:
    try:
        df = leer(archivos[clave]["nombre"], archivos[clave]["bytes"])
    except Exception as e:  # archivo dañado o con formato raro
        st.error(f"No se pudo leer el archivo de {titulo} ({archivos[clave]['nombre']}): {e}")
        hay_error = True
        continue
    mapas[clave], faltan = a.mapear_columnas(df, esperadas)
    if faltan:
        hay_error = True
        st.error(
            f"Al archivo de **{titulo}** ({archivos[clave]['nombre']}) le falta: "
            + ", ".join(f"**{f}**" for f in faltan)
            + ".  \nColumnas que tiene: " + ", ".join(f"`{c}`" for c in df.columns)
        )
if hay_error:
    st.stop()

lg_original = leer(archivos["lg"]["nombre"], archivos["lg"]["bytes"])
pcz_original = leer(archivos["pcz"]["nombre"], archivos["pcz"]["bytes"])
lg, pcz = preparar(archivos["lg"]["nombre"], archivos["lg"]["bytes"],
                   archivos["pcz"]["nombre"], archivos["pcz"]["bytes"], mapas["lg"], mapas["pcz"])
if lg.empty:
    st.error("El archivo de LG no tiene filas.")
    st.stop()

# ------------------------------------------------ sesión (autoguardado)
huella = a.huella(archivos["lg"]["bytes"], archivos["pcz"]["bytes"])
if ss.get(P + "sesion", {}).get("huella") != huella:
    previa = a.cargar_sesion(CARPETA_SESIONES, huella)
    if previa and len(previa["filas"]) == len(lg):
        ss[P + "sesion"] = previa
        p = a.progreso(previa)
        ss[P + "msg"] = ("info", f"Se retomó la sesión guardada de estos archivos: "
                                 f"{p['total'] - p['pendientes']} de {p['total']} filas resueltas.")
    else:
        ss[P + "sesion"] = a.sesion_nueva(huella, archivos["lg"]["nombre"], archivos["pcz"]["nombre"], len(lg))
    ss[P + "ver"] = ss.get(P + "ver", 0) + 1
    st.rerun()
sesion = ss[P + "sesion"]
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

    st.header("Sesión")
    p = a.progreso(sesion)
    st.caption(
        "El progreso se guarda solo en cada paso (carpeta `datos/sesiones`). Si cerrás la app y "
        "volvés a subir los mismos dos archivos, retomás donde quedaste."
    )
    st.markdown(f"Resueltas **{p['total'] - p['pendientes']}** de **{p['total']}** filas.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("💾 Exportar sesión (.json)", a.sesion_a_json(sesion),
                       f"sesion_lg_pcz_{huella}.json", mime="application/json")
    importada = c2.file_uploader("📂 Importar sesión (.json)", type=["json"], key=P + "up_sesion")
    if importada is not None and ss.get(P + "importada") != importada.file_id:
        try:
            nueva, avisos_ = a.importar_sesion(importada.getvalue().decode("utf-8"), len(lg), huella)
        except (ValueError, UnicodeDecodeError) as e:
            st.error(str(e))
        else:
            ss[P + "importada"] = importada.file_id
            ss[P + "sesion"] = nueva
            ss[P + "ver"] += 1
            guardar()
            ss[P + "msg"] = ("warning" if avisos_ else "success",
                             " ".join(avisos_) or "Sesión importada.")
            st.rerun()
    with c3:
        seguro = st.checkbox("Quiero borrar todo lo asociado")
        if st.button("🗑️ Empezar de cero", disabled=not seguro):
            ss[P + "sesion"] = a.sesion_nueva(huella, archivos["lg"]["nombre"], archivos["pcz"]["nombre"], len(lg))
            ss[P + "ver"] += 1
            guardar()
            st.rerun()

    st.button("Ir a asociar ➡️", type="primary", on_click=ir_a_paso, args=(PASOS[1],))
    st.stop()

# ================================================================== 3. Exportar
if paso == PASOS[2]:
    p = a.progreso(sesion)
    st.header("Exportar a Excel")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Filas de LG", p["total"])
    m2.metric("Asociadas", p["asociadas"])
    m3.metric("Ninguna corresponde", p["ninguna"])
    m4.metric("Pendientes", p["pendientes"])
    if p["pendientes"]:
        st.warning(f"Quedan {p['pendientes']} fila(s) pendientes: se exportan con estado «Pendiente».")
    multiples = {k: v for k, v in a.asociaciones_por_novedad(sesion).items() if len(v) > 1}
    if multiples:
        st.info("Novedades asociadas a más de una fila de LG (su «Texto LG» junta todos con « / »): "
                + "; ".join(f"{k} → filas {', '.join(str(f + 1) for f in v)}" for k, v in multiples.items()))
    st.caption(
        "El Excel trae 3 hojas: **LG_asociado** (LG + novedades asociadas + estado), "
        "**PCZ_completado** (PCZ + «Texto LG» + «Descripción combinada» para pegar en la tabla de "
        "eventos RAMS) y **Resumen**."
    )
    nombre = st.text_input("Nombre del archivo a descargar", value="asociacion_LG_PCZ")
    # Sacar caracteres que Windows no acepta en nombres de archivo
    nombre = re.sub(r'[\\/:*?"<>|]', "", nombre).strip().removesuffix(".xlsx") or "asociacion_LG_PCZ"
    st.download_button(f"⬇️ Descargar {nombre}.xlsx", a.exportar(lg_original, pcz_original, lg, pcz, sesion),
                       f"{nombre}.xlsx", type="primary")
    st.stop()

# ================================================================ 2. Asociación
n = len(lg)
asociadas_a = a.asociaciones_por_novedad(sesion)
desc_por_id = dict(zip(pcz["id"], pcz["descripcion"]))


def borrador() -> dict:
    """Elección en curso de la fila actual (se descarta al cambiar de fila sin confirmar)."""
    pos, ver = sesion["posicion"], ss[P + "ver"]
    b = ss.get(P + "borrador")
    if not b or b["fila"] != pos or b["ver"] != ver:
        guardada = sesion["filas"][str(pos)]
        b = {"fila": pos, "ver": ver,
             "novedades": list(guardada["novedades"]) if guardada["estado"] == "asociada" else [],
             "avisos": {k: list(v) for k, v in guardada.get("avisos", {}).items()}}
        ss[P + "borrador"] = b
    return b


def mover(destino: int):
    sesion["posicion"] = max(0, min(n - 1, destino))
    ss[P + "ver"] += 1
    guardar()


def tildar(nov: str, clave: str):
    b = borrador()
    if ss[clave] and nov not in b["novedades"]:
        b["novedades"].append(nov)
    elif not ss[clave] and nov in b["novedades"]:
        b["novedades"].remove(nov)


def elegir_avisos(nov: str, clave: str):
    borrador()["avisos"][nov] = [int(x.split(".")[0]) - 1 for x in ss[clave]]


def accion(tipo: str):
    pos, b = sesion["posicion"], borrador()
    if tipo == "confirmar":
        if not b["novedades"]:
            ss[P + "msg"] = ("error", "No elegiste ninguna novedad. Tildá al menos una o usá "
                                      "«Ninguna corresponde».")
            return
        a.registrar(sesion, pos, "asociada", b["novedades"], b["avisos"])
    elif tipo == "ninguna":
        a.registrar(sesion, pos, "ninguna")
    elif tipo == "saltar":
        a.registrar(sesion, pos, "pendiente")
    elif tipo == "deshacer":
        if a.deshacer(sesion) is None:
            ss[P + "msg"] = ("info", "No hay nada para deshacer.")
            return
        ss[P + "ver"] += 1
        guardar()
        return
    if pos == n - 1:
        ss[P + "msg"] = ("success", "Llegaste a la última fila. Revisá las pendientes o pasá a "
                                    "**3. Exportar**.")
    mover(pos + 1)


def ir_a_fila():
    mover(ss[f"{P}ir_a_{ss[P + 'ver']}"] - 1)


def proxima_pendiente():
    sig = a.siguiente_pendiente(sesion, sesion["posicion"])
    if sig is None:
        ss[P + "msg"] = ("success", "¡No quedan filas pendientes!")
    else:
        mover(sig)


pos = sesion["posicion"]
fila = lg.loc[pos]
guardada = sesion["filas"][str(pos)]
b = borrador()
ver = ss[P + "ver"]

# ------------------------------------------------------------------ progreso
p = a.progreso(sesion)
st.progress((p["total"] - p["pendientes"]) / p["total"])
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Fila", f"{pos + 1} de {n}")
m2.metric("Asociadas", p["asociadas"])
m3.metric("Ninguna corresponde", p["ninguna"])
m4.metric("Pendientes", p["pendientes"])
with m5:
    st.number_input("Ir a fila", 1, n, pos + 1, key=f"{P}ir_a_{ver}", on_change=ir_a_fila)
    st.button("Próxima pendiente", on_click=proxima_pendiente, use_container_width=True)

# --------------------------------------------------------------- fila de LG
ESTADO_ICONO = {"asociada": "✅ Asociada", "ninguna": "🚫 Ninguna corresponde", "pendiente": "⏳ Pendiente"}
with st.container(border=True):
    hora = a.formatear_hora(fila["hora"]) if pd.notna(fila["hora"]) else (
        "" if pd.isna(fila["hora_original"]) else str(fila["hora_original"]))
    st.markdown(
        f"#### LG fila {pos + 1} &nbsp;·&nbsp; Página {fila['pagina'] or '—'} &nbsp;·&nbsp; "
        f"{a.formatear_fecha(fila['fecha'])} &nbsp;·&nbsp; {hora or 'sin hora'}"
    )
    estado_txt = ESTADO_ICONO[guardada["estado"]]
    if guardada["estado"] == "asociada":
        estado_txt += ": " + ", ".join(guardada["novedades"])
    st.caption(f"Estado guardado: {estado_txt}")
    if fila["fecha"] is None:
        st.error(
            f"La fecha de esta fila no se pudo interpretar (viene como «{fila['fecha_original']}»). "
            "No se pueden proponer candidatos por fecha: usá el buscador para buscar en todas las novedades."
        )
    if fila["avisos"]:
        st.markdown(
            "<ol style='font-size:1.05rem;line-height:1.6'>"
            + "".join(f"<li>{a.resaltar(x, set())}</li>" for x in fila["avisos"])
            + "</ol>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Esta fila no tiene transcripción.")

# ----------------------------------------------------- elección y botones
with st.container(border=True):
    if b["novedades"]:
        st.markdown("**Tu elección:** " + ", ".join(f"N° {x}" for x in b["novedades"]))
        for nov in b["novedades"]:
            otras = [f + 1 for f in asociadas_a.get(nov, []) if f != pos]
            if otras:
                st.warning(f"La novedad {nov} ya está asociada a LG fila {', '.join(map(str, otras))}.")
        if len(fila["avisos"]) > 1:
            st.caption("Opcional: indicá a qué aviso corresponde cada novedad (si no, se usa el párrafo entero).")
            opciones = [f"{i + 1}. {x[:70]}" for i, x in enumerate(fila["avisos"])]
            cols = st.columns(min(len(b["novedades"]), 3))
            for k, nov in enumerate(b["novedades"]):
                clave = f"{P}av_{ver}_{pos}_{nov}"
                cols[k % len(cols)].multiselect(
                    f"Aviso(s) de N° {nov}", opciones,
                    default=[opciones[i] for i in b["avisos"].get(nov, []) if i < len(opciones)],
                    key=clave, on_change=elegir_avisos, args=(nov, clave), placeholder="Párrafo entero",
                )
    else:
        st.markdown("**Tu elección:** ninguna novedad tildada todavía.")

    c = st.columns([1, 1.6, 1.6, 1, 1, 1])
    c[0].button("⬅️ Anterior", on_click=mover, args=(pos - 1,), disabled=pos == 0, use_container_width=True)
    c[1].button("✅ Confirmar y siguiente", type="primary", on_click=accion, args=("confirmar",),
                use_container_width=True)
    c[2].button("🚫 Ninguna corresponde", on_click=accion, args=("ninguna",), use_container_width=True)
    c[3].button("⏭️ Saltar", on_click=accion, args=("saltar",), use_container_width=True,
                help="Deja la fila pendiente y pasa a la siguiente.")
    c[4].button("↩️ Deshacer", on_click=accion, args=("deshacer",), use_container_width=True,
                disabled=not sesion["historial"])
    c[5].button("➡️ Siguiente", on_click=mover, args=(pos + 1,), disabled=pos == n - 1,
                use_container_width=True)
    st.caption("Atajos: **1–9** tildar candidato · **Enter** confirmar y siguiente · **← →** anterior/siguiente "
               "· **N** ninguna corresponde · **S** saltar. (No funcionan mientras escribís en el buscador.)")

# -------------------------------------------------------------- candidatos
st.subheader("Novedades de PCZ candidatas")
f1, f2 = st.columns([3, 2])
busqueda = f1.text_input("🔎 Buscar en las novedades", key=f"{P}buscar_{pos}",
                         placeholder="Ej.: Boulogne 14  (filtra por N° o descripción)")
vecinos = f2.toggle("Ver también día anterior / siguiente", key=P + "vecinos",
                    help="Para eventos que cruzan la medianoche. Se muestran marcados como OTRO DÍA.")

if fila["fecha"] is None:
    # Sin fecha en LG: se busca en todas las novedades, solo si el usuario escribe algo
    cands = a.todas_las_novedades(fila, pcz[pcz["fecha"].notna()])
else:
    cands = a.candidatos(fila, pcz, vecinos)
del_dia = int((~cands["otro_dia"]).sum())
cands = a.buscar(cands, busqueda)
sin_fecha = a.buscar(a.pcz_sin_fecha(fila, pcz), busqueda)

if fila["fecha"] is not None:
    st.caption(f"{del_dia} novedad(es) del {a.formatear_fecha(fila['fecha'])}"
               + (f" · {len(cands)} coinciden con la búsqueda" if busqueda else "")
               + ". Puntaje: número compartido 3 (1 si es de una cifra) · palabra compartida 1 · "
                 "hora cercana hasta 3. Se resaltan las coincidencias.")


def mostrar(c: pd.DataFrame, inicio: int, etiqueta: str | None):
    for k, (_, cand) in enumerate(c.iterrows(), start=inicio):
        nov = cand["id"]
        elegida = nov in b["novedades"]
        otras = [f + 1 for f in asociadas_a.get(nov, []) if f != pos]
        with st.container(border=True):
            c1, c2 = st.columns([1, 5])
            clave = f"{P}sel_{ver}_{pos}_{cand['fila_pcz']}"
            c1.checkbox(f"\\[{k}\\] N° {nov}", value=elegida, key=clave, on_change=tildar, args=(nov, clave))
            c1.caption(f"Puntaje **{cand['puntaje']}**")
            marcas = []
            if etiqueta:
                marcas.append(f"<span style='background:#f59e0b;color:#000;padding:1px 6px;border-radius:4px;"
                              f"font-weight:600'>{etiqueta} · {a.formatear_fecha(cand['fecha'])}</span>")
            if otras:
                marcas.append(f"<span style='background:#3b82f6;color:#fff;padding:1px 6px;border-radius:4px'>"
                              f"🔗 ya asociada a LG fila {', '.join(map(str, otras))}</span>")
            if pos in asociadas_a.get(nov, []):
                marcas.append("<span style='background:#16a34a;color:#fff;padding:1px 6px;border-radius:4px'>"
                              "guardada en esta fila</span>")
            c2.markdown(
                (" ".join(marcas) + "<br>" if marcas else "")
                + a.resaltar(cand["descripcion"], cand["comunes"], cand["hora_suma"])
                + f"<br><span style='opacity:0.6;font-size:0.85rem'>{cand['detalle']}</span>",
                unsafe_allow_html=True,
            )
            if elegida and otras:
                c2.warning(f"Ya asociada a LG fila {', '.join(map(str, otras))}.")


mismo = cands[~cands["otro_dia"]]
otro = cands[cands["otro_dia"]]
if fila["fecha"] is None:
    if not busqueda:
        st.info("Escribí en el buscador para buscar entre todas las novedades de PCZ.")
    else:
        mostrar(cands, 1, "SIN FECHA EN LG")
else:
    if mismo.empty:
        st.info("No hay novedades de PCZ " + ("que coincidan con la búsqueda " if busqueda else "")
                + f"con fecha {a.formatear_fecha(fila['fecha'])}.")
    mostrar(mismo, 1, None)
    if vecinos:
        st.markdown("##### 🌙 OTRO DÍA (día anterior / siguiente)")
        if otro.empty:
            st.caption("No hay novedades del día anterior ni del siguiente.")
        mostrar(otro, len(mismo) + 1, "OTRO DÍA")
if len(sin_fecha):
    with st.expander(f"Novedades de PCZ sin fecha reconocible ({len(sin_fecha)})"):
        mostrar(sin_fecha, len(cands) + 1, "SIN FECHA")

with st.expander("Lista de todas las filas de LG"):
    st.dataframe(pd.DataFrame({
        "Fila": range(1, n + 1),
        "Fecha": lg["fecha"].map(a.formatear_fecha),
        "Estado": [a.ESTADOS[sesion["filas"][str(i)]["estado"]] for i in range(n)],
        "Novedades": [";".join(sesion["filas"][str(i)]["novedades"]) for i in range(n)],
        "Transcripción": lg["texto"].str.slice(0, 120),
    }), hide_index=True, use_container_width=True)

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
  if (!Array.from(doc.querySelectorAll('button')).some(b => b.innerText.trim().endsWith('Confirmar y siguiente'))) return;
  if (/^[1-9]$/.test(e.key)) {
    const marca = '[' + e.key + ']';
    const label = Array.from(doc.querySelectorAll('[data-testid="stCheckbox"] label'))
      .find(l => l.innerText.trim().startsWith(marca));
    const casilla = label && label.querySelector('input');
    if (casilla) { e.preventDefault(); casilla.click(); }
    return;
  }
  const mapa = {'Enter': 'Confirmar y siguiente', 'ArrowLeft': 'Anterior', 'ArrowRight': 'Siguiente',
                'n': 'Ninguna corresponde', 'N': 'Ninguna corresponde', 's': 'Saltar', 'S': 'Saltar'};
  if (mapa[e.key]) {
    e.preventDefault();
    const b = boton(mapa[e.key]);
    if (b) b.click();
  }
};
doc.addEventListener('keydown', window.parent.__lgpczTeclas);
</script>
""", height=0)
