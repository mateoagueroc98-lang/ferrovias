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
from openpyxl.styles import Alignment, PatternFill

# ------------------------------------------------------------------ columnas
# Nombre canónico -> función que reconoce el encabezado ya normalizado (sin tildes, minúsculas,
# solo letras y números). No es búsqueda aproximada: son reglas fijas. Si hay varias reglas (tupla),
# se prueban en orden: la segunda solo se usa si ninguna columna cumple la primera.
COLUMNAS_LG = {
    "Fecha": lambda c: c == "fecha",
    "Transcripción": lambda c: c == "transcripcion",
    "Hora": lambda c: c.startswith("hora"),
    # Solo se copia al Excel final (a la izquierda de «Descripción»)
    "Página": lambda c: c.startswith("pagina") or c in ("pag", "pg"),
}
EXTRAS_LG = ("Página",)
COLUMNAS_PCZ = {
    "Fecha": lambda c: c == "fecha",
    "Descripción": lambda c: c == "descripcion",
    # "N° Novedad", "Nº Novedad", "N Novedad", "Nro. Novedad", "Número de novedad"...
    "N° Novedad": lambda c: re.fullmatch(r"(n|no|nro|num|numero)?(de)?novedad", c) is not None,
    # Sin columna «Hora…», la hora se toma de «Comienzo de falla» (fecha y hora)
    "Hora": (lambda c: c.startswith("hora"), lambda c: c.startswith("comienzo")),
    # Columnas que solo se copian al Excel final (después de «Descripción»)
    "Zona": lambda c: c == "zona",
    "VER": lambda c: c == "ver",
    "Falla": lambda c: c == "falla",
    "Comienzo de falla": lambda c: c.startswith("comienzo"),
    "Habilitación": lambda c: c.startswith("habilitacion"),
}
EXTRAS_PCZ = ("Zona", "VER", "Falla", "Comienzo de falla", "Habilitación")


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
    for canon, reglas in esperadas.items():
        reglas = reglas if isinstance(reglas, tuple) else (reglas,)
        real = next((c for regla in reglas for c in df.columns if regla(_clave_encabezado(c))), None)
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
    # Fecha y hora en texto ("04/03/2025 14:50", "2025-03-04 14:50:00"): se usa solo la hora
    texto = re.sub(r"^\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}[\sT]+", "", texto)
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
OPCIONALES_PCZ = ("N° Novedad", "Hora") + EXTRAS_PCZ


def preparar_pcz(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Tabla de trabajo de PCZ: id, descripción, fecha y hora normalizadas, más las columnas de
    EXTRAS_PCZ tal como vienen (vacías si el archivo no las tiene).

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
    for nombre in EXTRAS_PCZ:
        t[nombre] = (df[mapa[nombre]].astype(object) if nombre in mapa
                     else pd.Series([None] * len(df), index=df.index, dtype=object))
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
# La novedad de PCZ es la principal: los candidatos son los avisos (renglones) del LG.
def tabla_avisos(lg: pd.DataFrame) -> pd.DataFrame:
    """Una fila por aviso del LG: fila de LG, n° de aviso, texto, fecha y hora de su párrafo."""
    filas = [{"clave": f"{i}:{j}", "fila_lg": i, "aviso": j, "texto": texto,
              "fecha": lg.loc[i, "fecha"], "hora": lg.loc[i, "hora"]}
             for i in lg.index for j, texto in enumerate(lg.loc[i, "avisos"])]
    t = pd.DataFrame(filas, columns=["clave", "fila_lg", "aviso", "texto", "fecha", "hora"])
    t["hora"] = t["hora"].astype(object)
    return t


def filtrar_por_fecha(tabla: pd.DataFrame, fecha, vecinos: bool = False) -> pd.DataFrame:
    """Filas con la MISMA fecha (y, si vecinos=True, del día anterior/siguiente).

    `fecha` puede ser una fecha o varias (novedades unidas de distintos días).
    Agrega la columna "otro_dia" (True para las del día anterior/siguiente).
    Sin fecha válida no hay candidatos por fecha.
    """
    base = {f for f in (fecha if isinstance(fecha, (list, tuple, set)) else [fecha]) if f is not None}
    if not base:
        return tabla.iloc[0:0].assign(otro_dia=pd.Series(dtype=bool))
    dias = set(base)
    if vecinos:
        dias |= {f + dt.timedelta(days=d) for f in base for d in (-1, 1)}
    sel = tabla[tabla["fecha"].isin(dias)].copy()
    sel["otro_dia"] = ~sel["fecha"].isin(base)
    return sel


def _horas(hora) -> list[int]:
    if isinstance(hora, (list, tuple)):
        return [int(h) for h in hora if h is not None and not pd.isna(h)]
    return [int(hora)] if hora is not None and not pd.isna(hora) else []


def novedad_combinada(pcz: pd.DataFrame, posiciones: list[int]) -> pd.Series:
    """Varias novedades de PCZ unidas en una sola (para buscar sus avisos del LG juntos)."""
    sel = pcz.iloc[list(posiciones)]
    fechas = [f for f in sel["fecha"] if f is not None and not pd.isna(f)]
    return pd.Series({"fecha": fechas[0] if fechas else None, "fechas": sorted(set(fechas)),
                      "descripcion": " ".join(sel["descripcion"]),
                      "hora": [h for h in sel["hora"] if h is not None and not pd.isna(h)]})


def puntuar(novedad: pd.Series, sel: pd.DataFrame) -> pd.DataFrame:
    """Agrega puntaje, detalle y coincidencias a cada aviso de `sel` (debe tener "otro_dia")."""
    sel = sel.copy()
    resultados = [
        similitud(texto, _horas(hora) + [h for _, _, h in horas_en_texto(texto)],
                  novedad["descripcion"], _horas(novedad["hora"]))
        for texto, hora in zip(sel["texto"], sel["hora"])
    ]
    sel["puntaje"] = [r["puntaje"] for r in resultados]
    sel["detalle"] = [r["detalle"] for r in resultados]
    sel["comunes"] = [r["comunes"] for r in resultados]
    sel["hora_suma"] = [r["dif_hora"] is not None and puntos_hora(r["dif_hora"]) > 0 for r in resultados]
    return sel.sort_values(["otro_dia", "puntaje", "fila_lg", "aviso"], ascending=[True, False, True, True])


def candidatos(novedad: pd.Series, avisos_lg: pd.DataFrame, vecinos: bool = False) -> pd.DataFrame:
    """Avisos del LG candidatos: primero los de la misma fecha (o fechas, si se unieron novedades de
    distintos días), de mayor a menor puntaje."""
    return puntuar(novedad, filtrar_por_fecha(avisos_lg, novedad.get("fechas") or novedad["fecha"], vecinos))


def avisos_sin_fecha(novedad: pd.Series, avisos_lg: pd.DataFrame) -> pd.DataFrame:
    """Avisos del LG cuya fecha no se pudo interpretar (pueden ser de cualquier día)."""
    return puntuar(novedad, avisos_lg[avisos_lg["fecha"].isna()].assign(otro_dia=True))


def todos_los_avisos(novedad: pd.Series, avisos_lg: pd.DataFrame) -> pd.DataFrame:
    """Todos los avisos puntuados (para novedades de PCZ sin fecha válida)."""
    return puntuar(novedad, avisos_lg.assign(otro_dia=True))


def buscar(cands: pd.DataFrame, texto: str) -> pd.DataFrame:
    """Filtra avisos que contengan todas las palabras buscadas (sin tildes/mayúsculas)."""
    palabras = sin_tildes(texto).split()
    if not palabras:
        return cands
    base = cands["texto"].map(sin_tildes)
    return cands[base.map(lambda b: all(p in b for p in palabras))]


# ------------------------------------------- unir novedades de distintos días
_SIN_EXCLUIR = object()


def novedades_para_unir(pcz: pd.DataFrame, trabajo: dict, elegidas: list[int], excluir_dia=_SIN_EXCLUIR,
                        dia=None, texto: str = "") -> pd.DataFrame:
    """Novedades de PCZ que se pueden unir a las `elegidas` (de otro día y todavía sin asociar),
    filtradas por día y por palabras (opcionales), ordenadas por parecido con las elegidas.
    excluir_dia: el día que se está recorriendo (None = el grupo de fechas no reconocidas)."""
    asociadas = asociacion_de(trabajo)
    t = pcz.assign(pos=range(len(pcz)))
    t = t[~t["pos"].isin(elegidas) & ~t["pos"].isin(asociadas)]
    if excluir_dia is None:
        t = t[t["fecha"].notna()]
    elif excluir_dia is not _SIN_EXCLUIR:
        t = t[t["fecha"] != excluir_dia]
    if dia is not None:
        t = t[t["fecha"] == dia]
    if palabras := sin_tildes(texto).split():
        t = t[t["descripcion"].map(sin_tildes).map(lambda d: all(p in d for p in palabras))]
    base = novedad_combinada(pcz, elegidas)
    t = t.copy()
    t["puntaje"] = [similitud(d, _horas(h), base["descripcion"], _horas(base["hora"]))["puntaje"]
                    for d, h in zip(t["descripcion"], t["hora"])]
    t["_sin_fecha"] = t["fecha"].isna()
    return t.sort_values(["puntaje", "_sin_fecha", "pos"], ascending=[False, True, True]).drop(columns="_sin_fecha")


# Columnas de PCZ en las que, al unir novedades de distintos días, se elige qué valor(es) van al Excel
ELEGIBLES_UNION = ("Comienzo de falla", "Habilitación")


def valores_union(pcz: pd.DataFrame, posiciones: list[int], nombre: str) -> list[tuple]:
    """Valores distintos (no vacíos) de una columna de PCZ entre novedades unidas, por fecha:
    [(valor, [N° de las novedades que lo tienen])]."""
    salida: dict[str, tuple] = {}
    for k in sorted(posiciones, key=lambda k: (pcz.loc[k, "fecha"] is None, pcz.loc[k, "fecha"] or dt.date.min, k)):
        v = pcz.loc[k, nombre]
        if texto := _texto_celda(v):
            salida.setdefault(texto, (v, []))[1].append(pcz.loc[k, "id"])
    return list(salida.values())


def opciones_union(pcz: pd.DataFrame, posiciones: list[int]) -> tuple[list, list[str]]:
    """Para novedades unidas: fechas distintas (para elegir una) y opciones de N° Novedad (cada uno
    solo, o todos juntos con « | »)."""
    # Por fecha (las sin fecha al final) y, dentro del día, en el orden del PCZ
    novs = sorted(posiciones, key=lambda k: (pcz.loc[k, "fecha"] is None, pcz.loc[k, "fecha"] or dt.date.min, k))
    fechas = sorted({pcz.loc[k, "fecha"] for k in novs if pcz.loc[k, "fecha"] is not None})
    ids = list(dict.fromkeys(pcz.loc[k, "id"] for k in novs))
    return fechas, ids + ([" | ".join(ids)] if len(ids) > 1 else [])


# ----------------------------------------------- estado del trabajo (en memoria)
def huella(*contenidos: bytes) -> str:
    """Identifica un archivo (o un par de archivos) para saber si se cargó otro."""
    h = hashlib.sha1()
    for c in contenidos:
        h.update(hashlib.sha1(c).digest())
    return h.hexdigest()[:16]


def dias_pcz(pcz: pd.DataFrame) -> list:
    """Días a recorrer (todas las fechas de PCZ, en orden); al final None si hay fechas inválidas."""
    dias = sorted({f for f in pcz["fecha"] if f is not None and not pd.isna(f)})
    return dias + ([None] if pcz["fecha"].isna().any() else [])


def novedades_del_dia(pcz: pd.DataFrame, dia) -> list[int]:
    """Posiciones de las novedades de PCZ de ese día (dia=None: las de fecha inválida)."""
    if dia is None:
        return [k for k, f in enumerate(pcz["fecha"]) if f is None or pd.isna(f)]
    return [k for k, f in enumerate(pcz["fecha"]) if f == dia]


def trabajo_nuevo(huella_archivos: str) -> dict:
    """Estado del trabajo de asociación. Vive solo en memoria mientras la app está abierta.

    asociaciones: [{"novedades": [posición en PCZ], "avisos": ["fila:aviso" del LG]}]
    descartadas: novedades de PCZ sin aviso en el LG.
    marcas: {posición en PCZ: "amarilla" | "naranja"}, para resaltar su fila en el Excel final.
    """
    return {"huella": huella_archivos, "dia": 0, "asociaciones": [], "descartadas": [], "marcas": {}}


def asociar(trabajo: dict, novedades, avisos_lg, fecha=None, numero: str | None = None,
            extras: dict | None = None) -> None:
    """fecha / numero / extras: lo elegido para el Excel cuando se unen novedades de distintos días
    (si no se dan, se usan la fecha de la primera novedad, todos los N° juntos y todos los valores).
    extras: {columna de EXTRAS_PCZ: [valores elegidos]} (p. ej. qué «Comienzo de falla» va)."""
    g = {"novedades": sorted(set(novedades)), "avisos": list(dict.fromkeys(avisos_lg))}
    if fecha is not None:
        g["fecha"] = fecha
    if numero:
        g["numero"] = numero
    if extras:
        g["extras"] = extras
    trabajo["asociaciones"].append(g)
    trabajo["descartadas"] = [k for k in trabajo["descartadas"] if k not in set(novedades)]
    unificar_marcas(trabajo, novedades)


def descartar(trabajo: dict, novedades) -> None:
    trabajo["descartadas"] = sorted(set(trabajo["descartadas"]) | set(novedades))


def quitar_asociacion(trabajo: dict, i: int) -> None:
    del trabajo["asociaciones"][i]


def recuperar(trabajo: dict, novedad: int) -> None:
    trabajo["descartadas"] = [k for k in trabajo["descartadas"] if k != novedad]


# Marcas: resaltan en el Excel final la fila donde termina la novedad (en «Asociaciones» si está
# asociada o no). La naranja pesa más que la amarilla.
COLORES_MARCA = {"amarilla": "FFFF00", "naranja": "FFC000"}


def marcar(trabajo: dict, novedad: int, color: str, juntas=()) -> None:
    """Pone la marca de ese color; si ya la tenía, la saca.

    `juntas` son las novedades unidas con ella (asociadas o tildadas juntas): todas quedan igual.
    """
    marcas = trabajo.setdefault("marcas", {})
    sacar = marcas.get(novedad) == color
    for k in {novedad, *juntas}:
        if sacar:
            marcas.pop(k, None)
        else:
            marcas[k] = color


def unificar_marcas(trabajo: dict, novedades) -> None:
    """Novedades unidas en una asociación: todas toman la marca de la fila (la naranja gana)."""
    if color := marca(trabajo, novedades):
        for k in novedades:
            trabajo["marcas"][k] = color


def marca(trabajo: dict, novedades) -> str | None:
    """Marca de una fila con estas novedades: naranja si alguna es naranja, si no amarilla, si no None."""
    colores = {trabajo.get("marcas", {}).get(k) for k in novedades}
    return next((c for c in ("naranja", "amarilla") if c in colores), None)


def asociacion_de(trabajo: dict) -> dict[int, int]:
    """Novedad de PCZ (posición) -> índice de la asociación en la que está."""
    return {k: i for i, g in enumerate(trabajo["asociaciones"]) for k in g["novedades"]}


def estado(trabajo: dict, novedad: int) -> str:
    if novedad in asociacion_de(trabajo):
        return "asociada"
    return "descartada" if novedad in trabajo["descartadas"] else "pendiente"


def novedades_por_aviso(trabajo: dict) -> dict[str, list[int]]:
    """Clave de aviso ("fila:aviso") -> novedades de PCZ (posición) a las que está asociado."""
    salida: dict[str, list[int]] = {}
    for g in trabajo["asociaciones"]:
        for clave in g["avisos"]:
            salida.setdefault(clave, []).extend(g["novedades"])
    return salida


def progreso(trabajo: dict, n_pcz: int) -> dict:
    asociadas = set(asociacion_de(trabajo))
    descartadas = set(trabajo["descartadas"]) - asociadas
    return {"total": n_pcz, "asociadas": len(asociadas), "descartadas": len(descartadas),
            "pendientes": n_pcz - len(asociadas) - len(descartadas)}


def pendientes(trabajo: dict, novedades: list[int]) -> list[int]:
    hechas = set(asociacion_de(trabajo)) | set(trabajo["descartadas"])
    return [k for k in novedades if k not in hechas]


# --------------------------------------------------------------- exportar
# Hoja «Asociaciones»: estructura fija, igual a la tabla madre del usuario (para copiar y pegar a
# continuación). Las columnas vacías se completan después a mano.
COLUMNAS_SALIDA = {
    "N°": "Número consecutivo: arranca en el número que elijas y sube de a uno.",
    "ID": None,
    "Fecha": "Fecha de la novedad de PCZ (formato 19/9/2026).",
    "Mes": None,
    "N° Novedad": "Número de la novedad de PCZ (si se unieron varias: «1001 | 1002»).",
    "Sistema": None,
    "Subsistema": None,
    "Parte": None,
    "Elemento": None,
    "Nombre correcto": None,
    "Km. INPAN": None,
    "BuscarV (Km. INPAN)": None,
    "Modelo": None,
    "Página": "Página del LG de los avisos asociados (si son de varias: «12 | 13»).",
    "Descripción": "Texto de PCZ en MAYÚSCULAS, un renglón vacío y abajo el texto del LG tal como viene.",
    # De PCZ, tal como vienen (si se unieron varias novedades: valores distintos con « | »)
    **{nombre: f"Columna «{nombre}» de PCZ." for nombre in EXTRAS_PCZ},
}
FORMATO_FECHA = "d/m/yyyy"


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


def texto_descripcion(textos_pcz: list[str], textos_lg: list[str]) -> str:
    """Celda «Descripción»: textos de PCZ en mayúsculas, un renglón vacío y los textos del LG (si hay)."""
    pcz = "\n".join(t.upper() for t in textos_pcz)
    return pcz + "\n\n" + "\n".join(textos_lg) if textos_lg else pcz


def _claves(avisos_lg) -> list[tuple[int, int]]:
    return [tuple(int(x) for x in c.split(":")) for c in avisos_lg]


def _juntar(valores) -> str:
    """Valores como texto, sin repetir, separados por « | »."""
    return " | ".join(dict.fromkeys(v for v in (_texto_celda(x) for x in valores) if v))


def _en_orden(pcz: pd.DataFrame, trabajo: dict) -> list[dict]:
    """Filas de la hoja «Asociaciones»: cada asociación y cada novedad de PCZ sin asociar (sola y sin
    avisos), ordenadas por día y, dentro del día, en el orden del PCZ. Sin fecha reconocida, al final."""
    asociadas = asociacion_de(trabajo)
    grupos = list(trabajo["asociaciones"]) + [{"novedades": [k], "avisos": []}
                                              for k in range(len(pcz)) if k not in asociadas]

    def orden(g):
        fechas = [g["fecha"]] if g.get("fecha") else \
            [pcz.loc[k, "fecha"] for k in g["novedades"] if pcz.loc[k, "fecha"] is not None]
        return (not fechas, min(fechas) if fechas else dt.date.min, min(g["novedades"]), g["novedades"])
    return sorted(grupos, key=orden)


def tabla_asociaciones(lg: pd.DataFrame, pcz: pd.DataFrame, trabajo: dict, numero_inicial: int = 1) -> pd.DataFrame:
    """Hoja «Asociaciones»: una fila por asociación y una por cada novedad de PCZ sin asociar
    (descartada o sin revisar), con la estructura fija de COLUMNAS_SALIDA, ordenadas por día.

    Si una asociación une varias novedades, sus N° se juntan con « | ». Las columnas sin dato
    quedan vacías.
    """
    filas = []
    for n, g in enumerate(_en_orden(pcz, trabajo)):
        novs = list(g["novedades"])
        claves = [(i, j) for i, j in _claves(g["avisos"]) if i in lg.index and j < len(lg.loc[i, "avisos"])]
        fechas = [pcz.loc[k, "fecha"] for k in novs if pcz.loc[k, "fecha"] is not None]
        ids = [pcz.loc[k, "id"] for k in novs]
        fila = dict.fromkeys(COLUMNAS_SALIDA, None)
        fila["N°"] = numero_inicial + n
        fila["Fecha"] = g.get("fecha") or (fechas[0] if fechas else _juntar(pcz.loc[k, "fecha_original"] for k in novs))
        numero = g.get("numero") or " | ".join(ids)
        fila["N° Novedad"] = int(numero) if numero.isdigit() else numero
        fila["Descripción"] = texto_descripcion([pcz.loc[k, "descripcion"] for k in novs],
                                                [lg.loc[i, "avisos"][j] for i, j in claves])
        paginas = list(dict.fromkeys(p for p in (lg.loc[i, "pagina"] for i, _ in claves) if p))
        if len(paginas) == 1:
            fila["Página"] = int(paginas[0]) if paginas[0].isdigit() else paginas[0]
        elif paginas:
            fila["Página"] = " | ".join(paginas)
        for nombre in EXTRAS_PCZ:
            valores = g["extras"][nombre] if nombre in g.get("extras", {}) else \
                [v for v in (pcz.loc[k, nombre] for k in novs) if _texto_celda(v)]
            fila[nombre] = (_sin_hora(valores[0]) if len({_texto_celda(v) for v in valores}) == 1
                            else _juntar(valores) or None)
        filas.append(fila)
    return pd.DataFrame(filas, columns=list(COLUMNAS_SALIDA))


def lg_sin_asociar(lg_original: pd.DataFrame, lg: pd.DataFrame, trabajo: dict, mapa_lg: dict) -> pd.DataFrame:
    """Filas de LG con avisos que no quedaron en ninguna asociación, con las columnas originales.

    Si parte del párrafo se asoció, la transcripción trae solo los avisos que quedaron afuera.
    """
    usados = set(_claves(novedades_por_aviso(trabajo)))
    col_texto = mapa_lg["Transcripción"]
    filas = []
    for i in range(len(lg)):
        avisos_ = lg.loc[i, "avisos"]
        resto = [x for j, x in enumerate(avisos_) if (i, j) not in usados]
        if not avisos_:
            filas.append(lg_original.iloc[i].copy())
        elif resto:
            fila = lg_original.iloc[i].copy()
            if len(resto) < len(avisos_):
                fila[col_texto] = "\n".join(resto)
            filas.append(fila)
    return _fechas_sin_hora(pd.DataFrame(filas, columns=lg_original.columns))


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


def exportar(lg_original: pd.DataFrame, lg: pd.DataFrame, pcz: pd.DataFrame, trabajo: dict, mapa_lg: dict, numero_inicial: int = 1) -> bytes:
    """Excel con las hojas Asociaciones y LG sin asociar (no toca los originales)."""
    hojas = {
        "Asociaciones": tabla_asociaciones(lg, pcz, trabajo, numero_inicial),
        "LG sin asociar": lg_sin_asociar(lg_original, lg, trabajo, mapa_lg),
    }
    # Color de cada fila (en el orden de la hoja) según las marcas de sus novedades
    colores = {
        "Asociaciones": [marca(trabajo, g["novedades"]) for g in _en_orden(pcz, trabajo)],
    }
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl", date_format="DD/MM/YYYY",
                        datetime_format="DD/MM/YYYY HH:MM") as w:
        for nombre, df in hojas.items():
            df.to_excel(w, sheet_name=nombre, index=False)
        for nombre, hoja in w.sheets.items():
            for fila in hoja.iter_rows(min_row=2):
                for celda in fila:
                    if isinstance(celda.value, dt.date) and (
                            not isinstance(celda.value, dt.datetime) or celda.value.time() == dt.time(0)):
                        celda.number_format = FORMATO_FECHA if nombre == "Asociaciones" else "DD/MM/YYYY"
                    elif isinstance(celda.value, dt.datetime) and nombre == "Asociaciones":
                        celda.number_format = FORMATO_FECHA + " h:mm"  # p. ej. Comienzo de falla
                    elif isinstance(celda.value, str) and "\n" in celda.value:
                        celda.alignment = Alignment(wrap_text=True, vertical="top")
            for n, color in enumerate(colores.get(nombre, []), start=2):
                if color:
                    for celda in hoja[n]:
                        celda.fill = PatternFill("solid", fgColor=COLORES_MARCA[color])
            for col in hoja.columns:
                largo = max((len(renglon) for c in col if c.value is not None
                             for renglon in str(c.value).split("\n")), default=8)
                hoja.column_dimensions[col[0].column_letter].width = min(max(largo + 2, 10), 60)
    return buffer.getvalue()
