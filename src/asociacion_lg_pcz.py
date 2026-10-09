"""Asociación manual de filas del Libro de Guardia (LG) con novedades del PCZ.

Todo local: sin IA ni APIs. La app propone candidatos de PCZ con la MISMA fecha que la
fila de LG, ordenados por una similitud simple (números, palabras y hora compartidos).
"""
import datetime as dt
import hashlib
import html
import io
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

# ------------------------------------------------------------------ columnas
# Nombre canónico -> función que reconoce el encabezado ya normalizado
# (sin tildes, minúsculas, solo letras y números).
COLUMNAS_LG = {
    "Página": lambda c: c in ("pagina", "pag"),
    "Fecha": lambda c: c == "fecha",
    "Hora": lambda c: c == "hora",
    "Transcripción": lambda c: c == "transcripcion",
}
COLUMNAS_PCZ = {
    "Descripción": lambda c: c == "descripcion",
    "Fecha": lambda c: c == "fecha",
    # "N° Novedad", "Nº Novedad", "N Novedad", "Nro. Novedad", "Número de novedad"...
    "N° Novedad": lambda c: re.fullmatch(r"(n|no|nro|num|numero)?(de)?novedad", c) is not None,
}

ESTADOS = {"asociada": "Asociada", "ninguna": "Ninguna", "pendiente": "Pendiente"}


def sin_tildes(texto: str) -> str:
    """'Señal Nº 12' -> 'senal no 12' (minúsculas, sin tildes)."""
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(ch for ch in t if not unicodedata.combining(ch)).lower()


def _clave_encabezado(nombre) -> str:
    return re.sub(r"[^a-z0-9]", "", sin_tildes(nombre))


def mapear_columnas(df: pd.DataFrame, esperadas: dict) -> tuple[dict, list[str]]:
    """Busca cada columna esperada entre los encabezados del archivo.

    Devuelve ({nombre canónico: nombre real en el archivo}, [faltantes]).
    """
    mapa, faltan = {}, []
    for canon, reconoce in esperadas.items():
        real = next((c for c in df.columns if reconoce(_clave_encabezado(c))), None)
        if real is None:
            faltan.append(canon)
        else:
            mapa[canon] = real
    return mapa, faltan


def leer_tabla(nombre: str, contenido: bytes) -> pd.DataFrame:
    """Lee un .xlsx/.xls (primera hoja) o .csv sin tocar el archivo original."""
    if nombre.lower().endswith(".csv"):
        texto = contenido.decode("utf-8-sig", errors="replace")
        sep = ";" if texto.splitlines()[0].count(";") > texto.splitlines()[0].count(",") else ","
        df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contenido))
    df.columns = [str(c).strip() for c in df.columns]
    return df


# -------------------------------------------------------------------- fechas
_EXCEL_ORIGEN = dt.date(1899, 12, 30)


def parsear_fecha(valor) -> dt.date | None:
    """Fecha de Excel (serial, datetime) o texto argentino (día primero) -> date.

    Acepta "DD/MM/AAAA", "D/M/AA", con "/", "-" o "."; también "AAAA-MM-DD".
    NUNCA interpreta mes primero. Devuelve None si no se puede.
    """
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    if isinstance(valor, (pd.Timestamp, dt.datetime)):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return _desde_serial(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", texto):
        return _desde_serial(float(texto))
    # Día/mes/año (opcionalmente seguido de una hora)
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2}|\d{4})(?:[ T].*)?", texto)
    if m:
        d, mes, a = (int(x) for x in m.groups())
        if a < 100:
            a += 2000
        return _fecha_segura(a, mes, d)
    # Año-mes-día (ISO, como lo guarda Excel/pandas al pasar a texto)
    m = re.fullmatch(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})(?:[ T].*)?", texto)
    if m:
        a, mes, d = (int(x) for x in m.groups())
        return _fecha_segura(a, mes, d)
    return None


def _desde_serial(n: float) -> dt.date | None:
    # Rango razonable: 1954 a 2119
    if 20000 <= n <= 80000:
        return _EXCEL_ORIGEN + dt.timedelta(days=int(n))
    return None


def _fecha_segura(a: int, m: int, d: int) -> dt.date | None:
    try:
        return dt.date(a, m, d)
    except ValueError:
        return None


def formatear_fecha(f: dt.date | None) -> str:
    return f.strftime("%d/%m/%Y") if f else "—"


# ---------------------------------------------------------------------- horas
_RE_HORA = re.compile(
    r"(?<![\d/.:])([01]?\d|2[0-3])(?:[:.]([0-5]\d)(?![\d/])\s*(?:hs?\b)?|\s*hs\b)",
    re.IGNORECASE,
)


def parsear_hora(valor) -> int | None:
    """Hora de la columna Hora -> minutos desde las 00:00 (o None)."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    if isinstance(valor, (pd.Timestamp, dt.datetime, dt.time)):
        return valor.hour * 60 + valor.minute
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 0 <= valor < 1:  # fracción de día de Excel
            return round(valor * 24 * 60) % (24 * 60)
        if 0 <= valor < 24:
            return int(valor) * 60
        return None
    texto = str(valor).strip()
    m = re.fullmatch(r"([01]?\d|2[0-3])(?:[:.]([0-5]\d))?(?::\d\d)?\s*(?:hs?)?", texto, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    return None


def horas_en_texto(texto: str) -> list[tuple[int, int, int]]:
    """Horas escritas en un texto: [(inicio, fin, minutos)]. Ej. '14:30', '9.05 hs', '22hs'."""
    return [
        (m.start(), m.end(), int(m.group(1)) * 60 + int(m.group(2) or 0))
        for m in _RE_HORA.finditer(texto)
    ]


def formatear_hora(minutos: int | None) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}" if minutos is not None else ""


# ------------------------------------------------------------------- tokens
STOPWORDS = set("""
a al algo ante antes asi aun bajo cada como con contra cual cuando de del desde donde dos
durante e el ella ellas ellos en entre era es esa ese eso esta estaba estan este esto fue
fueron ha habia han hasta hay hace la las le les lo los mas me mi muy nada ni no nos o otra
otro para pero poco por porque que quien se sea segun ser si sin sobre son su sus tal tambien
tan te tiene todo tras un una uno unos unas y ya hs hrs horas hora siendo queda quedo luego
dia dias mismo misma informa informan avisa avisan comunica comunican realiza realizan
""".split())

# Orden de la alternativa: km "14/116", sigla con guion "E-712", palabra/número
_RE_TOKEN = re.compile(r"\d+/\d+|\b[^\W\d_]{1,3}-\d+\b|[^\W_]+")


def tokens(texto: str) -> list[tuple[int, int, str]]:
    """Tokens comparables de un texto: [(inicio, fin, clave)].

    Clave "n:<número>" para números (sin ceros a la izquierda; "E712" -> "n:712",
    "14/116" -> "n:14/116") y "w:<raíz>" para palabras (sin tildes, 5 primeras letras,
    para que "señal" y "señales" coincidan). Las horas no cuentan como números.
    """
    texto = str(texto or "")
    horas = [(i, f) for i, f, _ in horas_en_texto(texto)]
    salida = []
    for m in _RE_TOKEN.finditer(texto):
        if any(i <= m.start() < f for i, f in horas):
            continue
        t = sin_tildes(m.group())
        if any(ch.isdigit() for ch in t):
            if "/" in t:
                clave = "/".join(p.lstrip("0") or "0" for p in t.split("/"))
            else:
                clave = "".join(ch for ch in t if ch.isdigit()).lstrip("0") or "0"
            salida.append((m.start(), m.end(), "n:" + clave))
        elif len(t) >= 3 and t not in STOPWORDS:
            salida.append((m.start(), m.end(), "w:" + t[:5]))
    return salida


# ------------------------------------------------------------------ puntaje
PUNTOS_NUMERO = 3        # número de 2+ cifras compartido (señal, cambio, km, tren...)
PUNTOS_NUMERO_CHICO = 1  # número de 1 cifra (más casual)
PUNTOS_PALABRA = 1       # palabra clave compartida


def puntos_hora(diferencia: int) -> int:
    if diferencia <= 30:
        return 3
    if diferencia <= 60:
        return 2
    if diferencia <= 120:
        return 1
    return 0


def similitud(texto_lg: str, horas_lg: list[int], texto_pcz: str) -> dict:
    """Puntaje explicable entre una fila de LG y una descripción de PCZ."""
    claves_lg = {c for _, _, c in tokens(texto_lg)}
    claves_pcz = {c for _, _, c in tokens(texto_pcz)}
    comunes = claves_lg & claves_pcz
    numeros = sorted(c[2:] for c in comunes if c.startswith("n:"))
    palabras = sorted(c[2:] for c in comunes if c.startswith("w:"))
    puntaje = sum(PUNTOS_NUMERO if len(n.replace("/", "")) >= 2 else PUNTOS_NUMERO_CHICO for n in numeros)
    puntaje += PUNTOS_PALABRA * len(palabras)

    horas_pcz = [h for _, _, h in horas_en_texto(texto_pcz)]
    dif = None
    if horas_lg and horas_pcz:
        # Diferencia circular (23:50 y 00:10 están a 20 minutos)
        dif = min(min(abs(a - b), 24 * 60 - abs(a - b)) for a in horas_lg for b in horas_pcz)
        puntaje += puntos_hora(dif)

    partes = []
    if numeros:
        partes.append(f"{len(numeros)} número(s): {', '.join(numeros)}")
    if palabras:
        partes.append(f"{len(palabras)} palabra(s)")
    if dif is not None:
        partes.append(f"hora a {dif} min")
    return {
        "puntaje": puntaje,
        "comunes": comunes,
        "dif_hora": dif,
        "detalle": " · ".join(partes) or "sin coincidencias",
    }


def resaltar(texto: str, comunes: set[str], horas_cercanas: bool = False) -> str:
    """HTML del texto con <mark> en los números/palabras compartidos (y horas si suman)."""
    texto = str(texto or "")
    marcas = [(i, f) for i, f, c in tokens(texto) if c in comunes]
    if horas_cercanas:
        marcas += [(i, f) for i, f, _ in horas_en_texto(texto)]
    marcas.sort()
    salida, pos = [], 0
    for i, f in marcas:
        if i < pos:
            continue
        salida.append(html.escape(texto[pos:i]))
        salida.append(f"<mark>{html.escape(texto[i:f])}</mark>")
        pos = f
    salida.append(html.escape(texto[pos:]))
    return "".join(salida)


# ---------------------------------------------------------------- preparar
def id_novedad(valor) -> str:
    """101, 101.0 y ' 101 ' -> '101'."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def avisos(transcripcion) -> list[str]:
    """Cada renglón no vacío de la transcripción es un aviso."""
    if transcripcion is None or (not isinstance(transcripcion, str) and pd.isna(transcripcion)):
        return []
    return [r.strip() for r in str(transcripcion).splitlines() if r.strip()]


def preparar_lg(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Tabla de trabajo de LG: una fila por párrafo, con fecha y hora ya normalizadas."""
    t = pd.DataFrame({
        "pagina": df[mapa["Página"]].map(lambda v: "" if pd.isna(v) else id_novedad(v)),
        "fecha_original": df[mapa["Fecha"]],
        "fecha": df[mapa["Fecha"]].map(parsear_fecha),
        "hora": df[mapa["Hora"]].map(parsear_hora),
        "hora_original": df[mapa["Hora"]],
        "avisos": df[mapa["Transcripción"]].map(avisos),
    })
    t["texto"] = t["avisos"].map(" ".join)
    return t.reset_index(drop=True)


def preparar_pcz(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Tabla de trabajo de PCZ: id, descripción y fecha normalizada."""
    t = pd.DataFrame({
        "id": df[mapa["N° Novedad"]].map(id_novedad),
        "descripcion": df[mapa["Descripción"]].map(lambda v: "" if pd.isna(v) else str(v).strip()),
        "fecha_original": df[mapa["Fecha"]],
        "fecha": df[mapa["Fecha"]].map(parsear_fecha),
    })
    return t.reset_index(drop=True)


def fechas_invalidas(t: pd.DataFrame) -> pd.DataFrame:
    """Filas cuya fecha no se pudo interpretar (para mostrárselas al usuario)."""
    malas = t[t["fecha"].isna()]
    return pd.DataFrame({
        "Fila": malas.index + 1,
        "Fila en Excel": malas.index + 2,
        "Fecha tal cual viene": malas["fecha_original"].map(lambda v: "(vacía)" if pd.isna(v) else str(v)),
    })


def ids_repetidos(pcz: pd.DataFrame) -> list[str]:
    ids = pcz["id"]
    return sorted(set(ids[ids.duplicated() & (ids != "")]))


# --------------------------------------------------------------- candidatos
def filtrar_por_fecha(pcz: pd.DataFrame, fecha: dt.date | None, vecinos: bool = False) -> pd.DataFrame:
    """Novedades de PCZ con la MISMA fecha (y, si vecinos=True, del día anterior/siguiente).

    Agrega la columna "otro_dia" (True para las del día anterior/siguiente).
    Sin fecha válida en LG no hay candidatos por fecha.
    """
    if fecha is None:
        return pcz.iloc[0:0].assign(otro_dia=pd.Series(dtype=bool))
    dias = {fecha}
    if vecinos:
        dias |= {fecha - dt.timedelta(days=1), fecha + dt.timedelta(days=1)}
    sel = pcz[pcz["fecha"].isin(dias)].copy()
    sel["otro_dia"] = sel["fecha"] != fecha
    return sel


def puntuar(fila_lg: pd.Series, sel: pd.DataFrame) -> pd.DataFrame:
    """Agrega puntaje, detalle y coincidencias a cada novedad de `sel` (debe tener "otro_dia")."""
    sel = sel.copy()
    horas_lg = [h for h in [fila_lg["hora"]] if h is not None and not pd.isna(h)]
    horas_lg += [h for _, _, h in horas_en_texto(fila_lg["texto"])]
    resultados = [similitud(fila_lg["texto"], horas_lg, d) for d in sel["descripcion"]]
    sel["puntaje"] = [r["puntaje"] for r in resultados]
    sel["detalle"] = [r["detalle"] for r in resultados]
    sel["comunes"] = [r["comunes"] for r in resultados]
    sel["hora_suma"] = [r["dif_hora"] is not None and puntos_hora(r["dif_hora"]) > 0 for r in resultados]
    sel["fila_pcz"] = sel.index
    return sel.sort_values(["otro_dia", "puntaje", "fila_pcz"], ascending=[True, False, True])


def candidatos(fila_lg: pd.Series, pcz: pd.DataFrame, vecinos: bool = False) -> pd.DataFrame:
    """Candidatos ordenados: primero los de la misma fecha, de mayor a menor puntaje."""
    return puntuar(fila_lg, filtrar_por_fecha(pcz, fila_lg["fecha"], vecinos))


def pcz_sin_fecha(fila_lg: pd.Series, pcz: pd.DataFrame) -> pd.DataFrame:
    """Novedades de PCZ cuya fecha no se pudo interpretar (pueden ser de cualquier día)."""
    return puntuar(fila_lg, pcz[pcz["fecha"].isna()].assign(otro_dia=True))


def todas_las_novedades(fila_lg: pd.Series, pcz: pd.DataFrame) -> pd.DataFrame:
    """Todas las novedades puntuadas (para filas de LG sin fecha válida)."""
    return puntuar(fila_lg, pcz.assign(otro_dia=True))


def buscar(cands: pd.DataFrame, texto: str) -> pd.DataFrame:
    """Filtra candidatos que contengan todas las palabras buscadas (sin tildes/mayúsculas)."""
    palabras = sin_tildes(texto).split()
    if not palabras:
        return cands
    base = (cands["id"] + " " + cands["descripcion"]).map(sin_tildes)
    return cands[base.map(lambda b: all(p in b for p in palabras))]


# ------------------------------------------------------------------ sesión
def huella(*contenidos: bytes) -> str:
    """Identifica el par de archivos para retomar la sesión correcta."""
    h = hashlib.sha1()
    for c in contenidos:
        h.update(hashlib.sha1(c).digest())
    return h.hexdigest()[:16]


def sesion_nueva(huella_archivos: str, nombre_lg: str, nombre_pcz: str, n_lg: int) -> dict:
    return {
        "version": 1,
        "huella": huella_archivos,
        "archivo_lg": nombre_lg,
        "archivo_pcz": nombre_pcz,
        "posicion": 0,
        # fila LG (str) -> {"estado", "novedades": [ids], "avisos": {id: [n° de renglón]}}
        "filas": {str(i): {"estado": "pendiente", "novedades": [], "avisos": {}} for i in range(n_lg)},
        "historial": [],
    }


def registrar(sesion: dict, fila: int, estado: str, novedades=(), avisos_por_novedad=None):
    """Guarda la decisión de una fila (y lo anterior en el historial para Deshacer)."""
    clave = str(fila)
    sesion["historial"].append({
        "fila": fila, "antes": sesion["filas"][clave], "posicion": sesion["posicion"],
    })
    sesion["historial"] = sesion["historial"][-300:]
    novedades = list(dict.fromkeys(novedades))
    sesion["filas"][clave] = {
        "estado": estado,
        "novedades": novedades,
        "avisos": {n: sorted(v) for n, v in (avisos_por_novedad or {}).items() if v and n in novedades},
    }


def deshacer(sesion: dict) -> int | None:
    """Revierte la última decisión. Devuelve la fila afectada (o None si no hay nada)."""
    if not sesion["historial"]:
        return None
    ultimo = sesion["historial"].pop()
    sesion["filas"][str(ultimo["fila"])] = ultimo["antes"]
    sesion["posicion"] = ultimo["fila"]
    return ultimo["fila"]


def asociaciones_por_novedad(sesion: dict) -> dict[str, list[int]]:
    """id de novedad -> filas de LG (0-based) a las que está asociada."""
    salida: dict[str, list[int]] = {}
    for fila, d in sesion["filas"].items():
        if d["estado"] == "asociada":
            for n in d["novedades"]:
                salida.setdefault(n, []).append(int(fila))
    return {n: sorted(f) for n, f in salida.items()}


def progreso(sesion: dict) -> dict:
    estados = [d["estado"] for d in sesion["filas"].values()]
    return {
        "total": len(estados),
        "asociadas": estados.count("asociada"),
        "ninguna": estados.count("ninguna"),
        "pendientes": estados.count("pendiente"),
    }


def siguiente_pendiente(sesion: dict, desde: int) -> int | None:
    n = len(sesion["filas"])
    for k in range(1, n + 1):
        i = (desde + k) % n
        if sesion["filas"][str(i)]["estado"] == "pendiente":
            return i
    return None


def guardar_sesion(sesion: dict, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"sesion_{sesion['huella']}.json"
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(sesion_a_json(sesion), encoding="utf-8")
    tmp.replace(ruta)  # escritura atómica: si se corta, no queda el JSON a medias
    return ruta


def cargar_sesion(carpeta: Path, huella_archivos: str) -> dict | None:
    ruta = carpeta / f"sesion_{huella_archivos}.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def sesion_a_json(sesion: dict) -> str:
    return json.dumps(sesion, ensure_ascii=False, indent=1)


def importar_sesion(texto: str, n_lg: int, huella_archivos: str) -> tuple[dict, list[str]]:
    """Lee un JSON exportado. Devuelve (sesión, advertencias). Lanza ValueError si no sirve."""
    try:
        sesion = json.loads(texto)
        filas = sesion["filas"]
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError("El archivo no es una sesión válida de este módulo.") from e
    avisos_ = []
    if sesion.get("huella") != huella_archivos:
        avisos_.append(
            "La sesión fue hecha con otros archivos (o con una versión distinta de ellos). "
            "Se cargó igual: revisá que las filas correspondan."
        )
    if len(filas) != n_lg:
        avisos_.append(f"La sesión tiene {len(filas)} filas de LG y el archivo actual tiene {n_lg}.")
    nuevas = sesion_nueva(huella_archivos, sesion.get("archivo_lg", ""), sesion.get("archivo_pcz", ""), n_lg)
    for i in range(n_lg):
        if str(i) in filas:
            nuevas["filas"][str(i)] = filas[str(i)]
    nuevas["posicion"] = min(int(sesion.get("posicion", 0)), max(n_lg - 1, 0))
    return nuevas, avisos_


# --------------------------------------------------------------- exportar
def _texto_lg(fila_lg: pd.Series, renglones: list[int] | None) -> str:
    """Texto de LG para una novedad: los renglones elegidos o el párrafo entero."""
    lineas = fila_lg["avisos"]
    if renglones:
        lineas = [lineas[i] for i in renglones if 0 <= i < len(lineas)]
    return " ".join(lineas)


def _sin_hora(v):
    if isinstance(v, (pd.Timestamp, dt.datetime)) and not pd.isna(v) and v.time() == dt.time(0):
        return v.date()
    return v


def _fechas_sin_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Fechas sin hora -> solo fecha (sin 00:00:00), también en columnas con formatos mezclados."""
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]) or df[c].dtype == object:
            df[c] = df[c].map(_sin_hora).astype(object)
    return df


def exportar(lg_original: pd.DataFrame, pcz_original: pd.DataFrame,
             lg: pd.DataFrame, pcz: pd.DataFrame, sesion: dict) -> bytes:
    """Excel con hojas LG_asociado, PCZ_completado y Resumen (no toca los originales)."""
    desc_por_id = dict(zip(pcz["id"], pcz["descripcion"]))

    # Hoja LG_asociado
    hoja_lg = _fechas_sin_hora(lg_original.copy())
    ids_col, desc_col, estado_col = [], [], []
    for i in range(len(lg)):
        d = sesion["filas"][str(i)]
        nov = d["novedades"] if d["estado"] == "asociada" else []
        ids_col.append(";".join(nov))
        desc_col.append(" | ".join(desc_por_id.get(n, "") for n in nov))
        estado_col.append(ESTADOS[d["estado"]])
    hoja_lg["N° Novedad asociada(s)"] = ids_col
    hoja_lg["Descripción PCZ"] = desc_col
    hoja_lg["Estado"] = estado_col

    # Hoja PCZ_completado
    textos: dict[str, list[str]] = {}
    for fila, d in sesion["filas"].items():
        if d["estado"] != "asociada":
            continue
        for n in d["novedades"]:
            textos.setdefault(n, []).append(_texto_lg(lg.loc[int(fila)], d.get("avisos", {}).get(n)))
    hoja_pcz = _fechas_sin_hora(pcz_original.copy())
    texto_lg = [" / ".join(textos.get(n, [])) for n in pcz["id"]]
    hoja_pcz["Texto LG"] = texto_lg
    hoja_pcz["Descripción combinada"] = [
        f"{desc} {t.lower()}".strip() if t else "" for desc, t in zip(pcz["descripcion"], texto_lg)
    ]

    # Hoja Resumen
    p = progreso(sesion)
    resumen = pd.DataFrame({
        "Concepto": ["Filas de LG", "Asociadas", "Ninguna corresponde", "Pendientes",
                     "Novedades de PCZ", "Novedades de PCZ con LG asociado"],
        "Cantidad": [p["total"], p["asociadas"], p["ninguna"], p["pendientes"],
                     len(pcz), sum(1 for n in pcz["id"] if n in textos)],
    })
    multiples = [
        {"N° Novedad": n, "Descripción PCZ": desc_por_id.get(n, ""),
         "Filas de LG": ", ".join(str(f + 1) for f in filas), "Cantidad": len(filas)}
        for n, filas in asociaciones_por_novedad(sesion).items() if len(filas) > 1
    ]
    multiples = pd.DataFrame(multiples, columns=["N° Novedad", "Descripción PCZ", "Filas de LG", "Cantidad"])

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl", date_format="DD/MM/YYYY",
                        datetime_format="DD/MM/YYYY HH:MM") as w:
        hoja_lg.to_excel(w, sheet_name="LG_asociado", index=False)
        hoja_pcz.to_excel(w, sheet_name="PCZ_completado", index=False)
        resumen.to_excel(w, sheet_name="Resumen", index=False)
        fila_titulo = len(resumen) + 3
        w.sheets["Resumen"].cell(row=fila_titulo, column=1,
                                 value="Novedades asociadas a más de una fila de LG")
        multiples.to_excel(w, sheet_name="Resumen", index=False, startrow=fila_titulo)
        for hoja in w.sheets.values():
            for fila in hoja.iter_rows(min_row=2):
                for celda in fila:
                    if isinstance(celda.value, dt.date) and (
                            not isinstance(celda.value, dt.datetime) or celda.value.time() == dt.time(0)):
                        celda.number_format = "DD/MM/YYYY"
            for col in hoja.columns:
                largo = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                hoja.column_dimensions[col[0].column_letter].width = min(max(largo + 2, 10), 60)
    return buffer.getvalue()
