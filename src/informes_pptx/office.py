"""Todo lo que necesita Excel o PowerPoint instalados está acá (y en ningún otro lado).

- OfficeWindows: usa PowerPoint/Excel por COM (solo Windows, con pywin32).
- OfficeSimulado: misma interfaz sin Office, para que el resto de la app funcione y se pueda
  probar en la Mac. Lo que no puede hacer, lo avisa (por ejemplo, no hay miniaturas).

obtener() elige solo. Para forzar la simulada en Windows: variable de entorno
INFORMES_OFFICE=simulado (por ejemplo en el .env).
"""
import os
import sys
from pathlib import Path


class OfficeSimulado:
    nombre = "Simulado (sin Office)"
    hace_miniaturas = False

    def __init__(self, motivo: str = ""):
        self.motivo = motivo

    def miniaturas(self, pptx: Path, carpeta: Path, ancho_px: int = 1280) -> list[Path]:
        """Sin PowerPoint no hay miniaturas: la pantalla muestra el esquema con los recuadros."""
        return []


class OfficeWindows:
    nombre = "PowerPoint de Windows"
    hace_miniaturas = True
    motivo = ""

    def miniaturas(self, pptx: Path, carpeta: Path, ancho_px: int = 1280) -> list[Path]:
        """Exporta cada diapositiva como diapositiva_NN.png con PowerPoint (sin mostrar ventanas)."""
        import pythoncom
        import win32com.client

        carpeta.mkdir(parents=True, exist_ok=True)
        for vieja in carpeta.glob("diapositiva_*.png"):
            vieja.unlink()
        pythoncom.CoInitialize()  # Streamlit corre cada pantalla en otro hilo
        try:
            app = win32com.client.Dispatch("PowerPoint.Application")
            # ReadOnly, Untitled, WithWindow=False: no toca el archivo ni abre ventana
            pres = app.Presentations.Open(str(Path(pptx).resolve()), True, False, False)
            try:
                alto_px = round(ancho_px * pres.PageSetup.SlideHeight / pres.PageSetup.SlideWidth)
                rutas = []
                for i, slide in enumerate(pres.Slides, 1):
                    ruta = carpeta / f"diapositiva_{i:02d}.png"
                    slide.Export(str(ruta.resolve()), "PNG", ancho_px, alto_px)
                    rutas.append(ruta)
            finally:
                pres.Close()
                # Cerrar PowerPoint solo si no quedó nada abierto (no cerrarle archivos al usuario)
                if app.Presentations.Count == 0:
                    app.Quit()
            return rutas
        finally:
            pythoncom.CoUninitialize()


def obtener():
    """El Office disponible en esta compu (el real en Windows, si no el simulado)."""
    if os.getenv("INFORMES_OFFICE", "").lower() == "simulado":
        return OfficeSimulado("está forzado con INFORMES_OFFICE=simulado")
    if sys.platform != "win32":
        return OfficeSimulado("esta compu no es Windows")
    try:
        import pythoncom  # noqa: F401
        import win32com.client  # noqa: F401
    except ImportError:
        return OfficeSimulado("falta instalar pywin32 (pip install -r requirements.txt)")
    return OfficeWindows()
