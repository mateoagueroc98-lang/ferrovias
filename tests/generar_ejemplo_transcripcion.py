"""Genera tests/ejemplos/LG_ejemplo.pdf: un Libro de Guardia INVENTADO de 7 páginas.

Son páginas rayadas con texto inventado (no hay datos reales), para probar el módulo
Transcripciones del LG sin subir PDFs internos. Correr:  python tests/generar_ejemplo_transcripcion.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ARCHIVO = Path(__file__).parent / "ejemplos" / "LG_ejemplo.pdf"

# (folio, renglones) por página. Los párrafos de folio 31→32 y 33→34 pasan de una página a otra.
PAGINAS = [
    (29, ["01/03/2026 TURNO DE 06 A 14 HS. PEREZ - GOMEZ",
          "07:10 HS AUX. ESTACION AVISA BARRERA PAN DRAGO",
          "BRAZO ASC NO BAJA. SE CONCURRE, SE CAMBIA FUSIBLE",
          "MECANICO. NORMAL 07:55 HS C/A PCZ.-",
          "[firma: DSSN] PEREZ", "",
          "01/03/2026 TURNO DE 14 A 22 HS. LOPEZ - DIAZ",
          "15:20 HS COND. T. 3029 AVISA SEÑAL 115 A PELIGRO",
          "SE VERIFICA CV 29ET, LIGA CORTADA. SE REPONE."]),
    (30, ["NORMAL 16:40 HS C/A PCZ.-",
          "[firma: DSSN] LOPEZ", "",
          "01/03/2026 TURNO DE 22 A 06 HS. RUIZ - SOSA",
          "23:05 HS PCZ AVISA CAMBIO 12 FUERA DE CORRESPONDENCIA",
          "SE LIMPIAN AGUJAS Y SE AJUSTA DETECTORA.",
          "NORMAL 23:50 HS.-"]),
    (31, ["02:15 HS AYTE. AVISA CAMPANILLA PAN RIVADAVIA NO SUENA",
          "SE CAMBIA RELE DE CONTROL. NORMAL 03:00 HS.-",
          "[firma: DSSE] RUIZ", "",
          "02/03/2026 TURNO DE 06 A 14 HS. PEREZ - GOMEZ",
          "08:30 HS SE CONCURRE A ABRIGO H 437 POR CONSIGNA",
          "SE MIDE BANCO B12: 12,4 VCC. SE CONTROLA CARGADOR"]),
    (32, ["Y RECTIFICADOR. SIN NOVEDAD.-",
          "[firma: DSSN] PEREZ", "",
          "CONSIGNA PARA EL TURNO NOCHE: PROBAR MESA DE MANDO",
          "LOS POLVORINES. SR. JEFE", "",
          "02/03/2026 TURNO DE 14 A 22 HS. LOPEZ - DIAZ",
          "18:45 HS SIN NOVEDAD EN EL SECTOR.-"]),
    (33, ["[firma: DSSN] LOPEZ", "",
          "02/03/2026 TURNO DE 22 A 06 HS. RUIZ - SOSA",
          "22:40 HS SE PRUEBA MESA DE MANDO LOS POLVORINES",
          "SEGUN CONSIGNA. FUNCIONA CORRECTAMENTE.",
          "01:30 HS PCZ AVISA CIRCUITO OCUPADO 9BT SIN TREN"]),
    (34, ["SE CAMBIA JUNTA AISLANTE. NORMAL 02:40 HS.-",
          "[firma: DSSE] RUIZ", "",
          "03/03/2026 TURNO DE 06 A 14 HS. PEREZ - GOMEZ",
          "09:00 HS T. FIJO: SE PINTAN BRAZOS PAN BEIRO."]),
    (35, ["[firma: DSSN] PEREZ", "", "(página casi vacía)"]),
]

ANCHO, ALTO = 1240, 1754  # A4 a 150 ppp


def pagina(folio: int, renglones: list[str]) -> Image.Image:
    img = Image.new("RGB", (ANCHO, ALTO), (248, 246, 238))
    d = ImageDraw.Draw(img)
    fuente = ImageFont.load_default(size=34)
    for y in range(200, ALTO - 60, 70):  # renglones del cuaderno
        d.line([(40, y), (ANCHO - 40, y)], fill=(170, 175, 200), width=2)
    d.text((ANCHO - 140, 90), f"{folio}", fill=(30, 30, 30), font=ImageFont.load_default(size=48))
    for n, texto in enumerate(renglones):
        d.text((70, 155 + 70 * n), texto, fill=(25, 45, 140), font=fuente)  # tinta azul
    return img


def generar() -> Path:
    ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    imagenes = [pagina(f, r) for f, r in PAGINAS]
    imagenes[0].save(ARCHIVO, save_all=True, append_images=imagenes[1:], resolution=150, quality=60)
    return ARCHIVO


if __name__ == "__main__":
    print(f"Generado {generar()}")
