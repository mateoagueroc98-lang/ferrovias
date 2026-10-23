"""Lectura de un Excel (.xlsx/.xlsm) sin Excel: hojas, gráficos y valores de celdas.

openpyxl no lee los gráficos de un archivo existente, así que se leen directo del xlsx (que es un
zip): xl/workbook.xml → hojas → xl/drawings/*.xml → cada gráfico (nombre, tipo, título y en qué
celdas está). Incluye los gráficos modernos (chartEx: treemap, cascada, embudo...), que el
archivo guarda dentro de un mc:AlternateContent. Funciona igual en la Mac y en Windows.
"""
import datetime as dt
import io
import posixpath
import re
import zipfile
from dataclasses import dataclass, field

from lxml import etree
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "cx": "http://schemas.microsoft.com/office/drawing/2014/chartex",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}
URI_GRAFICO = NS["c"]
URI_GRAFICO_MODERNO = NS["cx"]
MAX_FILAS, MAX_COLUMNAS = 1048576, 16384

TIPOS = {  # elemento del plotArea → nombre en pantalla
    "barChart": "Barras", "bar3DChart": "Barras 3D", "lineChart": "Líneas", "line3DChart": "Líneas 3D",
    "pieChart": "Torta", "pie3DChart": "Torta 3D", "ofPieChart": "Torta con subgráfico",
    "doughnutChart": "Anillo", "areaChart": "Áreas", "area3DChart": "Áreas 3D", "scatterChart": "Dispersión",
    "bubbleChart": "Burbujas", "radarChart": "Radial", "stockChart": "Cotizaciones", "surfaceChart": "Superficie",
    "surface3DChart": "Superficie 3D",
}
TIPOS_MODERNOS = {
    "treemap": "Treemap", "sunburst": "Proyección solar", "waterfall": "Cascada", "funnel": "Embudo",
    "boxWhisker": "Cajas y bigotes", "clusteredColumn": "Histograma", "paretoLine": "Pareto",
    "regionMap": "Mapa",
}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


class ErrorExcel(ValueError):
    """El archivo no se puede leer como Excel (mensaje listo para mostrar)."""


@dataclass
class Grafico:
    nombre: str            # el nombre que muestra Excel (Gráfico 3, Chart 1...)
    tipo: str              # Barras, Torta, Treemap...
    titulo: str            # título del gráfico ("" si no tiene)
    desde: str             # celda de arriba a la izquierda donde está (B5)
    hasta: str             # celda de abajo a la derecha (J20)
    moderno: bool = False  # chartEx (treemap, cascada...)
    en_grupo: bool = False

    def descripcion(self) -> str:
        partes = [self.tipo + (f" «{self.titulo}»" if self.titulo else ""), f"en {self.desde}:{self.hasta}"]
        if self.en_grupo:
            partes.append("dentro de un grupo")
        return f"{self.nombre} — " + ", ".join(partes)


@dataclass
class Hoja:
    nombre: str
    visible: bool
    es_de_grafico: bool = False   # hoja que es un gráfico entero (no tiene celdas)
    dimension: str = ""           # rango usado según el archivo (A1:Z200)
    graficos: list[Grafico] = field(default_factory=list)
    anchos: dict = field(default_factory=dict)  # {n° de columna: ancho en caracteres}


@dataclass
class InfoExcel:
    hojas: list[Hoja]

    def hoja(self, nombre: str) -> Hoja | None:
        return next((h for h in self.hojas if h.nombre == nombre), None)

    @property
    def visibles(self) -> list[Hoja]:
        return [h for h in self.hojas if h.visible and not h.es_de_grafico]


# --------------------------------------------------------------- referencias
def normalizar_celda(texto: str) -> str | None:
    """' b5 ' -> 'B5'; '$N$41' -> 'N41'. None si no es una celda válida."""
    m = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d{1,7})", str(texto).strip())
    if not m:
        return None
    col, fila = m.group(1).upper(), int(m.group(2))
    if not (1 <= fila <= MAX_FILAS and column_index_from_string(col) <= MAX_COLUMNAS):
        return None
    return f"{col}{fila}"


def partir_celda(celda: str) -> tuple[int, int]:
    """'N41' -> (41, 14): fila y columna."""
    m = re.fullmatch(r"([A-Z]+)(\d+)", celda)
    return int(m.group(2)), column_index_from_string(m.group(1))


def armar_rango(desde: str, hasta: str) -> str | None:
    """('N41', 'A5') -> 'A5:N41' (en cualquier orden). None si alguna celda no es válida."""
    a, b = normalizar_celda(desde), normalizar_celda(hasta)
    if not a or not b:
        return None
    (f1, c1), (f2, c2) = partir_celda(a), partir_celda(b)
    return f"{get_column_letter(min(c1, c2))}{min(f1, f2)}:{get_column_letter(max(c1, c2))}{max(f1, f2)}"


def ref_celda(hoja: str, celda: str) -> str:
    """('Carátula', 'D32') -> 'Carátula!D32'; con comillas si la hoja tiene espacios u otros signos."""
    if re.fullmatch(r"[^\W\d][\w.]*", hoja):
        return f"{hoja}!{celda}"
    return "'" + hoja.replace("'", "''") + f"'!{celda}"


def partir_ref(ref: str) -> tuple[str, str]:
    """'Carátula!D32' o "'Hoja 1'!D32" -> (hoja, celda). Si no tiene hoja: ('', celda)."""
    ref = str(ref).strip()
    if "!" not in ref:
        return "", ref
    hoja, celda = ref.rsplit("!", 1)
    if len(hoja) >= 2 and hoja[0] == hoja[-1] == "'":
        hoja = hoja[1:-1].replace("''", "'")
    return hoja, celda


# ------------------------------------------------------------- lectura del zip
def _xml(z: zipfile.ZipFile, ruta: str):
    return etree.fromstring(z.read(ruta))


def _rels(z: zipfile.ZipFile, parte: str) -> dict:
    """{rId: ruta dentro del zip} de las relaciones de una parte (xl/workbook.xml, etc.)."""
    carpeta, nombre = posixpath.split(parte)
    ruta = posixpath.join(carpeta, "_rels", nombre + ".rels")
    if ruta not in z.namelist():
        return {}
    out = {}
    for rel in _xml(z, ruta).findall("pr:Relationship", NS):
        if rel.get("TargetMode") == "External":
            continue
        destino = rel.get("Target")
        destino = destino.lstrip("/") if destino.startswith("/") else posixpath.normpath(posixpath.join(carpeta, destino))
        out[rel.get("Id")] = destino
    return out


def _titulo(raiz) -> str:
    titulo = raiz.find(".//c:title", NS)
    if titulo is None:
        titulo = raiz.find(".//cx:title", NS)
    if titulo is None:
        return ""
    textos = [t.text or "" for t in titulo.iter("{%s}t" % NS["a"])]
    if not textos:  # título que sale de una celda: Excel guarda el último valor
        textos = [v.text or "" for v in titulo.iter() if etree.QName(v).localname in ("v", "pt") and v.text]
    return " ".join("".join(textos).split())


def _tipo(z: zipfile.ZipFile, ruta: str, moderno: bool) -> tuple[str, str]:
    """(tipo, título) del gráfico guardado en `ruta`."""
    try:
        raiz = _xml(z, ruta)
    except (KeyError, etree.XMLSyntaxError):
        return ("Gráfico moderno" if moderno else "Gráfico"), ""
    if moderno:
        layouts = {s.get("layoutId") for s in raiz.iterfind(".//cx:series", NS)}
        nombres = [TIPOS_MODERNOS.get(l, l) for l in sorted(layouts - {None})]
        tipo = " + ".join(nombres) if nombres else "Gráfico moderno"
    else:
        area = raiz.find(".//c:plotArea", NS)
        tipos = []
        for hijo in area if area is not None else []:
            local = etree.QName(hijo).localname
            if local in TIPOS:
                nombre = TIPOS[local]
                if local in ("barChart", "bar3DChart"):
                    dir_ = hijo.find("c:barDir", NS)
                    if dir_ is not None and dir_.get("val") == "col":
                        nombre = nombre.replace("Barras", "Columnas")
                tipos.append(nombre)
        tipo = "Combinado (" + " + ".join(tipos) + ")" if len(tipos) > 1 else (tipos[0] if tipos else "Gráfico")
    return tipo, _titulo(raiz)


def _celda_de(marca) -> str:
    """xdr:from / xdr:to (columna y fila desde 0) -> 'B5'."""
    col = int(marca.findtext("xdr:col", "0", NS))
    fila = int(marca.findtext("xdr:row", "0", NS))
    return f"{get_column_letter(col + 1)}{fila + 1}"


def _marcos(elem, en_grupo=False):
    """Los xdr:graphicFrame de un ancla, entrando en grupos y en mc:AlternateContent (solo Choice)."""
    for hijo in elem:
        local = etree.QName(hijo).localname if isinstance(hijo.tag, str) else ""
        if local == "graphicFrame":
            yield hijo, en_grupo
        elif local == "grpSp":
            yield from _marcos(hijo, True)
        elif local == "AlternateContent":
            eleccion = hijo.find("mc:Choice", NS)
            if eleccion is not None:  # el Fallback es una copia vieja (un cartel): no se cuenta
                yield from _marcos(eleccion, en_grupo)


EMU_POR_PX = 9525
ALTO_FILA_PX = 20  # 15 puntos, el alto normal de una fila


def ancho_columna_px(anchos: dict, col: int) -> float:
    """Ancho en píxeles de la columna (n° desde 1), según el ancho en caracteres del archivo."""
    return anchos.get(col, 8.43) * 7 + 5


def _celda_final(desde: str, ancho_emu: int, alto_emu: int, anchos: dict) -> str:
    """Celda donde termina un gráfico anclado a una sola celda (se calcula con su tamaño)."""
    fila, col = partir_celda(desde)
    resto = ancho_emu / EMU_POR_PX - ancho_columna_px(anchos, col)
    while resto > 0 and col < MAX_COLUMNAS:
        col += 1
        resto -= ancho_columna_px(anchos, col)
    filas = max(int(-(-alto_emu / EMU_POR_PX // ALTO_FILA_PX)) - 1, 0)
    return f"{get_column_letter(col)}{min(fila + filas, MAX_FILAS)}"


def _graficos(z: zipfile.ZipFile, ruta_dibujo: str, anchos: dict) -> list[Grafico]:
    rels = _rels(z, ruta_dibujo)
    graficos = []
    for ancla in _xml(z, ruta_dibujo):
        local = etree.QName(ancla).localname if isinstance(ancla.tag, str) else ""
        if local == "AlternateContent":  # a veces el ancla entera viene envuelta
            eleccion = ancla.find("mc:Choice", NS)
            ancla = eleccion[0] if eleccion is not None and len(eleccion) else ancla
            local = etree.QName(ancla).localname
        if local not in ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor"):
            continue
        desde = ancla.find("xdr:from", NS)
        hasta = ancla.find("xdr:to", NS)
        celda_desde = _celda_de(desde) if desde is not None else "A1"
        ext = ancla.find("xdr:ext", NS)
        if hasta is not None:
            celda_hasta = _celda_de(hasta)
        elif ext is not None:
            celda_hasta = _celda_final(celda_desde, int(ext.get("cx", 0)), int(ext.get("cy", 0)), anchos)
        else:
            celda_hasta = celda_desde
        for marco, en_grupo in _marcos(ancla):
            datos = marco.find("a:graphic/a:graphicData", NS)
            if datos is None or datos.get("uri") not in (URI_GRAFICO, URI_GRAFICO_MODERNO):
                continue
            moderno = datos.get("uri") == URI_GRAFICO_MODERNO
            ref = datos.find("cx:chart" if moderno else "c:chart", NS)
            ruta = rels.get(ref.get("{%s}id" % NS["r"])) if ref is not None else None
            tipo, titulo = _tipo(z, ruta, moderno) if ruta else ("Gráfico", "")
            nombre = marco.find("xdr:nvGraphicFramePr/xdr:cNvPr", NS).get("name", "")
            graficos.append(Grafico(nombre, tipo, titulo, celda_desde, celda_hasta, moderno, en_grupo))
    return graficos


def _dimension_y_anchos(z: zipfile.ZipFile, ruta: str) -> tuple[str, dict]:
    """Rango usado (<dimension>) y anchos de columna (<cols>), leyendo solo el principio de la hoja."""
    dimension, anchos = "", {}
    with z.open(ruta) as f:
        for _, elem in etree.iterparse(f, events=("end",)):
            local = etree.QName(elem).localname
            if local == "dimension":
                dimension = elem.get("ref", "")
            elif local == "col":
                for n in range(int(elem.get("min")), min(int(elem.get("max")), 300) + 1):
                    anchos[n] = float(elem.get("width", 8.43))
            elif local == "sheetData":  # las celdas no hacen falta
                break
            if local in ("sheetData", "row", "c"):
                elem.clear()
    return dimension, anchos


def leer(contenido: bytes) -> InfoExcel:
    """Hojas (con su estado visible/oculta) y los gráficos de cada una."""
    try:
        z = zipfile.ZipFile(io.BytesIO(contenido))
        libro = _xml(z, "xl/workbook.xml")
    except (zipfile.BadZipFile, KeyError, etree.XMLSyntaxError) as e:
        raise ErrorExcel("El archivo no se puede leer como Excel (.xlsx o .xlsm). Si es un .xls viejo, "
                         "abrilo en Excel y guardalo como .xlsx.") from e
    rels = _rels(z, "xl/workbook.xml")
    hojas = []
    for h in libro.iterfind("m:sheets/m:sheet", NS):
        ruta = rels.get(h.get("{%s}id" % NS["r"]), "")
        hoja = Hoja(h.get("name"), h.get("state", "visible") == "visible", "chartsheets/" in ruta)
        if ruta in z.namelist() and not hoja.es_de_grafico:
            hoja.dimension, hoja.anchos = _dimension_y_anchos(z, ruta)
            for destino in _rels(z, ruta).values():
                if "/drawings/" in destino and destino.endswith(".xml") and destino in z.namelist():
                    hoja.graficos.extend(_graficos(z, destino, hoja.anchos))
        hojas.append(hoja)
    return InfoExcel(hojas)


# ---------------------------------------------------------------- tamaños
def tamano_rango_px(hoja: Hoja | None, rango: str) -> tuple[int, int]:
    """Tamaño aproximado del rango en píxeles de pantalla (para la vista simulada)."""
    a, b = rango.split(":")
    (f1, c1), (f2, c2) = partir_celda(a), partir_celda(b)
    anchos = hoja.anchos if hoja else {}
    ancho = sum(ancho_columna_px(anchos, c) for c in range(c1, min(c2, c1 + 300) + 1))
    return round(ancho), (min(f2, f1 + 2000) - f1 + 1) * ALTO_FILA_PX


# ---------------------------------------------------------------- valores
def leer_celdas(contenido: bytes, refs: list[str]) -> dict:
    """{ref: texto} con el último valor guardado en el archivo (sin recalcular nada).

    Lo que no existe queda como None. El texto imita el formato de la celda (fechas, %, decimales
    con coma) pero es aproximado: el valor exacto lo da Excel en Windows.
    """
    out = {}
    if not refs:
        return out
    try:
        wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - cualquier problema de openpyxl
        raise ErrorExcel(f"No se pudieron leer las celdas del Excel ({e}).") from e
    try:
        for ref in refs:
            hoja, celda = partir_ref(ref)
            celda = normalizar_celda(celda)
            if hoja not in wb.sheetnames or not celda:
                out[ref] = None
                continue
            c = wb[hoja][celda]
            out[ref] = texto_valor(c.value, c.number_format or "General")
    finally:
        wb.close()
    return out


def texto_valor(valor, formato: str = "General") -> str:
    """Texto de un valor de celda, más o menos como lo muestra Excel en castellano."""
    if valor is None:
        return ""
    f = formato.lower()
    if isinstance(valor, (dt.datetime, dt.date)):
        if "mmmm" in f:
            texto = MESES[valor.month - 1]
            if "yy" in f:
                texto += f" {valor.year if 'yyyy' in f else str(valor.year)[2:]}"
            return texto  # Excel en castellano muestra el mes en minúscula
        if isinstance(valor, dt.datetime) and (valor.hour or valor.minute) and "h" in f:
            return f"{valor:%d/%m/%Y %H:%M}"
        return f"{valor:%d/%m/%Y}"
    if isinstance(valor, bool):
        return "VERDADERO" if valor else "FALSO"
    if isinstance(valor, (int, float)):
        decimales = 0
        m = re.search(r"0[.,](0+)", formato)
        if m:
            decimales = len(m.group(1))
        elif f == "general":
            return _con_coma(f"{valor:.10g}")
        if "%" in formato:
            return _con_coma(f"{valor * 100:,.{decimales}f}") + "%"
        return _con_coma(f"{valor:,.{decimales}f}" if "," in formato.split(".")[0] or "#" in formato
                         else f"{valor:.{decimales}f}")
    return str(valor)


def _con_coma(texto: str) -> str:
    """'12,500.5' -> '12.500,5' (separadores de Argentina)."""
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


if __name__ == "__main__":  # python -m src.informes_pptx.excel_zip archivo.xlsx: hojas y gráficos
    import sys
    from pathlib import Path
    for ruta in sys.argv[1:]:
        print(f"##### {ruta}")
        for h in leer(Path(ruta).read_bytes()).hojas:
            estado = "visible" if h.visible else "OCULTA"
            print(f"\nHoja «{h.nombre}» ({estado}{', hoja de gráfico' if h.es_de_grafico else ''})"
                  f"{' – usa ' + h.dimension if h.dimension else ''} – {len(h.graficos)} gráficos")
            for g in h.graficos:
                print(f"  · {g.descripcion()}")
