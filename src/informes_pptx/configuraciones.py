"""Informes PowerPoint – configuraciones de informe.

Una configuración se arma sobre una plantilla y dice de dónde sale cada cosa del Excel:
- cada lugar de imagen: hoja + rango (A5:N41) o gráfico, como captura o como gráfico pegado, y cómo
  se acomoda en el recuadro;
- cada texto variable: texto libre (con valor por defecto) o una celda del Excel (Carátula!D32).

Se guarda en informes/configuraciones/<id>.json con el formato legible del ejemplo:
  "imagenes": {"img_02_01": {"hoja": "Confiabilidad", "rango": "A5:N41", "modo": "captura", ...}}
  "textos":   {"mes": {"fuente": "celda", "celda": "Carátula!D32"}}
En memoria (mientras se edita) cada imagen tiene además "toma", "desde" y "hasta", y cada texto
"hoja" y "celda" por separado: a_json() y de_json() pasan de un formato al otro.
"""
import copy
import datetime as dt
import io
import json
import secrets
from pathlib import Path

from PIL import Image, ImageDraw

from src.informes_pptx import excel_zip as ez
from src.informes_pptx import plantillas as pl

RAIZ = pl.RAIZ
VERSION = 1
RANGO, GRAFICO = "rango", "grafico"       # qué toma del Excel
CAPTURA = "captura"                       # modo: captura (imagen) o "grafico" (gráfico pegado, editable)
AJUSTES = {"encajar": "Encajar manteniendo proporción", "ancho": "Ajustar al ancho", "alto": "Ajustar al alto"}
LIBRE, CELDA = "libre", "celda"


class ErrorConfiguracion(ValueError):
    """La configuración tiene un problema (mensaje listo para mostrar)."""


def imagen_vacia() -> dict:
    return {"hoja": "", "toma": RANGO, "desde": "", "hasta": "", "grafico": "", "modo": CAPTURA,
            "ajuste": "encajar", "estilo": {}}


def texto_vacio() -> dict:
    return {"fuente": LIBRE, "por_defecto": "", "hoja": "", "celda": ""}


# ------------------------------------------------------- formato del archivo
def imagen_a_json(img: dict) -> dict:
    out = {"hoja": img["hoja"]}
    if img["toma"] == GRAFICO:
        out["grafico"] = img["grafico"]
    else:
        out["rango"] = ez.armar_rango(img["desde"], img["hasta"]) or f"{img['desde']}:{img['hasta']}".strip(":")
    out.update(modo=img["modo"], ajuste=img["ajuste"], estilo=img.get("estilo") or {})
    return out


def imagen_de_json(datos: dict) -> dict:
    img = {**imagen_vacia(), **{k: datos[k] for k in ("hoja", "modo", "ajuste", "estilo") if k in datos}}
    if "grafico" in datos:
        img.update(toma=GRAFICO, grafico=datos["grafico"])
    elif datos.get("rango"):
        desde, _, hasta = datos["rango"].partition(":")
        img.update(toma=RANGO, desde=desde, hasta=hasta or desde)
    return img


def texto_a_json(t: dict) -> dict:
    if t["fuente"] == CELDA:
        celda = ez.normalizar_celda(t["celda"]) or t["celda"].strip()  # «d32» se guarda como D32
        return {"fuente": CELDA, "celda": ez.ref_celda(t["hoja"], celda) if t["hoja"] else celda}
    return {"fuente": LIBRE, "por_defecto": t["por_defecto"]}


def texto_de_json(datos: dict) -> dict:
    t = texto_vacio()
    if datos.get("fuente") == CELDA:
        hoja, celda = ez.partir_ref(datos.get("celda", ""))
        t.update(fuente=CELDA, hoja=hoja, celda=celda)
    else:
        t["por_defecto"] = datos.get("por_defecto", "")
    return t


def a_json(config: dict) -> dict:
    return {**{k: v for k, v in config.items() if k not in ("imagenes", "textos")},
            "imagenes": {k: imagen_a_json(v) for k, v in config["imagenes"].items()},
            "textos": {k: texto_a_json(v) for k, v in config["textos"].items()}}


def de_json(datos: dict) -> dict:
    return {**datos, "imagenes": {k: imagen_de_json(v) for k, v in datos.get("imagenes", {}).items()},
            "textos": {k: texto_de_json(v) for k, v in datos.get("textos", {}).items()}}


# ------------------------------------------------------- contra la plantilla
def lugares(plantilla: dict) -> list[tuple[dict, dict]]:
    """(diapositiva, lugar de imagen) de toda la plantilla, en orden."""
    return [(d, img) for d in plantilla["diapositivas"] for img in d["imagenes"]]


def completar(config: dict, plantilla: dict) -> tuple[dict, list[str]]:
    """Agrega lo que falta (lugares o variables nuevos de la plantilla) y saca lo que ya no está.

    Devuelve (configuración, avisos de lo que se sacó).
    """
    config = copy.deepcopy(config)
    avisos = []
    ids_img = [img["id"] for _, img in lugares(plantilla)]
    ids_var = list(pl.variables(plantilla))
    for clave, ids, vacio, que in [("imagenes", ids_img, imagen_vacia, "lugar de imagen"),
                                   ("textos", ids_var, texto_vacio, "texto variable")]:
        actual = config.get(clave, {})
        for sobrante in [k for k in actual if k not in ids]:
            avisos.append(f"El {que} «{sobrante}» ya no está en la plantilla: se saca de la configuración.")
        config[clave] = {k: actual.get(k) or vacio() for k in ids}
    return config, avisos


def esta_completa_imagen(img: dict) -> bool:
    return bool(img["hoja"] and (img["grafico"] if img["toma"] == GRAFICO else img["desde"] and img["hasta"]))


def esta_completo_texto(t: dict) -> bool:
    return t["fuente"] == LIBRE or bool(t["hoja"] and t["celda"])


def errores_imagen(img: dict) -> list[str]:
    """Problemas de escritura de un lugar de imagen (no hace falta el Excel para verlos)."""
    errores = []
    if img["toma"] == RANGO:
        for campo, nombre in (("desde", "Desde"), ("hasta", "Hasta")):
            if img[campo] and not ez.normalizar_celda(img[campo]):
                errores.append(f"«{img[campo]}» no es una celda válida ({nombre}). Ejemplo: A5.")
        if img["modo"] != CAPTURA:
            errores.append("El gráfico pegado solo se puede elegir si se toma un gráfico, no un rango.")
    if img["ajuste"] not in AJUSTES:
        errores.append(f"Ajuste desconocido: {img['ajuste']}.")
    return errores


def errores_texto(t: dict) -> list[str]:
    if t["fuente"] == CELDA and t["celda"] and not ez.normalizar_celda(t["celda"]):
        return [f"«{t['celda']}» no es una celda válida. Ejemplo: D32."]
    return []


def validar(config: dict, plantilla: dict) -> tuple[list[str], list[str]]:
    """(errores que impiden guardar, cosas sin completar). Las sin completar no impiden guardar."""
    errores, pendientes = [], []
    if not config.get("nombre", "").strip():
        errores.append("La configuración no tiene nombre.")
    nombres_img = {img["id"]: img["nombre"] for _, img in lugares(plantilla)}
    for iid, img in config["imagenes"].items():
        errores += [f"{nombres_img.get(iid, iid)}: {e}" for e in errores_imagen(img)]
        if not esta_completa_imagen(img):
            pendientes.append(nombres_img.get(iid, iid))
    variables = pl.variables(plantilla)
    for vid, t in config["textos"].items():
        nombre = variables.get(vid, {}).get("nombre", vid)
        errores += [f"{nombre}: {e}" for e in errores_texto(t)]
        if not esta_completo_texto(t):
            pendientes.append(nombre)
    return errores, pendientes


# ----------------------------------------------------------- contra el Excel
def avisos_excel(config: dict, info: ez.InfoExcel) -> dict:
    """{id de imagen o variable: [avisos]} de lo que no existe en el Excel subido."""
    out = {}

    def hoja_ok(clave, hoja) -> ez.Hoja | None:
        h = info.hoja(hoja)
        if h is None:
            out.setdefault(clave, []).append(f"La hoja «{hoja}» no existe en este Excel (¿la renombraron?).")
        elif not h.visible:
            out.setdefault(clave, []).append(f"La hoja «{hoja}» está oculta en este Excel.")
        elif h.es_de_grafico:
            out.setdefault(clave, []).append(f"«{hoja}» es una hoja de gráfico: no tiene celdas.")
        else:
            return h
        return None

    for iid, img in config["imagenes"].items():
        if not img["hoja"]:
            continue
        h = hoja_ok(iid, img["hoja"])
        if h and img["toma"] == GRAFICO and img["grafico"] and img["grafico"] not in [g.nombre for g in h.graficos]:
            out.setdefault(iid, []).append(f"No hay un gráfico «{img['grafico']}» en la hoja «{img['hoja']}».")
    for vid, t in config["textos"].items():
        if t["fuente"] == CELDA and t["hoja"]:
            hoja_ok(vid, t["hoja"])
    return out


# ------------------------------------------------------------- acomodar
def encajar(ancho_img: float, alto_img: float, caja: dict, ajuste: str) -> dict:
    """Posición y tamaño de la imagen dentro del recuadro, centrada.

    encajar: entra entera sin deformarse; ancho / alto: ocupa todo el ancho (o alto) del recuadro,
    manteniendo la proporción (puede sobresalir por el otro lado).
    """
    ex, ey = caja["ancho"] / ancho_img, caja["alto"] / alto_img
    escala = {"ancho": ex, "alto": ey}.get(ajuste, min(ex, ey))
    ancho, alto = ancho_img * escala, alto_img * escala
    return {"x": round(caja["x"] + (caja["ancho"] - ancho) / 2), "y": round(caja["y"] + (caja["alto"] - alto) / 2),
            "ancho": round(ancho), "alto": round(alto)}


def vista_en_recuadro(png: bytes, caja: dict, ajuste: str, ancho_px: int = 900) -> bytes:
    """Dibujo de cómo queda la imagen en su recuadro (recuadro en rojo punteado)."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    pos = encajar(img.width, img.height, caja, ajuste)
    margen_x, margen_y = caja["ancho"] * 0.08, caja["alto"] * 0.08
    x0 = min(caja["x"], pos["x"]) - margen_x
    y0 = min(caja["y"], pos["y"]) - margen_y
    x1 = max(caja["x"] + caja["ancho"], pos["x"] + pos["ancho"]) + margen_x
    y1 = max(caja["y"] + caja["alto"], pos["y"] + pos["alto"]) + margen_y
    k = ancho_px / (x1 - x0)
    lienzo = Image.new("RGB", (ancho_px, max(round((y1 - y0) * k), 1)), "#ECEAE8")

    def px(x, y):
        return round((x - x0) * k), round((y - y0) * k)

    d = ImageDraw.Draw(lienzo)
    d.rectangle([*px(caja["x"], caja["y"]), *px(caja["x"] + caja["ancho"], caja["y"] + caja["alto"])], fill="#FFFFFF")
    chica = img.resize((max(round(pos["ancho"] * k), 1), max(round(pos["alto"] * k), 1)), Image.LANCZOS)
    lienzo.paste(chica, px(pos["x"], pos["y"]))
    (ax, ay), (bx, by) = px(caja["x"], caja["y"]), px(caja["x"] + caja["ancho"], caja["y"] + caja["alto"])
    for x in range(ax, bx, 16):  # borde punteado del recuadro
        d.line([(x, ay), (min(x + 8, bx), ay)], fill="#D41920", width=3)
        d.line([(x, by), (min(x + 8, bx), by)], fill="#D41920", width=3)
    for y in range(ay, by, 16):
        d.line([(ax, y), (ax, min(y + 8, by))], fill="#D41920", width=3)
        d.line([(bx, y), (bx, min(y + 8, by))], fill="#D41920", width=3)
    salida = io.BytesIO()
    lienzo.save(salida, "PNG")
    return salida.getvalue()


# -------------------------------------------------------------------- en disco
def _carpeta(raiz: Path) -> Path:
    return raiz / "configuraciones"


def _ruta(cid: str, raiz: Path) -> Path:
    return _carpeta(raiz) / f"{cid}.json"


def ahora() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def _nuevo_id(nombre: str, raiz: Path) -> str:
    while True:
        cid = f"{pl.slug(nombre)[:40] or 'configuracion'}_{secrets.token_hex(3)}"
        if not _ruta(cid, raiz).exists():
            return cid


def _escribir(config: dict, raiz: Path):
    _carpeta(raiz).mkdir(parents=True, exist_ok=True)
    _ruta(config["id"], raiz).write_text(json.dumps(a_json(config), ensure_ascii=False, indent=2), encoding="utf-8")


def crear(nombre: str, plantilla: dict, raiz: Path = RAIZ) -> dict:
    config = {"version": VERSION, "id": _nuevo_id(nombre, raiz), "nombre": nombre.strip(),
              "plantilla": plantilla["id"], "excel_referencia": "", "creada": ahora(), "modificada": ahora(),
              "imagenes": {}, "textos": {}}
    config, _ = completar(config, plantilla)
    if not config["nombre"]:
        raise ErrorConfiguracion("La configuración no tiene nombre.")
    _escribir(config, raiz)
    return config


def guardar(config: dict, plantilla: dict, raiz: Path = RAIZ) -> dict:
    errores, _ = validar(config, plantilla)
    if errores:
        raise ErrorConfiguracion("\n".join(errores))
    config = {**config, "nombre": config["nombre"].strip(), "modificada": ahora()}
    _escribir(config, raiz)
    return config


def cargar(cid: str, raiz: Path = RAIZ) -> dict:
    return de_json(json.loads(_ruta(cid, raiz).read_text(encoding="utf-8")))


def listar(raiz: Path = RAIZ) -> tuple[list[dict], list[str]]:
    """(configuraciones, de la más nueva a la más vieja; archivos que no se pudieron leer)."""
    configs, rotas = [], []
    for ruta in sorted(_carpeta(raiz).glob("*.json")) if _carpeta(raiz).exists() else []:
        try:
            configs.append(cargar(ruta.stem, raiz))
        except (OSError, ValueError, KeyError, AttributeError):
            rotas.append(ruta.name)
    configs.sort(key=lambda c: c.get("modificada", ""), reverse=True)
    return configs, rotas


def de_plantilla(pid: str, raiz: Path = RAIZ) -> list[dict]:
    return [c for c in listar(raiz)[0] if c["plantilla"] == pid]


def duplicar(cid: str, raiz: Path = RAIZ) -> dict:
    original = cargar(cid, raiz)
    copia = {**original, "id": _nuevo_id(original["nombre"], raiz), "nombre": f"{original['nombre']} (copia)",
             "creada": ahora(), "modificada": ahora()}
    _escribir(copia, raiz)
    return copia


def eliminar(cid: str, raiz: Path = RAIZ):
    _ruta(cid, raiz).unlink()
