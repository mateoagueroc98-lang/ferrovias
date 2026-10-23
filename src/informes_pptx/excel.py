"""Motor de Excel: capturas de rangos y gráficos, y valores de celdas, con el Excel instalado.

Todo lo que usa Excel por COM está acá (lo de PowerPoint está en office.py). Hay dos motores con la
misma interfaz:
- MotorWindows: Excel de verdad (Windows + pywin32). Abre una COPIA del archivo, en una instancia
  propia de Excel invisible (no toca otros Excel abiertos), sin actualizar vínculos externos y en
  solo lectura; actualiza las tablas dinámicas (RefreshAll) y siempre cierra sin guardar.
- MotorSimulado: sin Excel (Mac). Devuelve imágenes de relleno con el nombre de lo pedido y los
  valores guardados en el archivo, para poder probar todo.

Uso:
    with motor.abrir(contenido, "Indicadores.xlsx") as libro:
        png = libro.capturar_rango("Confiabilidad", "A5:N41").png
        png = libro.capturar_grafico("Disponib.", "Gráfico 3").png
        texto = libro.texto_celda("Carátula", "D32")
        libro.copiar_grafico("Disponib.", "Gráfico 3")  # queda en el portapapeles (etapa 3)

obtener() elige el motor. INFORMES_OFFICE=simulado fuerza el simulado también en Windows.
"""
import gc
import io
import os
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.informes_pptx import excel_zip as ez

FUENTE = Path(__file__).resolve().parents[2] / "static" / "fuentes" / "Overpass-Variable.ttf"
ESCALA = 3          # las capturas salen al triple de la resolución de pantalla (no se pixelan)
MAX_LADO_PX = 7000  # tope para rangos enormes
# Constantes de Excel
XL_SCREEN, XL_PICTURE, XL_BITMAP = 1, -4147, 2
MSO_GRUPO = 6


class ErrorMotor(RuntimeError):
    """Excel no pudo hacer algo (mensaje listo para mostrar)."""


@dataclass
class Captura:
    png: bytes
    metodo: str = ""   # cómo se hizo (para revisar qué funcionó con cada tipo de gráfico)
    avisos: list[str] = field(default_factory=list)

    @property
    def tamano(self) -> tuple[int, int]:
        return Image.open(io.BytesIO(self.png)).size


def reintentar(funcion, intentos: int = 5, espera: float = 0.3):
    """El portapapeles de Windows a veces está ocupado un instante: se reintenta con esperas."""
    for i in range(intentos):
        try:
            return funcion()
        except Exception:  # noqa: BLE001 - errores de COM y del portapapeles
            if i == intentos - 1:
                raise
            time.sleep(espera * (i + 1))


# ===================================================================== simulado
def _fuente(tamano: int):
    try:
        return ImageFont.truetype(str(FUENTE), tamano)
    except OSError:
        return ImageFont.load_default()


def imagen_relleno(titulo: str, detalle: str, ancho: int, alto: int) -> bytes:
    """Imagen de relleno con el nombre de lo pedido (lo que devuelve el motor simulado)."""
    ancho, alto = max(int(ancho), 60), max(int(alto), 40)
    img = Image.new("RGB", (ancho, alto), "#F4F3F2")
    d = ImageDraw.Draw(img)
    paso = max(min(ancho, alto) // 12, 12)
    for x in range(-alto, ancho, paso * 2):  # rayado suave, para que se note que es de mentira
        d.line([(x, alto), (x + alto, 0)], fill="#E8E6E4", width=paso // 2)
    grosor = max(min(ancho, alto) // 90, 2)
    d.rectangle([0, 0, ancho - 1, alto - 1], outline="#D41920", width=grosor)
    tam = max(min(ancho // 18, alto // 6), 10)
    for i, (texto, color, t) in enumerate([("SIMULADO", "#D41920", tam), (titulo, "#1C1A19", tam),
                                           (detalle, "#5A5552", max(tam * 2 // 3, 9))]):
        f = _fuente(t)
        caja = d.textbbox((0, 0), texto, font=f)
        y = alto / 2 + (i - 1) * tam * 1.5 - (caja[3] - caja[1]) / 2
        d.text(((ancho - (caja[2] - caja[0])) / 2, y), texto, fill=color, font=f)
    salida = io.BytesIO()
    img.save(salida, "PNG")
    return salida.getvalue()


class _LibroSimulado:
    def __init__(self, contenido: bytes):
        self.contenido = contenido
        self.info = ez.leer(contenido)
        self.avisos = ["Motor simulado: las imágenes son de relleno y los valores son los guardados en el archivo."]

    def _hoja(self, hoja: str) -> ez.Hoja:
        h = self.info.hoja(hoja)
        if h is None:
            raise ErrorMotor(f"No existe la hoja «{hoja}».")
        if not h.visible:
            raise ErrorMotor(f"La hoja «{hoja}» está oculta.")
        return h

    def capturar_rango(self, hoja: str, rango: str) -> Captura:
        ancho, alto = ez.tamano_rango_px(self._hoja(hoja), rango)
        escala = min(ESCALA, MAX_LADO_PX / max(ancho, alto, 1))
        return Captura(imagen_relleno(f"{hoja}!{rango}", "captura de rango", ancho * escala, alto * escala),
                       "simulado")

    def capturar_grafico(self, hoja: str, nombre: str) -> Captura:
        g = next((g for g in self._hoja(hoja).graficos if g.nombre == nombre), None)
        if g is None:
            raise ErrorMotor(f"No existe el gráfico «{nombre}» en la hoja «{hoja}».")
        ancho, alto = ez.tamano_rango_px(self._hoja(hoja), f"{g.desde}:{g.hasta}")
        return Captura(imagen_relleno(nombre, f"{g.tipo} – {hoja}", ancho * ESCALA, alto * ESCALA), "simulado")

    def copiar_grafico(self, hoja: str, nombre: str) -> None:
        raise ErrorMotor("El gráfico pegado (editable) necesita Excel en Windows. En el motor simulado se usa "
                         "una captura.")

    def texto_celda(self, hoja: str, celda: str) -> str | None:
        return ez.leer_celdas(self.contenido, [ez.ref_celda(hoja, celda)])[ez.ref_celda(hoja, celda)]


class MotorSimulado:
    nombre = "Simulado (sin Excel)"
    real = False

    def __init__(self, motivo: str = ""):
        self.motivo = motivo

    @contextmanager
    def abrir(self, contenido: bytes, nombre_archivo: str = "libro.xlsx", actualizar: bool = True):
        yield _LibroSimulado(contenido)


# ====================================================================== Windows
class _LibroWindows:
    def __init__(self, app, wb, carpeta: Path):
        self.app, self.wb, self.carpeta = app, wb, carpeta
        self.avisos: list[str] = []
        self._n = 0

    # ------------------------------------------------------------- generales
    def actualizar(self):
        """Actualiza conexiones, tablas dinámicas y Modelo de datos, y espera a que terminen."""
        try:
            self.wb.RefreshAll()
            self.app.CalculateUntilAsyncQueriesDone()
        except Exception as e:  # noqa: BLE001
            self.avisos.append(f"No se pudieron actualizar los datos ({_mensaje(e)}). Se usan los valores "
                               "que tenía guardados el archivo.")
        try:
            self.app.Calculate()
        except Exception:  # noqa: BLE001
            pass

    def _hoja(self, hoja: str):
        try:
            h = self.wb.Worksheets(hoja)
        except Exception as e:  # noqa: BLE001
            raise ErrorMotor(f"No existe la hoja «{hoja}».") from e
        if h.Visible != -1:  # -1 = visible; las ocultas no se usan (y no se tocan)
            raise ErrorMotor(f"La hoja «{hoja}» está oculta.")
        return h

    def _shape(self, hoja: str, nombre: str):
        """El shape del gráfico, aunque esté dentro de un grupo."""
        def buscar(shapes):
            for i in range(1, shapes.Count + 1):
                s = shapes.Item(i)
                if s.Name == nombre:
                    return s
                if s.Type == MSO_GRUPO:
                    for j in range(1, s.GroupItems.Count + 1):
                        if s.GroupItems.Item(j).Name == nombre:
                            return s.GroupItems.Item(j)
            return None
        s = buscar(self._hoja(hoja).Shapes)
        if s is None:
            raise ErrorMotor(f"No existe el gráfico «{nombre}» en la hoja «{hoja}».")
        return s

    def _ruta(self, extension: str) -> Path:
        self._n += 1
        return self.carpeta / f"captura_{self._n}.{extension}"

    # -------------------------------------------------------- portapapeles
    def _emf_del_portapapeles(self) -> bytes | None:
        import win32clipboard
        import win32con

        def leer():
            win32clipboard.OpenClipboard()
            try:
                if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_ENHMETAFILE):
                    return None
                return win32clipboard.GetClipboardData(win32con.CF_ENHMETAFILE)
            finally:
                win32clipboard.CloseClipboard()
        return reintentar(leer)

    def _emf_a_png(self, emf: bytes) -> bytes:
        """Dibuja el EMF (imagen vectorial) en alta resolución y lo pasa a PNG."""
        ruta = self._ruta("emf")
        ruta.write_bytes(emf)
        with Image.open(ruta) as im:
            dpi = im.info.get("dpi", 96)
            dpi = dpi[0] if isinstance(dpi, tuple) else dpi
            escala = min(ESCALA, MAX_LADO_PX / max(im.size))
            im.load(dpi=dpi * escala)
            salida = io.BytesIO()
            im.convert("RGB").save(salida, "PNG")
        return salida.getvalue()

    def _copiar_como_imagen(self, objeto) -> Captura:
        """CopyPicture vectorial → PNG en alta. Si falla, mapa de bits (resolución de pantalla)."""
        try:
            reintentar(lambda: objeto.CopyPicture(XL_SCREEN, XL_PICTURE))
            emf = self._emf_del_portapapeles()
            if emf:
                return Captura(self._emf_a_png(emf), f"CopyPicture vectorial (×{ESCALA})")
        except Exception as e:  # noqa: BLE001
            error = _mensaje(e)
        else:
            error = "el portapapeles no tenía la imagen"
        from PIL import ImageGrab
        reintentar(lambda: objeto.CopyPicture(XL_SCREEN, XL_BITMAP))
        img = reintentar(lambda: _imagen_o_error(ImageGrab.grabclipboard()))
        salida = io.BytesIO()
        img.convert("RGB").save(salida, "PNG")
        return Captura(salida.getvalue(), "CopyPicture mapa de bits",
                       [f"Se capturó en resolución de pantalla ({error})."])

    # ------------------------------------------------------------- capturas
    def capturar_rango(self, hoja: str, rango: str) -> Captura:
        """Imagen del rango, con los gráficos y formas que flotan encima."""
        return self._copiar_como_imagen(self._hoja(hoja).Range(rango))

    def capturar_grafico(self, hoja: str, nombre: str) -> Captura:
        """Imagen del gráfico. Primero copia del shape (anda con los modernos, como treemap); si no,
        Chart.Export."""
        shape = self._shape(hoja, nombre)
        try:
            return self._copiar_como_imagen(shape)
        except Exception as e:  # noqa: BLE001
            primero = _mensaje(e)
        ruta = self._ruta("png")
        try:
            reintentar(lambda: shape.Chart.Export(str(ruta), "PNG"))
            return Captura(ruta.read_bytes(), "Chart.Export", [f"La copia como imagen falló ({primero})."])
        except Exception as e:  # noqa: BLE001
            raise ErrorMotor(f"No se pudo capturar el gráfico «{nombre}»: {primero}; {_mensaje(e)}") from e

    def copiar_grafico(self, hoja: str, nombre: str) -> None:
        """Deja el gráfico (editable) en el portapapeles, para pegarlo en PowerPoint (etapa 3).
        Hay que pegarlo antes de cerrar el libro."""
        shape = self._shape(hoja, nombre)
        try:
            reintentar(lambda: shape.Chart.ChartArea.Copy())
        except Exception:  # noqa: BLE001 - los gráficos modernos no siempre tienen ChartArea.Copy
            reintentar(lambda: shape.Copy())

    def texto_celda(self, hoja: str, celda: str) -> str | None:
        """El texto tal como lo muestra Excel (con su formato: «septiembre 2026», «87,5%»)."""
        try:
            return str(self._hoja(hoja).Range(celda).Text)
        except ErrorMotor:
            return None


def _imagen_o_error(img):
    if not isinstance(img, Image.Image):
        raise ErrorMotor("El portapapeles no tenía la imagen.")
    return img


def _mensaje(e: Exception) -> str:
    """Mensaje corto de un error de COM (los traen anidados)."""
    args = getattr(e, "args", ())
    if len(args) >= 3 and isinstance(args[2], tuple) and len(args[2]) >= 3 and args[2][2]:
        return str(args[2][2]).strip()
    return str(e) or type(e).__name__


class MotorWindows:
    nombre = "Excel de Windows"
    real = True
    motivo = ""

    @contextmanager
    def abrir(self, contenido: bytes, nombre_archivo: str = "libro.xlsx", actualizar: bool = True):
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()  # Streamlit corre cada pantalla en otro hilo
        carpeta = Path(tempfile.mkdtemp(prefix="informes_excel_"))
        ruta = carpeta / ("libro" + (Path(nombre_archivo).suffix.lower() or ".xlsx"))
        ruta.write_bytes(contenido)  # se trabaja sobre una copia temporal
        app = wb = libro = None
        pid = None
        try:
            app = win32com.client.DispatchEx("Excel.Application")  # instancia propia, aparte de las del usuario
            pid = _pid(app)
            app.Visible = False
            app.DisplayAlerts = False
            app.AskToUpdateLinks = False
            app.EnableEvents = False
            try:
                app.AutomationSecurity = 3  # no correr macros del archivo
            except Exception:  # noqa: BLE001
                pass
            try:
                wb = app.Workbooks.Open(str(ruta), 0, True)  # UpdateLinks=0, ReadOnly=True
            except Exception as e:  # noqa: BLE001
                raise ErrorMotor(f"Excel no pudo abrir el archivo: {_mensaje(e)}") from e
            libro = _LibroWindows(app, wb, carpeta)
            if actualizar:
                libro.actualizar()
            yield libro
        finally:
            if libro is not None:  # soltar las referencias de COM para que Excel pueda cerrarse
                libro.app = libro.wb = None
            if wb is not None:
                try:
                    wb.Close(False)  # sin guardar
                except Exception:  # noqa: BLE001
                    pass
            if app is not None:
                try:
                    app.Quit()
                except Exception:  # noqa: BLE001
                    pass
            wb = app = libro = None
            gc.collect()
            _terminar(pid)
            pythoncom.CoUninitialize()
            shutil.rmtree(carpeta, ignore_errors=True)


def _pid(app) -> int | None:
    try:
        import win32process
        return win32process.GetWindowThreadProcessId(app.Hwnd)[1]
    except Exception:  # noqa: BLE001
        return None


def _terminar(pid: int | None, espera_ms: int = 8000):
    """Si NUESTRO Excel no se cerró solo, se cierra a la fuerza (solo ese proceso)."""
    if not pid:
        return
    try:
        import win32api
        import win32con
        import win32event
        proceso = win32api.OpenProcess(win32con.SYNCHRONIZE | win32con.PROCESS_TERMINATE, False, pid)
    except Exception:  # noqa: BLE001 - ya no existe
        return
    try:
        if win32event.WaitForSingleObject(proceso, espera_ms) == win32event.WAIT_TIMEOUT:
            win32api.TerminateProcess(proceso, 0)
    finally:
        win32api.CloseHandle(proceso)


def exportar(motor, contenido: bytes, nombre_archivo: str, pedidos: list[dict], celdas: list[str] = (),
             actualizar: bool = True) -> tuple[dict, dict, list[str]]:
    """Hace varias capturas y lee varias celdas abriendo el Excel UNA sola vez.

    pedidos: [{"id", "hoja", "rango"} o {"id", "hoja", "grafico"}]; celdas: ["Carátula!D32", ...].
    Devuelve ({id: Captura o ErrorMotor}, {celda: texto o None}, avisos generales).
    Un pedido que falla no frena a los demás.
    """
    capturas, textos = {}, {}
    with motor.abrir(contenido, nombre_archivo, actualizar) as libro:
        for p in pedidos:
            try:
                capturas[p["id"]] = (libro.capturar_grafico(p["hoja"], p["grafico"]) if p.get("grafico")
                                     else libro.capturar_rango(p["hoja"], p["rango"]))
            except Exception as e:  # noqa: BLE001 - se informa y se sigue con el resto
                capturas[p["id"]] = e if isinstance(e, ErrorMotor) else ErrorMotor(_mensaje(e))
        for ref in celdas:
            hoja, celda = ez.partir_ref(ref)
            try:
                textos[ref] = libro.texto_celda(hoja, celda)
            except Exception:  # noqa: BLE001
                textos[ref] = None
        avisos = list(libro.avisos)
    return capturas, textos, avisos


def obtener():
    """El motor disponible en esta compu (Excel real en Windows, si no el simulado)."""
    if os.getenv("INFORMES_OFFICE", "").lower() == "simulado":
        return MotorSimulado("está forzado con INFORMES_OFFICE=simulado")
    if sys.platform != "win32":
        return MotorSimulado("esta compu no es Windows")
    try:
        import pythoncom  # noqa: F401
        import win32com.client  # noqa: F401
    except ImportError:
        return MotorSimulado("falta instalar pywin32 (pip install -r requirements.txt)")
    return MotorWindows()


if __name__ == "__main__":
    # Prueba de capturas en la compu del trabajo, por ejemplo:
    #   py -3.13 -m src.informes_pptx.excel muestras\Indicadores.xlsx "Confiabilidad!A5:N41" "Disponib.!Gráfico 3"
    # Guarda los PNG en muestras/prueba_capturas/ y dice cómo se hizo cada uno.
    archivo, *pedidos_texto = sys.argv[1:]
    pedidos = []
    for i, texto in enumerate(pedidos_texto, 1):
        hoja, que = ez.partir_ref(texto)
        desde, _, hasta = que.partition(":")
        rango = ez.armar_rango(desde, hasta or desde)
        pedidos.append({"id": f"{i:02d}", "hoja": hoja, **({"rango": rango} if rango else {"grafico": que})})
    motor = obtener()
    print(f"Motor: {motor.nombre}{' (' + motor.motivo + ')' if motor.motivo else ''}")
    inicio = time.time()
    capturas, _, avisos = exportar(motor, Path(archivo).read_bytes(), archivo, pedidos)
    print(f"Excel abierto, actualizado y cerrado en {time.time() - inicio:.0f} s")
    for a in avisos:
        print(f"  ⚠ {a}")
    salida = Path("muestras") / "prueba_capturas"
    salida.mkdir(parents=True, exist_ok=True)
    for p, texto in zip(pedidos, pedidos_texto):
        cap = capturas[p["id"]]
        if isinstance(cap, Exception):
            print(f"{texto}: ERROR – {cap}")
            continue
        ruta = salida / f"{p['id']}.png"
        ruta.write_bytes(cap.png)
        print(f"{texto}: {cap.tamano[0]} × {cap.tamano[1]} px con {cap.metodo} → {ruta}")
        for a in cap.avisos:
            print(f"  ⚠ {a}")
