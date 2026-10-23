"""Tests del módulo Informes PowerPoint, etapa 2: configuraciones y Excel (python -m pytest)."""
import datetime as dt
import io
import json

import pytest
from PIL import Image

from src.informes_pptx import configuraciones as cf
from src.informes_pptx import excel
from src.informes_pptx import excel_zip as ez
from src.informes_pptx import plantillas as pl
from tests.generar_ejemplo_excel import ARCHIVO as EXCEL, generar as generar_excel
from tests.generar_ejemplo_informe import ARCHIVO as PPTX, generar as generar_pptx


@pytest.fixture(scope="module")
def contenido() -> bytes:
    generar_excel()
    return EXCEL.read_bytes()


@pytest.fixture(scope="module")
def info(contenido) -> ez.InfoExcel:
    return ez.leer(contenido)


@pytest.fixture
def plantilla(tmp_path) -> dict:
    generar_pptx()
    p = pl.crear("Informe", "Informe_ejemplo.pptx", PPTX.read_bytes(), tmp_path)
    titulo = p["diapositivas"][0]["textos"][0]
    titulo.update(tipo=pl.VARIABLE, reemplazo=pl.FRAGMENTO, fragmento="Septiembre 2026",
                  variable_nombre="Mes", variable_id="mes")
    fuente = p["diapositivas"][3]["textos"][2]
    fuente.update(tipo=pl.VARIABLE, variable_nombre="Fuente", variable_id="fuente")
    return pl.guardar(p, tmp_path)


# ------------------------------------------------------------- lectura del xlsx
def test_hojas_visibles_y_ocultas(info):
    assert [h.nombre for h in info.hojas] == ["Carátula", "Confiabilidad", "Disponib.", "Datos"]
    assert [h.nombre for h in info.visibles] == ["Carátula", "Confiabilidad", "Disponib."]


def test_graficos_incluye_los_modernos_y_los_agrupados(info):
    conf = info.hoja("Confiabilidad").graficos
    assert [(g.nombre, g.tipo, g.titulo) for g in conf] == [("Chart 1", "Columnas", "Fallas por mes")]
    disp = info.hoja("Disponib.").graficos
    assert [(g.nombre, g.tipo, g.titulo, g.moderno, g.en_grupo) for g in disp] == [
        ("Chart 1", "Torta", "Participación por sistema", False, False),
        ("Gráfico 7", "Treemap", "Fallas por sistema", True, True),  # el Fallback no se cuenta
    ]
    assert (disp[1].desde, disp[1].hasta) == ("F21", "N39")
    assert disp[0].desde == "F2"  # anclado a una celda: el final se calcula con su tamaño


def test_archivo_que_no_es_excel():
    with pytest.raises(ez.ErrorExcel):
        ez.leer(b"no es un zip")


def test_valores_guardados_con_formato(contenido):
    v = ez.leer_celdas(contenido, ["Carátula!D32", "Carátula!D33", "Carátula!D34", "'Disponib.'!A2",
                                   "Nada!A1", "Carátula!ZZZZ1"])
    assert v == {"Carátula!D32": "septiembre 2026", "Carátula!D33": "12.500,5", "Carátula!D34": "87,5%",
                 "'Disponib.'!A2": "Señales", "Nada!A1": None, "Carátula!ZZZZ1": None}


@pytest.mark.parametrize("valor, formato, texto", [
    (dt.datetime(2026, 9, 1), "dd/mm/yyyy", "01/09/2026"),
    (dt.datetime(2026, 9, 1), "mmmm-yy", "septiembre 26"),
    (0.91, "0%", "91%"),
    (1234.5, "General", "1234,5"),
    (1234567, "#,##0", "1.234.567"),
    ("texto", "General", "texto"),
    (None, "General", ""),
])
def test_texto_valor(valor, formato, texto):
    assert ez.texto_valor(valor, formato) == texto


@pytest.mark.parametrize("hoja, celda, ref", [
    ("Carátula", "D32", "Carátula!D32"),
    ("Disponib.", "A1", "Disponib.!A1"),
    ("Hoja 1", "A1", "'Hoja 1'!A1"),
    ("O'Brien", "B2", "'O''Brien'!B2"),
    ("2026", "A1", "'2026'!A1"),
])
def test_referencias_ida_y_vuelta(hoja, celda, ref):
    assert ez.ref_celda(hoja, celda) == ref
    assert ez.partir_ref(ref) == (hoja, celda)


def test_celdas_y_rangos():
    assert ez.normalizar_celda(" $n$41 ") == "N41"
    assert ez.normalizar_celda("A0") is None and ez.normalizar_celda("XFE1") is None
    assert ez.armar_rango("N41", "a5") == "A5:N41"
    assert ez.armar_rango("A5", "5A") is None


# ------------------------------------------------------------ configuración
def test_crear_completa_todos_los_lugares_y_variables(plantilla, tmp_path):
    c = cf.crear("Señalamiento", plantilla, tmp_path)
    assert list(c["imagenes"]) == ["img_02_01", "img_02_02", "img_03_01", "img_04_01"]
    assert list(c["textos"]) == ["mes", "fuente"]
    errores, pendientes = cf.validar(c, plantilla)
    assert errores == [] and len(pendientes) == 4  # los textos libres ya están completos


def test_json_legible_como_el_ejemplo(plantilla, tmp_path):
    c = cf.crear("Señalamiento", plantilla, tmp_path)
    c["imagenes"]["img_02_01"].update(hoja="Confiabilidad", desde="N41", hasta="a5")
    c["imagenes"]["img_02_02"].update(hoja="Disponib.", toma=cf.GRAFICO, grafico="Gráfico 7", modo=cf.GRAFICO)
    c["textos"]["mes"].update(fuente=cf.CELDA, hoja="Carátula", celda=" d32")
    c["textos"]["fuente"]["por_defecto"] = "Indicadores RAMS"
    cf.guardar(c, plantilla, tmp_path)
    datos = json.loads((tmp_path / "configuraciones" / f"{c['id']}.json").read_text(encoding="utf-8"))
    assert datos["nombre"] == "Señalamiento" and datos["plantilla"] == plantilla["id"]
    assert datos["imagenes"]["img_02_01"] == {"hoja": "Confiabilidad", "rango": "A5:N41", "modo": "captura",
                                              "ajuste": "encajar", "estilo": {}}
    assert datos["imagenes"]["img_02_02"] == {"hoja": "Disponib.", "grafico": "Gráfico 7", "modo": "grafico",
                                              "ajuste": "encajar", "estilo": {}}
    assert datos["textos"] == {"mes": {"fuente": "celda", "celda": "Carátula!D32"},
                               "fuente": {"fuente": "libre", "por_defecto": "Indicadores RAMS"}}
    vuelta = cf.cargar(c["id"], tmp_path)
    assert vuelta["imagenes"]["img_02_01"]["desde"] == "A5" and vuelta["textos"]["mes"]["hoja"] == "Carátula"


def test_errores_que_no_dejan_guardar(plantilla, tmp_path):
    c = cf.crear("x", plantilla, tmp_path)
    c["imagenes"]["img_02_01"].update(hoja="Confiabilidad", desde="A5", hasta="N99999999", modo=cf.GRAFICO)
    c["textos"]["mes"].update(fuente=cf.CELDA, hoja="Carátula", celda="D")
    with pytest.raises(cf.ErrorConfiguracion) as e:
        cf.guardar(c, plantilla, tmp_path)
    assert "no es una celda válida (Hasta)" in str(e.value)
    assert "gráfico pegado solo se puede elegir si se toma un gráfico" in str(e.value)
    assert "«D» no es una celda válida" in str(e.value)


def test_avisos_si_el_excel_cambio(plantilla, tmp_path, info):
    c = cf.crear("x", plantilla, tmp_path)
    c["imagenes"]["img_02_01"].update(hoja="Confiab", desde="A1", hasta="B2")           # hoja renombrada
    c["imagenes"]["img_02_02"].update(hoja="Disponib.", toma=cf.GRAFICO, grafico="Gráfico 99")
    c["imagenes"]["img_03_01"].update(hoja="Datos", desde="A1", hasta="B2")             # hoja oculta
    c["textos"]["mes"].update(fuente=cf.CELDA, hoja="Portada", celda="D32")
    avisos = cf.avisos_excel(c, info)
    assert "no existe" in avisos["img_02_01"][0]
    assert "Gráfico 99" in avisos["img_02_02"][0]
    assert "oculta" in avisos["img_03_01"][0]
    assert "Portada" in avisos["mes"][0]
    assert "img_04_01" not in avisos and "fuente" not in avisos


def test_completar_si_la_plantilla_cambio(plantilla, tmp_path):
    c = cf.crear("x", plantilla, tmp_path)
    c["textos"]["viejo"] = cf.texto_vacio()
    del c["imagenes"]["img_04_01"]
    c2, avisos = cf.completar(c, plantilla)
    assert "viejo" not in c2["textos"] and "img_04_01" in c2["imagenes"]
    assert any("viejo" in a for a in avisos)


def test_listar_duplicar_eliminar_y_por_plantilla(plantilla, tmp_path):
    c = cf.crear("Uno", plantilla, tmp_path)
    copia = cf.duplicar(c["id"], tmp_path)
    assert copia["nombre"] == "Uno (copia)"
    assert {x["id"] for x in cf.de_plantilla(plantilla["id"], tmp_path)} == {c["id"], copia["id"]}
    cf.eliminar(c["id"], tmp_path)
    assert [x["id"] for x in cf.listar(tmp_path)[0]] == [copia["id"]]


# ---------------------------------------------------------------- acomodar
CAJA = {"x": 100, "y": 100, "ancho": 400, "alto": 200}


@pytest.mark.parametrize("ancho, alto, ajuste, esperado", [
    (100, 100, "encajar", {"x": 200, "y": 100, "ancho": 200, "alto": 200}),   # cuadrada en caja apaisada
    (800, 200, "encajar", {"x": 100, "y": 150, "ancho": 400, "alto": 100}),
    (100, 100, "ancho", {"x": 100, "y": 0, "ancho": 400, "alto": 400}),       # sobresale arriba y abajo
    (800, 200, "alto", {"x": -100, "y": 100, "ancho": 800, "alto": 200}),
])
def test_encajar_centrado(ancho, alto, ajuste, esperado):
    assert cf.encajar(ancho, alto, CAJA, ajuste) == esperado


def test_vista_en_recuadro():
    png = excel.imagen_relleno("x", "y", 300, 100)
    img = Image.open(io.BytesIO(cf.vista_en_recuadro(png, CAJA, "encajar", 500)))
    assert img.width == 500


# ------------------------------------------------------------- motor simulado
def test_motor_simulado_captura_rangos_graficos_y_celdas(contenido):
    motor = excel.MotorSimulado()
    pedidos = [{"id": "a", "hoja": "Confiabilidad", "rango": "A5:N41"},
               {"id": "b", "hoja": "Disponib.", "grafico": "Gráfico 7"},
               {"id": "c", "hoja": "Disponib.", "grafico": "No existe"},
               {"id": "d", "hoja": "Datos", "rango": "A1:B2"}]
    capturas, textos, avisos = excel.exportar(motor, contenido, "x.xlsx", pedidos, ["Carátula!D32", "Nada!A1"])
    ancho, alto = capturas["a"].tamano
    assert ancho > 2000 and alto > 1500  # en alta (triple de pantalla)
    assert capturas["b"].tamano[0] > 0
    assert isinstance(capturas["c"], excel.ErrorMotor) and isinstance(capturas["d"], excel.ErrorMotor)
    assert textos == {"Carátula!D32": "septiembre 2026", "Nada!A1": None}
    assert avisos


def test_simulado_no_pega_graficos(contenido):
    with excel.MotorSimulado().abrir(contenido) as libro, pytest.raises(excel.ErrorMotor):
        libro.copiar_grafico("Disponib.", "Gráfico 7")


def test_obtener_motor_simulado(monkeypatch):
    monkeypatch.setenv("INFORMES_OFFICE", "simulado")
    assert not excel.obtener().real


def test_reintentar():
    intentos = []

    def falla_dos_veces():
        intentos.append(1)
        if len(intentos) < 3:
            raise OSError("portapapeles ocupado")
        return "ok"
    assert excel.reintentar(falla_dos_veces, espera=0) == "ok" and len(intentos) == 3
