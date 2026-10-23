"""Dibujo de una diapositiva de la plantilla (SVG) con los recuadros a escala.

Si hay miniatura (imagen de la diapositiva hecha con PowerPoint) va de fondo y los recuadros se
dibujan encima; si no, se ve el esquema solo. Colores de señal: texto fijo gris, texto variable
amarillo, lugar de imagen rojo Ferrovías.
"""
import base64
from html import escape

ANCHO = 1000  # ancho del dibujo en px (el alto sale de la proporción de la diapositiva)
ESTILOS = {
    "fijo": ("#8C8682", "rgba(140,134,130,.10)"),
    "variable": ("#C98A00", "rgba(255,226,122,.55)"),
    "imagen": ("#D41920", "rgba(212,25,32,.12)"),
}


def _corto(texto: str, largo: int) -> str:
    t = " ".join(texto.split())
    return t if len(t) <= largo else t[:largo - 1] + "…"


def svg(diapositiva: dict, tamano: dict, fondo_png: bytes | None = None, resaltado: str | None = None) -> str:
    """SVG de la diapositiva. `resaltado`: id de un texto o imagen para marcarlo más fuerte."""
    k = ANCHO / tamano["ancho"]
    alto = round(tamano["alto"] * k)
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}" '
              f'style="width:100%;height:auto;display:block;font-family:Overpass,sans-serif">',
              f'<rect width="{ANCHO}" height="{alto}" fill="#FFFFFF" stroke="#D3CFCC"/>']
    if fondo_png:
        datos = base64.b64encode(fondo_png).decode()
        partes.append(f'<image href="data:image/png;base64,{datos}" width="{ANCHO}" height="{alto}"/>')

    recuadros = [(f"T{i}", t["id"], t["tipo"], t["caja"], t["contenido"])
                 for i, t in enumerate(diapositiva["textos"], 1)]
    recuadros += [(f"I{i}", img["id"], "imagen", img["caja"], img["nombre"])
                  for i, img in enumerate(diapositiva["imagenes"], 1)]
    # Los más grandes primero, así los chicos quedan arriba y se pueden ver
    recuadros.sort(key=lambda r: -(r[3]["ancho"] * r[3]["alto"]))
    for etiqueta, rid, tipo, caja, texto in recuadros:
        borde, relleno = ESTILOS[tipo]
        x, y = caja["x"] * k, caja["y"] * k
        w, h = max(caja["ancho"] * k, 4), max(caja["alto"] * k, 4)
        grosor = 4 if rid == resaltado else 2
        trazo = "" if tipo == "imagen" else ' stroke-dasharray="6 4"'
        partes.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" '
                      f'fill="{"none" if fondo_png and tipo == "fijo" else relleno}" stroke="{borde}" '
                      f'stroke-width="{grosor}"{trazo}/>')
        ancho_et = 15 * len(etiqueta) + 12
        libre = w - ancho_et - 12
        if not fondo_png and texto and h > 28 and libre > 40:  # sin miniatura: algo del contenido al lado
            partes.append(f'<text x="{x + ancho_et + 7:.1f}" y="{y + 21:.1f}" font-size="19" fill="#1C1A19">'
                          f'{escape(_corto(texto, max(int(libre / 10), 3)))}</text>')
        partes.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{ancho_et}" height="28" rx="3" fill="{borde}"/>'
                      f'<text x="{x + 6:.1f}" y="{y + 21:.1f}" font-size="19" font-weight="700" '
                      f'fill="#FFFFFF">{etiqueta}</text>')
    partes.append("</svg>")
    return "".join(partes)
