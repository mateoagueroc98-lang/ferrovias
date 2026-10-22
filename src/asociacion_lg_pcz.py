"""Asociación manual de filas del Libro de Guardia (LG) con novedades del PCZ.

Todo local: sin IA ni APIs. La app propone candidatos de PCZ con la MISMA fecha que la
fila de LG, ordenados por una similitud simple (números, palabras y hora compartidos).
"""
import datetime as dt
import hashlib
import html
import io
import re
import unicodedata

import pandas as pd

# ------------------------------------------------------------------ columnas
# Nombre canónico -> función que reconoce el encabezado ya normalizado
# (sin tildes, minúsculas, solo letras y números).
COLUMNAS_LG = {
    "Fecha": lambda c: c == "fecha",
    "Transcripción": lambda c: c == "transcripcion",
    "Hora": lambda c: c.startswith("hora"),
}
COLUMNAS_PCZ = {
    "Fecha": lambda c: c == "fecha",
    "Descripción": lambda c: c == "descripcion",
    # "N° Novedad", "Nº Novedad", "N Novedad", "Nro. Novedad", "Número de novedad"...
    "N° Novedad": lambda c: re.fullmatch(r"(n|no|nro|num|numero)?(de)?novedad", c) is not None,
    "Hora": lambda c: c.startswith("hora"),
}



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


def formatear_hora(minutos) -> str:
    """Minutos desde las 00:00 -> "HH:MM" (vacío si no hay hora)."""
    if minutos is None or pd.isna(minutos):
        return ""
    minutos = int(minutos)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


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


def similitud(texto_lg: str, horas_lg: list[int], texto_pcz: str, horas_pcz: list[int] = ()) -> dict:
    """Puntaje explicable entre una fila de LG y una descripción de PCZ.

    horas_lg / horas_pcz: horas de las columnas Hora (las escritas en los textos se suman solas).
    """
    claves_lg = {c for _, _, c in tokens(texto_lg)}
    claves_pcz = {c for _, _, c in tokens(texto_pcz)}
    comunes = claves_lg & claves_pcz
    numeros = sorted(c[2:] for c in comunes if c.startswith("n:"))
    palabras = sorted(c[2:] for c in comunes if c.startswith("w:"))
    puntaje = sum(PUNTOS_NUMERO if len(n.replace("/", "")) >= 2 else PUNTOS_NUMERO_CHICO for n in numeros)
    puntaje += PUNTOS_PALABRA * len(palabras)

    horas_pcz = list(horas_pcz) + [h for _, _, h in horas_en_texto(texto_pcz)]
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


# Columnas que pueden no estar en el archivo de LG
OPCIONALES_LG = ("Hora",)


def preparar_lg(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Tabla de trabajo de LG: una fila por párrafo, con fecha y hora ya normalizadas.

    mapa: {nombre canónico: columna del archivo}. Hora es opcional.
    """
    vacia = pd.Series([None] * len(df), index=df.index, dtype=object)
    pagina = df[mapa["Página"]] if "Página" in mapa else vacia
    hora = df[mapa["Hora"]] if "Hora" in mapa else vacia
    t = pd.DataFrame({
        "pagina": pagina.map(lambda v: "" if pd.isna(v) else id_novedad(v)),
        "fecha_original": df[mapa["Fecha"]],
        "fecha": df[mapa["Fecha"]].map(parsear_fecha),
        # dtype object: si no, con filas sin hora pandas pasa los minutos a decimales (510.0)
        "hora": pd.Series([parsear_hora(v) for v in hora], index=df.index, dtype=object),
        "hora_original": hora,
        "avisos": df[mapa["Transcripción"]].map(avisos),
    })
    t["texto"] = t["avisos"].map(" ".join)
    return t.reset_index(drop=True)


# Columnas que pueden no estar en el archivo de PCZ (sin N° Novedad se usa el número de fila del Excel)
OPCIONALES_PCZ = ("N° Novedad", "Hora")


def preparar_pcz(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Tabla de trabajo de PCZ: id, descripción, fecha y hora normalizadas.

    Sin columna "N° Novedad", el id de cada novedad es su número de fila en el Excel.
    """
    if "N° Novedad" in mapa:
        ids = df[mapa["N° Novedad"]].map(id_novedad)
    else:
        ids = pd.Series([str(i + 2) for i in range(len(df))], index=df.index)
    hora = df[mapa["Hora"]] if "Hora" in mapa else pd.Series([None] * len(df), index=df.index)
    t = pd.DataFrame({
        "id": ids,
        "descripcion": df[mapa["Descripción"]].map(lambda v: "" if pd.isna(v) else str(v).strip()),
        "fecha_original": df[mapa["Fecha"]],
        "fecha": df[mapa["Fecha"]].map(parsear_fecha),
        "hora": pd.Series([parsear_hora(v) for v in hora], index=df.index, dtype=object),
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
    horas_pcz = sel["hora"] if "hora" in sel else pd.Series([None] * len(sel), index=sel.index)
    resultados = [similitud(fila_lg["texto"], horas_lg, d, [h] if h is not None and not pd.isna(h) else [])
                  for d, h in zip(sel["descripcion"], horas_pcz)]
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


# ----------------------------------------------- estado del trabajo (en memoria)
def huella(*contenidos: bytes) -> str:
    """Identifica un archivo (o un par de archivos) para saber si se cargó otro."""
    h = hashlib.sha1()
    for c in contenidos:
        h.update(hashlib.sha1(c).digest())
    return h.hexdigest()[:16]


def trabajo_nuevo(huella_archivos: str, n_lg: int) -> dict:
    """Estado del trabajo de asociación. Vive solo en memoria mientras la app está abierta.

    Por cada fila de LG: las asociaciones hechas (grupos de avisos -> novedades) y los avisos
    descartados (los que no tienen novedad en PCZ).
    """
    return {
        "huella": huella_archivos,
        "posicion": 0,
        "filas": {str(i): {"grupos": [], "descartados": []} for i in range(n_lg)},
        "historial": [],
    }


def registrar(trabajo: dict, fila: int, grupos: list[dict], descartados) -> None:
    """Guarda cómo queda una fila (y lo anterior en el historial, para Deshacer)."""
    clave = str(fila)
    trabajo["historial"].append({"fila": fila, "antes": trabajo["filas"][clave]})
    trabajo["historial"] = trabajo["historial"][-300:]
    trabajo["filas"][clave] = {
        "grupos": [{"avisos": sorted(g["avisos"]), "novedades": list(dict.fromkeys(g["novedades"]))}
                   for g in grupos],
        "descartados": sorted(set(descartados)),
    }


def deshacer(trabajo: dict) -> int | None:
    """Revierte el último cambio. Devuelve la fila afectada (o None si no hay nada)."""
    if not trabajo["historial"]:
        return None
    ultimo = trabajo["historial"].pop()
    trabajo["filas"][str(ultimo["fila"])] = ultimo["antes"]
    trabajo["posicion"] = ultimo["fila"]
    return ultimo["fila"]


def avisos_cubiertos(grupos: list[dict]) -> set[int]:
    return {i for g in grupos for i in g["avisos"]}


def pendientes_de_fila(d: dict, n_avisos: int) -> list[int]:
    """Avisos de la fila que todavía no están asociados ni descartados."""
    resueltos = avisos_cubiertos(d["grupos"]) | set(d["descartados"])
    return [i for i in range(n_avisos) if i not in resueltos]


def filas_de_tabla(grupos: list[dict], n_avisos: int, descartados=()) -> list[dict]:
    """Filas para mostrar LG (izquierda) ↔ PCZ (derecha), en el orden de los avisos.

    Cada asociación es una fila; cada aviso descartado o pendiente es una fila sin novedades.
    """
    filas = [{**g, "descartado": False} for g in grupos]
    cubiertos = avisos_cubiertos(grupos)
    filas += [{"avisos": [i], "novedades": [], "descartado": i in descartados}
              for i in range(n_avisos) if i not in cubiertos]
    return sorted(filas, key=lambda f: (min(f["avisos"], default=-1), len(f["novedades"]) == 0))


def fila_con_avisos(fila_lg: pd.Series, renglones: list[int]) -> pd.Series:
    """Copia de la fila de LG cuyo texto son solo los avisos elegidos (para puntuar)."""
    elegidos = [fila_lg["avisos"][i] for i in renglones if 0 <= i < len(fila_lg["avisos"])]
    fila = fila_lg.copy()
    if elegidos:
        fila["texto"] = " ".join(elegidos)
    return fila


def asociaciones_por_novedad(trabajo: dict) -> dict[str, list[int]]:
    """id de novedad -> filas de LG (0-based) en las que está asociada."""
    salida: dict[str, set[int]] = {}
    for fila, d in trabajo["filas"].items():
        for g in d["grupos"]:
            for n in g["novedades"]:
                salida.setdefault(n, set()).add(int(fila))
    return {n: sorted(f) for n, f in salida.items()}


def progreso(trabajo: dict, n_avisos: list[int]) -> dict:
    """Avisos asociados / descartados / pendientes, y cantidad de asociaciones."""
    asociados = descartados = pendientes = asociaciones = 0
    for i, n in enumerate(n_avisos):
        d = trabajo["filas"][str(i)]
        cubiertos = avisos_cubiertos(d["grupos"])
        asociados += len(cubiertos)
        descartados += len(set(d["descartados"]) - cubiertos)
        pendientes += len(pendientes_de_fila(d, n))
        asociaciones += len(d["grupos"])
    return {"avisos": sum(n_avisos), "asociados": asociados, "descartados": descartados,
            "pendientes": pendientes, "asociaciones": asociaciones}


def siguiente_pendiente(trabajo: dict, desde: int, n_avisos: list[int]) -> int | None:
    """Próxima fila (dando la vuelta) que tiene avisos sin asociar ni descartar."""
    n = len(n_avisos)
    for k in range(1, n + 1):
        i = (desde + k) % n
        if pendientes_de_fila(trabajo["filas"][str(i)], n_avisos[i]):
            return i
    return None


# --------------------------------------------------------------- exportar
COMBINADA = "Descripción combinada"
FILA_LG = "Fila LG"


def _texto_celda(v) -> str:
    """Valor de una celda como texto (para juntar varios con « | »)."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return ""
    if isinstance(v, (pd.Timestamp, dt.datetime)):
        return v.strftime("%d/%m/%Y") if v.time() == dt.time(0) else v.strftime("%d/%m/%Y %H:%M")
    if isinstance(v, dt.date):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, dt.time):
        return v.strftime("%H:%M")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def columnas_disponibles(lg_original: pd.DataFrame, pcz_original: pd.DataFrame) -> list[str]:
    """Columnas que se pueden elegir para la hoja Asociaciones."""
    return ([f"LG · {c}" for c in lg_original.columns] + [f"PCZ · {c}" for c in pcz_original.columns]
            + [COMBINADA, FILA_LG])


def columnas_por_defecto(mapa_lg: dict, mapa_pcz: dict) -> list[str]:
    """Selección inicial: fecha, hora y texto de LG; N°, descripción de PCZ; descripción combinada."""
    salida = [f"LG · {mapa_lg[c]}" for c in ("Fecha", "Hora", "Transcripción") if c in mapa_lg]
    salida += [f"PCZ · {mapa_pcz[c]}" for c in ("N° Novedad", "Descripción") if c in mapa_pcz]
    return salida + [COMBINADA]


def tabla_asociaciones(lg_original: pd.DataFrame, pcz_original: pd.DataFrame, lg: pd.DataFrame,
                       pcz: pd.DataFrame, trabajo: dict, mapa_lg: dict, mapa_pcz: dict,
                       columnas: list[str]) -> pd.DataFrame:
    """Una fila por asociación, con las columnas elegidas en el orden elegido.

    La transcripción de LG trae solo los avisos asociados y cada columna de PCZ los valores de
    las novedades asociadas, separados por « | ».
    """
    col_texto_lg = mapa_lg["Transcripción"]
    posicion = {}
    for k, nov in enumerate(pcz["id"]):
        posicion.setdefault(nov, k)
    filas = []
    for i in range(len(lg)):
        for g in trabajo["filas"][str(i)]["grupos"]:
            avisos_ = [lg.loc[i, "avisos"][j] for j in g["avisos"] if j < len(lg.loc[i, "avisos"])]
            texto_lg = " | ".join(avisos_)
            novs = [posicion[n] for n in g["novedades"] if n in posicion]
            fila = {}
            for col in columnas:
                if col == FILA_LG:
                    fila[col] = i + 1
                elif col == COMBINADA:
                    desc = " | ".join(pcz.loc[k, "descripcion"] for k in novs)
                    fila[col] = f"{desc} {texto_lg.lower()}".strip()
                elif col.startswith("LG · "):
                    nombre = col[len("LG · "):]
                    fila[col] = texto_lg if nombre == col_texto_lg else lg_original.iloc[i][nombre]
                elif col.startswith("PCZ · "):
                    nombre = col[len("PCZ · "):]
                    fila[col] = " | ".join(_texto_celda(pcz_original.iloc[k][nombre]) for k in novs)
            filas.append(fila)
    return _fechas_sin_hora(pd.DataFrame(filas, columns=columnas))


def lg_sin_asociar(lg_original: pd.DataFrame, lg: pd.DataFrame, trabajo: dict, mapa_lg: dict) -> pd.DataFrame:
    """Filas de LG con avisos sin asociar (descartados o no revisados), con las columnas originales.

    Si parte del párrafo se asoció, la transcripción trae solo los avisos que quedaron afuera.
    """
    col_texto = mapa_lg["Transcripción"]
    filas = []
    for i in range(len(lg)):
        cubiertos = avisos_cubiertos(trabajo["filas"][str(i)]["grupos"])
        avisos_ = lg.loc[i, "avisos"]
        resto = [x for j, x in enumerate(avisos_) if j not in cubiertos]
        if not avisos_ and not cubiertos:
            filas.append(lg_original.iloc[i].copy())
        elif resto:
            fila = lg_original.iloc[i].copy()
            if cubiertos:
                fila[col_texto] = "\n".join(resto)
            filas.append(fila)
    return _fechas_sin_hora(pd.DataFrame(filas, columns=lg_original.columns))


def pcz_sin_asociar(pcz_original: pd.DataFrame, pcz: pd.DataFrame, trabajo: dict) -> pd.DataFrame:
    """Novedades de PCZ que no están en ninguna asociación, con las columnas originales."""
    asociadas = asociaciones_por_novedad(trabajo)
    quedan = [k for k, nov in enumerate(pcz["id"]) if nov not in asociadas]
    return _fechas_sin_hora(pcz_original.iloc[quedan].copy())


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


def exportar(lg_original: pd.DataFrame, pcz_original: pd.DataFrame, lg: pd.DataFrame, pcz: pd.DataFrame,
             trabajo: dict, mapa_lg: dict, mapa_pcz: dict, columnas: list[str]) -> bytes:
    """Excel con las hojas Asociaciones, LG sin asociar y PCZ sin asociar (no toca los originales)."""
    hojas = {
        "Asociaciones": tabla_asociaciones(lg_original, pcz_original, lg, pcz, trabajo, mapa_lg, mapa_pcz,
                                           columnas),
        "LG sin asociar": lg_sin_asociar(lg_original, lg, trabajo, mapa_lg),
        "PCZ sin asociar": pcz_sin_asociar(pcz_original, pcz, trabajo),
    }
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl", date_format="DD/MM/YYYY",
                        datetime_format="DD/MM/YYYY HH:MM") as w:
        for nombre, df in hojas.items():
            df.to_excel(w, sheet_name=nombre, index=False)
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
