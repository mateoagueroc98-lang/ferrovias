"""Tests del módulo Asociación LG ↔ PCZ (correr con:  python -m pytest)."""
import datetime as dt
import io

import pandas as pd
import pytest

from src import asociacion_lg_pcz as a
from tests.generar_ejemplos import generar

F = dt.date


# ------------------------------------------------------------- fechas
@pytest.mark.parametrize("valor, esperado", [
    ("05/03/2025", F(2025, 3, 5)),      # día primero, nunca mes primero
    ("5/3/25", F(2025, 3, 5)),
    ("05-03-2025", F(2025, 3, 5)),
    ("5.3.2025", F(2025, 3, 5)),
    ("13/01/2025", F(2025, 1, 13)),
    (" 05/03/2025 14:30 ", F(2025, 3, 5)),
    ("2025-03-05", F(2025, 3, 5)),      # ISO
    ("2025-03-05 00:00:00", F(2025, 3, 5)),
    (45721, F(2025, 3, 5)),             # número serial de Excel
    (45721.75, F(2025, 3, 5)),          # serial con hora
    ("45721", F(2025, 3, 5)),
    (dt.datetime(2025, 3, 5, 10, 0), F(2025, 3, 5)),
    (pd.Timestamp("2025-03-05"), F(2025, 3, 5)),
    (F(2025, 3, 5), F(2025, 3, 5)),
])
def test_parsear_fecha_valida(valor, esperado):
    assert a.parsear_fecha(valor) == esperado


@pytest.mark.parametrize("valor", [
    "03/13/2025",   # mes 13: NO se reinterpreta como MM/DD
    "32/01/2025", "31/02/2025", "ayer", "", "  ", None, float("nan"), pd.NaT, 12, "1/2",
])
def test_parsear_fecha_invalida(valor):
    assert a.parsear_fecha(valor) is None


@pytest.mark.parametrize("valor, esperado", [
    ("14:40", 14 * 60 + 40), ("9.05", 9 * 60 + 5), ("22hs", 22 * 60), ("08:15:00", 8 * 60 + 15),
    (dt.time(23, 50), 23 * 60 + 50), (0.5, 12 * 60), (None, None), ("sin hora", None),
])
def test_parsear_hora(valor, esperado):
    assert a.parsear_hora(valor) == esperado


def test_horas_en_texto_no_confunde_km():
    horas = [h for _, _, h in a.horas_en_texto("km 14/116 a las 9:10 hs, km 14.300, 22 hs")]
    assert horas == [9 * 60 + 10, 22 * 60]


# ------------------------------------------------------------ columnas
def test_mapear_columnas_tolerante():
    df = pd.DataFrame(columns=["  DESCRIPCION ", "fecha", "Nº Novedad"])
    mapa, faltan = a.mapear_columnas(df, a.COLUMNAS_PCZ)
    assert faltan == []
    assert mapa["N° Novedad"] == "Nº Novedad"
    for nombre in ["N° Novedad", "N Novedad", "Nro. Novedad", "nº novedad"]:
        _, faltan = a.mapear_columnas(pd.DataFrame(columns=["Descripción", "Fecha", nombre]), a.COLUMNAS_PCZ)
        assert faltan == [], nombre


def test_mapear_columnas_avisa_faltantes():
    _, faltan = a.mapear_columnas(pd.DataFrame(columns=["Pagina", "Fecha"]), a.COLUMNAS_LG)
    assert faltan == ["Hora", "Transcripción"]


# ------------------------------------------------------ filtro por fecha
def _pcz():
    df = pd.DataFrame({
        "Descripción": ["a", "b", "c", "d", "e"],
        "Fecha": ["04/03/2025", 45721, "6/3/25", "05/03/2025", "basura"],
        "N° Novedad": [1, 2, 3, 4, 5],
    })
    mapa, _ = a.mapear_columnas(df, a.COLUMNAS_PCZ)
    return a.preparar_pcz(df, mapa)


def test_filtro_solo_misma_fecha():
    sel = a.filtrar_por_fecha(_pcz(), F(2025, 3, 5))
    assert list(sel["id"]) == ["2", "4"]
    assert not sel["otro_dia"].any()


def test_filtro_no_confunde_mes_y_dia():
    # 3 de mayo NO es 5 de marzo
    assert a.filtrar_por_fecha(_pcz(), F(2025, 5, 3)).empty


def test_filtro_con_dias_vecinos_marcados():
    sel = a.filtrar_por_fecha(_pcz(), F(2025, 3, 5), vecinos=True)
    assert sorted(sel["id"]) == ["1", "2", "3", "4"]
    assert dict(zip(sel["id"], sel["otro_dia"])) == {"1": True, "2": False, "3": True, "4": False}


def test_filtro_sin_fecha_lg_no_da_candidatos():
    assert a.filtrar_por_fecha(_pcz(), None).empty


def test_fechas_invalidas_se_informan():
    malas = a.fechas_invalidas(_pcz())
    assert list(malas["Fila"]) == [5]
    assert list(malas["Fecha tal cual viene"]) == ["basura"]


# ------------------------------------------------------------- puntaje
def test_similitud_numeros_palabras_y_hora():
    r = a.similitud("Falla en señal 14 de estación Boulogne", [8 * 60 + 15],
                    "Señales 14 Boulogne a peligro 08:10 hs")
    assert "n:14" in r["comunes"] and "w:boulo" in r["comunes"] and "w:senal" in r["comunes"]
    assert r["dif_hora"] == 5
    assert r["puntaje"] == 3 + 2 + 3


def test_similitud_sigla_y_km():
    r = a.similitud("Locomotora E712 en km 14/116", [], "loc E-712 km 14/116")
    assert {"n:712", "n:14/116"} <= r["comunes"]


def test_hora_cruza_medianoche():
    r = a.similitud("x", [23 * 60 + 50], "y 00:10")
    assert r["dif_hora"] == 20


def test_resaltar_escapa_html():
    salida = a.resaltar("Señal 14 <b>", {"n:14"})
    assert "<mark>14</mark>" in salida and "&lt;b&gt;" in salida


def test_candidatos_ordenados_y_todos_visibles():
    lg = pd.Series({"fecha": F(2025, 3, 5), "hora": None, "texto": "señal d"})
    pcz = _pcz()
    pcz.loc[3, "descripcion"] = "señal"
    c = a.candidatos(lg, pcz)
    assert list(c["id"]) == ["4", "2"]  # se muestran todos los del día, el mejor primero


# ------------------------------------------------------ sesión y exportación
def _cargar_ejemplos(tmp_path):
    ruta_lg, ruta_pcz = generar(tmp_path)
    lg_df = a.leer_tabla(ruta_lg.name, ruta_lg.read_bytes())
    pcz_df = a.leer_tabla(ruta_pcz.name, ruta_pcz.read_bytes())
    lg = a.preparar_lg(lg_df, a.mapear_columnas(lg_df, a.COLUMNAS_LG)[0])
    pcz = a.preparar_pcz(pcz_df, a.mapear_columnas(pcz_df, a.COLUMNAS_PCZ)[0])
    return lg_df, pcz_df, lg, pcz


def test_ejemplos_fechas_mezcladas(tmp_path):
    _, _, lg, pcz = _cargar_ejemplos(tmp_path)
    assert lg["fecha"].notna().all()
    assert set(lg["fecha"]) == {F(2025, 3, 4), F(2025, 3, 5), F(2025, 3, 6)}
    assert pcz["fecha"].isna().sum() == 1  # la "32/13/2025"
    # El mejor candidato de la fila 4 (E712, Márquez) es la novedad 1014
    assert a.candidatos(lg.loc[3], pcz).iloc[0]["id"] == "1014"


def test_deshacer_y_progreso():
    s = a.sesion_nueva("h", "lg", "pcz", 3)
    a.registrar(s, 0, "asociada", ["1", "2"])
    a.registrar(s, 1, "ninguna")
    assert a.progreso(s) == {"total": 3, "asociadas": 1, "ninguna": 1, "pendientes": 1}
    assert a.deshacer(s) == 1
    assert s["filas"]["1"]["estado"] == "pendiente"
    assert a.siguiente_pendiente(s, 0) == 1


def test_guardar_e_importar(tmp_path):
    s = a.sesion_nueva("h", "lg", "pcz", 2)
    a.registrar(s, 1, "asociada", ["7"])
    a.guardar_sesion(s, tmp_path)
    assert a.cargar_sesion(tmp_path, "h")["filas"]["1"]["novedades"] == ["7"]
    otra, avisos = a.importar_sesion(a.sesion_a_json(s), 2, "otra")
    assert otra["filas"]["1"]["novedades"] == ["7"] and avisos
    with pytest.raises(ValueError):
        a.importar_sesion("no es json", 2, "h")


def test_exportar(tmp_path):
    lg_df, pcz_df, lg, pcz = _cargar_ejemplos(tmp_path)
    s = a.sesion_nueva("h", "lg", "pcz", len(lg))
    a.registrar(s, 0, "asociada", ["1001", "1002"], {"1002": [1]})
    a.registrar(s, 1, "ninguna")
    a.registrar(s, 4, "asociada", ["1002"])  # 1002 en dos filas de LG
    hojas = pd.read_excel(io.BytesIO(a.exportar(lg_df, pcz_df, lg, pcz, s)), sheet_name=None)

    assert list(hojas) == ["LG_asociado", "PCZ_completado", "Resumen"]
    hl = hojas["LG_asociado"]
    assert list(hl["Estado"]) == ["Asociada", "Ninguna", "Pendiente", "Pendiente", "Asociada"]
    assert hl.loc[0, "N° Novedad asociada(s)"] == "1001;1002"

    hp = hojas["PCZ_completado"].set_index("Nº Novedad")
    assert len(hp) == len(pcz_df)
    # 1001 recibe el párrafo entero; 1002 solo el 2° renglón de la fila 1 + la fila 5
    assert hp.loc[1001, "Texto LG"].startswith("Se informa falla en señal 14")
    assert hp.loc[1002, "Texto LG"].startswith("Se normaliza señal 14 a las 9:10 hs. / Abrigo 3")
    assert hp.loc[1002, "Descripción combinada"].startswith(
        "Señal 14 Boulogne normalizada 09:12 se normaliza señal 14")
    assert pd.isna(hp.loc[1003, "Descripción combinada"])  # sin LG -> vacío

    res = hojas["Resumen"]
    assert "1002" in res.astype(str).to_string()
