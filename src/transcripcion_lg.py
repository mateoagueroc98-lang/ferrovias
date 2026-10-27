"""Transcripciones del LG: del PDF escaneado del Libro de Guardia a un Excel, con la API de Claude.

El PDF se convierte en imágenes y se manda en TANDAS de 3 páginas, una tanda por vez y en orden:
cada tanda recibe como contexto la última fecha usada y el último párrafo de la anterior, así el
modelo puede seguir un párrafo que pasa de una página a otra. El modelo responde un JSON (formato
definido en el documento de instrucciones), que acá se valida y se une tanda tras tanda.

Los dos documentos de configuración (instrucciones y referencia) se guardan en
config/transcripcion_lg/, que SÍ va a git, con historial de versiones y los originales aparte.
"""
import base64
import datetime as dt
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

PAGINAS_POR_TANDA = 3
LADO_MAX_PX = 2576           # lado largo máximo que leen los modelos actuales (más no suma nitidez)
MAX_BYTES_IMAGEN = 4_500_000  # la API acepta hasta 5 MB por imagen
MAX_TOKENS_RESPUESTA = 32000
ESFUERZO = "high"            # letra manuscrita difícil: conviene que el modelo piense con calma

# ------------------------------------------------------------- configuración
CARPETA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "transcripcion_lg"
DOCUMENTOS = {
    "instrucciones": "PROMPT_Sistema_Transcripcion_LG.md",
    "referencia": "REFERENCIA_Transcripcion_LG.md",
}
FORMATO_FECHA_HISTORIAL = "%Y-%m-%d_%H-%M-%S"

# Precios en US$ por millón de tokens: entrada, salida, escritura de caché (5 min), lectura de caché.
PRECIOS = {
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.20),
    # Por si la API pasa la tanda a otro modelo (respaldo automático cuando el principal se niega).
    "claude-opus-5": (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-8": (5.0, 25.0, 6.25, 0.50),
    "claude-sonnet-5": (2.0, 10.0, 2.5, 0.20),
}
MODELOS = {
    "claude-opus-5-5": "Claude Opus 5.5 (el mejor; recomendado)",
    "claude-sonnet-5-5": "Claude Sonnet 5.5 (la mitad de precio)",
}
MODELO_DEFECTO = "claude-opus-5-5"


def tokens_aprox(texto: str) -> int:
    """Cantidad aproximada de tokens de un texto en castellano (≈ 3,5 caracteres por token)."""
    return round(len(texto) / 3.5)


def _ruta(clave: str, carpeta: Path) -> Path:
    return carpeta / DOCUMENTOS[clave]


def leer_original(clave: str, carpeta: Path = CARPETA_CONFIG) -> str:
    return (carpeta / "originales" / DOCUMENTOS[clave]).read_text(encoding="utf-8")


def leer_documento(clave: str, carpeta: Path = CARPETA_CONFIG) -> str:
    """Versión vigente del documento; si nunca se editó, el original."""
    ruta = _ruta(clave, carpeta)
    return ruta.read_text(encoding="utf-8") if ruta.exists() else leer_original(clave, carpeta)


def _limpiar(texto: str) -> str:
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def guardar_documento(clave: str, texto: str, carpeta: Path = CARPETA_CONFIG,
                      ahora: dt.datetime | None = None) -> bool:
    """Guarda la nueva versión y pasa la anterior al historial. Devuelve False si no cambió nada."""
    texto = _limpiar(texto)
    anterior = leer_documento(clave, carpeta)
    if texto == anterior:
        return False
    ahora = ahora or dt.datetime.now()
    historial = carpeta / "historial"
    historial.mkdir(parents=True, exist_ok=True)
    destino = historial / f"{ahora.strftime(FORMATO_FECHA_HISTORIAL)}_{DOCUMENTOS[clave]}"
    n = 2
    while destino.exists():  # dos guardados en el mismo segundo
        destino = historial / f"{ahora.strftime(FORMATO_FECHA_HISTORIAL)}-{n}_{DOCUMENTOS[clave]}"
        n += 1
    destino.write_text(anterior, encoding="utf-8", newline="\n")
    _ruta(clave, carpeta).write_text(texto, encoding="utf-8", newline="\n")
    return True


def historial(clave: str, carpeta: Path = CARPETA_CONFIG) -> list[tuple[dt.datetime, Path]]:
    """Versiones anteriores del documento, de la más nueva a la más vieja."""
    versiones = []
    for ruta in (carpeta / "historial").glob(f"*_{DOCUMENTOS[clave]}"):
        try:
            fecha = dt.datetime.strptime(ruta.name[:19], FORMATO_FECHA_HISTORIAL)
        except ValueError:
            continue
        versiones.append((fecha, ruta))
    return sorted(versiones, key=lambda v: (v[0], v[1].name), reverse=True)


def leer_ajustes(carpeta: Path = CARPETA_CONFIG) -> dict:
    ajustes = {"modelo": MODELO_DEFECTO}
    ruta = carpeta / "ajustes.json"
    if ruta.exists():
        try:
            ajustes.update(json.loads(ruta.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            pass
    if ajustes["modelo"] not in MODELOS:
        ajustes["modelo"] = MODELO_DEFECTO
    return ajustes


def guardar_ajustes(ajustes: dict, carpeta: Path = CARPETA_CONFIG) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "ajustes.json").write_text(json.dumps(ajustes, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- PDF → imágenes
def paginas_a_imagenes(pdf: bytes) -> list[bytes]:
    """Cada página del PDF como JPEG de hasta LADO_MAX_PX en el lado largo."""
    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument(pdf)
    imagenes = []
    try:
        for pagina in documento:
            ancho, alto = pagina.get_size()
            imagen = pagina.render(scale=LADO_MAX_PX / max(ancho, alto)).to_pil().convert("RGB")
            calidad = 85
            while True:
                buf = io.BytesIO()
                imagen.save(buf, format="JPEG", quality=calidad)
                if buf.tell() <= MAX_BYTES_IMAGEN or calidad <= 40:
                    break
                calidad -= 15
            imagenes.append(buf.getvalue())
            pagina.close()
    finally:
        documento.close()
    return imagenes


def armar_tandas(n_paginas: int) -> list[list[int]]:
    """[[0, 1, 2], [3, 4, 5], ...] con los índices de página (desde 0) de cada tanda."""
    return [list(range(i, min(i + PAGINAS_POR_TANDA, n_paginas)))
            for i in range(0, n_paginas, PAGINAS_POR_TANDA)]


# --------------------------------------------------------------- tandas y filas
@dataclass
class Tanda:
    paginas: list[int]                          # índices de página del PDF (desde 0)
    estado: str = "pendiente"                   # pendiente / ok / error
    resultado: dict | None = None               # JSON validado
    error: str = ""
    intentos: list[dict] = field(default_factory=list)  # {"cruda", "uso", "error", "contexto"}

    @property
    def nombre(self) -> str:
        a, b = self.paginas[0] + 1, self.paginas[-1] + 1
        return f"págs. {a}-{b}" if a != b else f"pág. {a}"


@dataclass
class Fila:
    folio: str
    fecha: str      # DD/MM/AAAA (o el texto tal como vino, si no se entiende)
    hora: str       # HH:MM o vacía
    transcripcion: str
    tanda: int      # índice de la tanda de donde salió
    revisar: list[str] = field(default_factory=list)


class ErrorRespuesta(ValueError):
    """La respuesta del modelo no sirve (mensaje listo para mostrar). Guarda lo que vino, si vino algo."""

    def __init__(self, mensaje: str, cruda: str = "", uso: list[dict] | None = None):
        super().__init__(mensaje)
        self.cruda, self.uso = cruda, uso or []


def normalizar_fecha(texto) -> str | None:
    """'5/10/2026', '05-10-26', '05.10.2026' → '05/10/2026'. None si no se entiende."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2}|\d{4})\s*", str(texto or ""))
    if not m:
        return None
    d, mes, a = int(m[1]), int(m[2]), int(m[3])
    if a < 100:
        a += 2000
    try:
        return dt.date(a, mes, d).strftime("%d/%m/%Y")
    except ValueError:
        return None


def normalizar_hora(texto) -> str | None:
    """'6:00', '06.00', '0600', '6 hs' → '06:00'. None si no se entiende."""
    t = str(texto or "").strip().lower().removesuffix("hs").removesuffix("h").strip(" .")
    m = re.fullmatch(r"(\d{1,2})(?:\s*[:.,]\s*|\s+)?(\d{2})?", t)
    if not m:
        return None
    h, mi = int(m[1]), int(m[2] or 0)
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def validar_respuesta(cruda: str) -> dict:
    """Lee el JSON que devolvió el modelo y lo deja en limpio. Lanza ErrorRespuesta si está mal."""
    texto = cruda.strip()
    # Por si viene envuelto en ```json ... ``` o con algo de texto alrededor.
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    try:
        datos = json.loads(texto)
    except ValueError as e:
        inicio, fin = texto.find("{"), texto.rfind("}")
        if inicio < 0:
            raise ErrorRespuesta("La respuesta no es JSON.") from None
        if fin <= inicio:
            raise ErrorRespuesta(f"JSON mal formado o incompleto: {e}") from None
        try:
            datos = json.loads(texto[inicio:fin + 1])
        except ValueError as e:
            raise ErrorRespuesta(f"JSON mal formado: {e}") from None
    if not isinstance(datos, dict):
        raise ErrorRespuesta("El JSON no es un objeto { ... }.")
    filas = datos.get("filas")
    if not isinstance(filas, list):
        raise ErrorRespuesta("Falta la lista \"filas\".")
    continuacion = datos.get("continuacion_del_anterior") or ""
    if not isinstance(continuacion, str):
        raise ErrorRespuesta("\"continuacion_del_anterior\" tiene que ser texto.")
    cortado = datos.get("cortado_al_final", False)
    if not isinstance(cortado, bool):
        raise ErrorRespuesta("\"cortado_al_final\" tiene que ser true o false.")

    limpias = []
    for n, fila in enumerate(filas, 1):
        if not isinstance(fila, dict):
            raise ErrorRespuesta(f"La fila {n} no es un objeto {{ ... }}.")
        transcripcion = fila.get("transcripcion")
        if not isinstance(transcripcion, str) or not transcripcion.strip():
            raise ErrorRespuesta(f"La fila {n} no tiene \"transcripcion\".")
        revisar = []
        fecha_cruda = _texto(fila.get("fecha"))
        fecha = normalizar_fecha(fecha_cruda)
        if fecha is None:
            fecha = fecha_cruda
            revisar.append("fecha vacía" if not fecha_cruda else "fecha no reconocida")
        hora_cruda = _texto(fila.get("hora"))
        hora = normalizar_hora(hora_cruda) if hora_cruda else ""
        if hora is None:
            hora = hora_cruda
            revisar.append("hora no reconocida")
        folio = _texto(fila.get("folio")) or "folio [ilegible]"
        limpias.append({"folio": folio, "fecha": fecha, "hora": hora,
                        "transcripcion": _limpiar(transcripcion).strip(), "revisar": revisar})
    if not limpias and not continuacion.strip():
        raise ErrorRespuesta("La respuesta no trae ninguna fila ni continuación.")
    return {"continuacion_del_anterior": _limpiar(continuacion).strip(), "filas": limpias,
            "cortado_al_final": cortado}


# ------------------------------------------------------------------- folios
_FOLIO = re.compile(r"\s*folio\s+(\d+)(?:\s*-\s*(\d+))?(.*)$", re.IGNORECASE)


def _numeros_folio(folio: str) -> tuple[str, str, str] | None:
    """'folio 18-19' → ('18', '19', ''); 'folio 01 (libro nuevo)' → ('01', '01', ' (libro nuevo)')."""
    m = _FOLIO.match(folio or "")
    if not m:
        return None
    return m[1], m[2] or m[1], m[3]


def extender_folio(folio: str, siguiente: str) -> str:
    """El párrafo de `folio` sigue en la página `siguiente`: 'folio 18' + 'folio 19' → 'folio 18-19'."""
    a, b = _numeros_folio(folio), _numeros_folio(siguiente)
    if a is None or b is None or b[0] == a[1]:
        return folio
    inicio, _, resto_a = a
    nuevo, _, resto_b = b
    return f"folio {inicio}-{nuevo}{resto_a or resto_b}"


def folio_siguiente(folio: str) -> str:
    """'folio 18' → 'folio 19' (la página que sigue a la última del folio)."""
    n = _numeros_folio(folio)
    if n is None:
        return folio
    fin = n[1]
    return f"folio {int(fin) + 1:0{len(fin)}d}"


def numero_folio(folio: str) -> int | None:
    n = _numeros_folio(folio)
    return int(n[0]) if n else None


# ----------------------------------------------------------- unión de tandas
REVISAR_CORTADO = "quedó cortado y la tanda siguiente no trajo la continuación"
REVISAR_SIN_ANTERIOR = "continuación de un párrafo anterior que no está (tanda anterior con error)"


def unir_tandas(tandas: list[Tanda]) -> list[Fila]:
    """Junta las filas de todas las tandas resueltas, pegando las continuaciones donde van."""
    filas: list[Fila] = []
    esperaba_continuacion = False   # la tanda anterior (ok) terminó cortada
    anterior_ok = False
    for i, tanda in enumerate(tandas):
        if tanda.estado != "ok" or tanda.resultado is None:
            if esperaba_continuacion and filas:
                filas[-1].revisar.append(REVISAR_CORTADO)
            esperaba_continuacion = anterior_ok = False
            continue
        r = tanda.resultado
        nuevas = [Fila(f["folio"], f["fecha"], f["hora"], f["transcripcion"], i, list(f["revisar"]))
                  for f in r["filas"]]
        continuacion = r["continuacion_del_anterior"]
        if continuacion:
            if anterior_ok and filas:
                ultima = filas[-1]
                ultima.transcripcion = f"{ultima.transcripcion} {continuacion}".strip()
                siguiente = nuevas[0].folio if nuevas else folio_siguiente(ultima.folio)
                ultima.folio = extender_folio(ultima.folio, siguiente)
            else:
                fecha = next((f.fecha for f in reversed(filas) if normalizar_fecha(f.fecha)), "")
                folio = nuevas[0].folio if nuevas else "folio [ilegible]"
                filas.append(Fila(folio, fecha, "", continuacion, i, [REVISAR_SIN_ANTERIOR]))
        elif esperaba_continuacion and filas:
            filas[-1].revisar.append(REVISAR_CORTADO)
        filas.extend(nuevas)
        esperaba_continuacion = r["cortado_al_final"]
        anterior_ok = True
    if esperaba_continuacion and filas:
        filas[-1].revisar.append("quedó cortado al final del PDF")
    return filas


def contexto_para(tandas: list[Tanda], i: int, fecha_contexto: str = "") -> dict:
    """Lo que la tanda i necesita saber de las anteriores: última fecha y último párrafo."""
    filas = unir_tandas(tandas[:i])
    fecha = next((f.fecha for f in reversed(filas) if normalizar_fecha(f.fecha)), "") or fecha_contexto
    anterior = tandas[i - 1] if i > 0 else None
    ultimo = ""
    cortado = False
    if anterior is not None and anterior.estado == "ok" and filas:
        ultimo = filas[-1].transcripcion
        cortado = bool(anterior.resultado and anterior.resultado["cortado_al_final"])
    return {"ultima_fecha": fecha, "ultimo_parrafo": ultimo, "anterior_cortado": cortado}


def mensaje_usuario(imagenes: list[bytes], paginas: list[int], contexto: dict) -> list[dict]:
    """Contenido del mensaje para una tanda: las imágenes y el contexto de continuidad."""
    contenido = []
    for n, imagen in zip(paginas, imagenes):
        contenido.append({"type": "text", "text": f"Página {n + 1} del PDF:"})
        contenido.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg",
            "data": base64.standard_b64encode(imagen).decode()}})
    partes = ["Contexto de continuidad:"]
    fecha = contexto["ultima_fecha"]
    partes.append(f"- Fecha de contexto (última fecha usada): {fecha}" if fecha
                  else "- Fecha de contexto: no hay (usá la que se vea en las páginas).")
    if contexto["ultimo_parrafo"]:
        partes.append("- Último párrafo de la tanda anterior:\n<<<\n" + contexto["ultimo_parrafo"] + "\n>>>")
        if contexto["anterior_cortado"]:
            partes.append("- Ese párrafo quedó cortado al final de la tanda anterior: es probable que "
                          "la primera página empiece con su continuación.")
    else:
        partes.append("- No hay párrafo anterior: esta es la primera tanda (o la anterior falló).")
    partes.append(f"\nTranscribí estas {len(paginas)} página(s). Devolvé solo el JSON.")
    contenido.append({"type": "text", "text": "\n".join(partes)})
    return contenido


def system_prompt(instrucciones: str, referencia: str) -> list[dict]:
    """Instrucciones + referencia. La referencia lleva caché: de la 2.ª tanda en adelante sale ~10 %."""
    return [
        {"type": "text", "text": instrucciones},
        {"type": "text", "text": "REFERENCIA_Transcripcion_LG (documento de referencia):\n\n" + referencia,
         "cache_control": {"type": "ephemeral"}},
    ]


# --------------------------------------------------------------- API de Claude
def llamar_api(client, modelo: str, system: list[dict], contenido: list[dict]) -> tuple[str, list[dict]]:
    """Una llamada a Claude. Devuelve (texto de la respuesta, uso de tokens por modelo).

    Lanza ErrorRespuesta si el modelo se negó o la respuesta quedó cortada.
    """
    with client.beta.messages.stream(
        model=modelo,
        max_tokens=MAX_TOKENS_RESPUESTA,
        output_config={"effort": ESFUERZO},
        # Si el modelo se niega, la API reintenta sola con otro modelo de respaldo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": contenido}],
    ) as stream:
        respuesta = stream.get_final_message()
    uso = _uso(respuesta)
    texto = "".join(b.text for b in respuesta.content if b.type == "text")
    if respuesta.stop_reason == "refusal":
        raise ErrorRespuesta("El modelo se negó a responder esta tanda.", texto, uso)
    if respuesta.stop_reason == "max_tokens":
        raise ErrorRespuesta("La respuesta quedó cortada (demasiado larga).", texto, uso)
    return texto, uso


def probar_conexion(client, modelo: str) -> str:
    """Comprueba clave, red y acceso al modelo sin gastar crédito. Devuelve el nombre del modelo."""
    return client.models.retrieve(modelo).display_name


def explicar_error(e: Exception, modelo: str) -> tuple[str, bool]:
    """Error de la API → (mensaje para mostrar, si conviene frenar todas las tandas que faltan)."""
    import anthropic

    detalle = str(getattr(e, "message", "") or e)
    if isinstance(e, anthropic.AuthenticationError):
        return ("La clave de Anthropic no es válida. Revisá la línea ANTHROPIC_API_KEY del archivo .env "
                "(la clave completa, sin espacios ni comillas) y volvé a abrir la app.", True)
    if isinstance(e, anthropic.PermissionDeniedError):
        return f"La clave de Anthropic no tiene permiso para usar la API ({detalle}).", True
    if isinstance(e, anthropic.NotFoundError):
        return f"El modelo {modelo} no existe o la clave no tiene acceso. Elegí otro en ⚙️ Configuración.", True
    if isinstance(e, anthropic.BadRequestError) and "credit" in detalle.lower():
        return ("No queda crédito en la cuenta de Anthropic. Cargá más en la consola "
                "(console.anthropic.com → Billing).", True)
    if isinstance(e, anthropic.RateLimitError):
        return ("Anthropic frenó los pedidos por ser demasiados seguidos. Esperá un par de minutos y "
                "reintentá las tandas que faltan.", True)
    if isinstance(e, anthropic.APITimeoutError):
        return "Claude tardó demasiado en responder esta tanda. Probá reintentarla.", False
    if isinstance(e, anthropic.APIConnectionError):
        causa = f"{e.__cause__ or ''} {e.__context__ or ''}"
        if "CERTIFICATE_VERIFY_FAILED" in causa or "certificate" in causa.lower():
            return ("No se pudo conectar con api.anthropic.com: la red revisa las conexiones seguras "
                    "(problema de certificado). En la red de la empresa hay que pedirle a Sistemas que "
                    "habilite api.anthropic.com.", True)
        return ("No se pudo conectar con api.anthropic.com. Revisá que haya internet; si en el trabajo "
                "anda internet pero esto no, puede que la red de la empresa lo bloquee: hay que pedirle "
                "a Sistemas que habilite api.anthropic.com.", True)
    if isinstance(e, anthropic.APIStatusError) and e.status_code >= 500:
        return "Los servidores de Anthropic tuvieron un problema. Probá reintentar la tanda en un rato.", False
    return f"Error de la API: {detalle}", False


def _uso(respuesta) -> list[dict]:
    u = respuesta.usage
    partes = getattr(u, "iterations", None) or [u]
    return [{
        "modelo": getattr(p, "model", None) or respuesta.model,
        "entrada": p.input_tokens or 0,
        "salida": p.output_tokens or 0,
        "cache_escritura": getattr(p, "cache_creation_input_tokens", 0) or 0,
        "cache_lectura": getattr(p, "cache_read_input_tokens", 0) or 0,
    } for p in partes]


def procesar_tanda(tanda: Tanda, llamar, system: list[dict], contenido: list[dict],
                   contexto: dict) -> Tanda:
    """Llama al modelo y valida. Si el JSON viene mal, reintenta una vez; si falla otra vez, error.

    llamar(system, contenido) -> (texto, uso). Los errores de conexión o de la API (que no sean
    de la respuesta) no se reintentan acá: el SDK ya reintenta solo y suben tal cual.
    """
    tanda.estado, tanda.resultado, tanda.error = "pendiente", None, ""
    for _ in range(2):
        try:
            cruda, uso = llamar(system, contenido)
        except ErrorRespuesta as e:
            tanda.intentos.append({"cruda": e.cruda, "uso": e.uso, "error": str(e), "contexto": contexto})
            tanda.error = str(e)
            continue
        try:
            resultado = validar_respuesta(cruda)
        except ErrorRespuesta as e:
            tanda.intentos.append({"cruda": cruda, "uso": uso, "error": str(e), "contexto": contexto})
            tanda.error = str(e)
            continue
        tanda.intentos.append({"cruda": cruda, "uso": uso, "error": "", "contexto": contexto})
        tanda.estado, tanda.resultado, tanda.error = "ok", resultado, ""
        return tanda
    tanda.estado = "error"
    return tanda


# ------------------------------------------------------------- costo y tokens
def costo(uso: list[dict]) -> float:
    """Costo en US$ de una lista de usos (los modelos sin precio cargado se cuentan como Opus 5.5)."""
    total = 0.0
    for u in uso:
        entrada, salida, escritura, lectura = PRECIOS.get(u["modelo"], PRECIOS[MODELO_DEFECTO])
        total += (u["entrada"] * entrada + u["salida"] * salida
                  + u["cache_escritura"] * escritura + u["cache_lectura"] * lectura) / 1_000_000
    return total


def uso_total(tandas: list[Tanda]) -> dict:
    """Tokens y costo de toda la sesión (incluye intentos fallidos y reintentos)."""
    usos = [u for t in tandas for i in t.intentos for u in i["uso"]]
    return {
        "llamadas": sum(1 for t in tandas for _ in t.intentos),
        "entrada": sum(u["entrada"] + u["cache_escritura"] + u["cache_lectura"] for u in usos),
        "salida": sum(u["salida"] for u in usos),
        "costo": costo(usos),
    }


TOKENS_POR_PAGINA = 4800   # imagen de 2576 px de lado largo (tope de tokens por imagen)
SALIDA_POR_PAGINA = 3000   # transcripción + razonamiento del modelo, a ojo


def estimar_costo(n_paginas: int, tokens_documentos: int, modelo: str) -> float:
    """Estimación ANTES de empezar (a ojo; el costo real se muestra al terminar)."""
    n_tandas = len(armar_tandas(n_paginas))
    uso = [{"modelo": modelo, "entrada": n_paginas * (TOKENS_POR_PAGINA + 20) + n_tandas * 300,
            "salida": n_paginas * SALIDA_POR_PAGINA,
            "cache_escritura": tokens_documentos,
            "cache_lectura": tokens_documentos * max(n_tandas - 1, 0)}]
    return costo(uso)


# --------------------------------------------------------------- exportación
COLUMNAS = ["Folio", "Fecha", "Hora", "Transcripción"]
MAX_CELDA = 32767


def resumen(filas: list[Fila], tandas: list[Tanda]) -> dict:
    textos = [f.transcripcion for f in filas]
    return {
        "filas": len(filas),
        "dudosos": sum(t.count("[?]") for t in textos),
        "ilegibles": sum(t.lower().count("[ilegible]") for t in textos),
        "tandas_error": [t.nombre for t in tandas if t.estado == "error"],
        "tandas_pendientes": [t.nombre for t in tandas if t.estado == "pendiente"],
        "para_revisar": sum(1 for f in filas if f.revisar),
    }


def nombre_archivo(filas: list[dict]) -> str:
    """LG_transcripcion_<fecha primera fila>_<fecha última fila>.xlsx (fechas con guiones)."""
    fechas = [normalizar_fecha(f["Fecha"]) for f in filas]
    fechas = [f.replace("/", "-") for f in fechas if f]
    if not fechas:
        return "LG_transcripcion.xlsx"
    return f"LG_transcripcion_{fechas[0]}_{fechas[-1]}.xlsx"


def exportar_excel(filas: list[dict]) -> bytes:
    """Una hoja con Folio | Fecha | Hora | Transcripción. filas: dicts con esas 4 claves."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Transcripción"
    ws.append(COLUMNAS)
    for celda in ws[1]:
        celda.font = Font(bold=True)
    arriba = Alignment(vertical="top")
    ajustar = Alignment(vertical="top", wrap_text=True)
    for f in filas:
        fecha_txt = normalizar_fecha(f["Fecha"])
        fecha = dt.datetime.strptime(fecha_txt, "%d/%m/%Y").date() if fecha_txt else (_texto(f["Fecha"]) or None)
        hora_txt = normalizar_hora(f["Hora"]) if _texto(f["Hora"]) else None
        hora = dt.time(*map(int, hora_txt.split(":"))) if hora_txt else (_texto(f["Hora"]) or None)
        texto = _limpiar(_texto(f["Transcripción"]))[:MAX_CELDA]
        ws.append([_texto(f["Folio"]), fecha, hora, texto])
        fila = ws.max_row
        ws.cell(fila, 1).alignment = arriba
        ws.cell(fila, 2).alignment = arriba
        ws.cell(fila, 3).alignment = arriba
        ws.cell(fila, 4).alignment = ajustar
        if isinstance(fecha, dt.date):
            ws.cell(fila, 2).number_format = "DD/MM/YYYY"
        if isinstance(hora, dt.time):
            ws.cell(fila, 3).number_format = "HH:MM"
    for col, ancho in zip(range(1, 5), (22, 12, 8, 100)):
        ws.column_dimensions[get_column_letter(col)].width = ancho
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
