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
    df = pd.DataFrame(columns=["  DESCRIPCION ", "fecha", "Nº Novedad", "Hora del evento"])
    mapa, faltan = a.mapear_columnas(df, a.COLUMNAS_PCZ)
    assert faltan == [] and mapa["Hora"] == "Hora del evento"
    assert mapa["N° Novedad"] == "Nº Novedad"
    for nombre in ["N° Novedad", "N Novedad", "Nro. Novedad", "nº novedad"]:
        _, faltan = a.mapear_columnas(pd.DataFrame(columns=["Descripción", "Fecha", nombre]), a.COLUMNAS_PCZ)
        assert faltan == ["Hora"], nombre  # la hora es opcional


def test_mapear_columnas_avisa_faltantes():
    _, faltan = a.mapear_columnas(pd.DataFrame(columns=["Pagina", "Fecha"]), a.COLUMNAS_LG)
    assert faltan == ["Transcripción", "Hora"]


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


# ---------------------------------------- deshacer, progreso y exportación
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
    s = a.trabajo_nuevo("h", 3)
    n_avisos = [2, 1, 1]
    a.registrar(s, 0, [{"avisos": [0], "novedades": ["1", "2"]}], descartados=[1])
    a.registrar(s, 1, [], descartados=[0])
    assert a.progreso(s, n_avisos) == {"avisos": 4, "asociados": 1, "descartados": 2, "pendientes": 1,
                                       "asociaciones": 1}
    assert a.siguiente_pendiente(s, 0, n_avisos) == 2
    assert a.deshacer(s) == 1
    assert s["filas"]["1"] == {"grupos": [], "descartados": []}
    assert a.siguiente_pendiente(s, 0, n_avisos) == 1


def _trabajo_ejemplo(lg):
    s = a.trabajo_nuevo("h", len(lg))
    # Fila 1 (2 avisos): los dos avisos -> 1001 y 1002 en una sola asociación
    a.registrar(s, 0, [{"avisos": [0, 1], "novedades": ["1001", "1002"]}], [])
    # Fila 2 (2 avisos): aviso 1 -> 1003; el aviso 2 queda sin asociar
    a.registrar(s, 1, [{"avisos": [0], "novedades": ["1003"]}], [])
    # Fila 5: dos asociaciones distintas (1022 y, aparte, 1002 que ya estaba en la fila 1)
    a.registrar(s, 4, [{"avisos": [0], "novedades": ["1022"]}, {"avisos": [1], "novedades": ["1002"]}], [])
    return s


MAPA_LG = {"Fecha": "Fecha", "Hora": "Hora", "Transcripción": "Transcripcion"}
MAPA_PCZ = {"Fecha": "Fecha", "Descripción": "Descripcion", "N° Novedad": "Nº Novedad", "Hora": "Hora"}


def test_columnas_por_defecto_y_disponibles(tmp_path):
    lg_df, pcz_df, _, _ = _cargar_ejemplos(tmp_path)
    defecto = a.columnas_por_defecto(MAPA_LG, MAPA_PCZ)
    assert defecto == ["LG · Fecha", "LG · Hora", "LG · Transcripcion", "PCZ · Nº Novedad",
                       "PCZ · Descripcion", a.COMBINADA]
    assert set(defecto) <= set(a.columnas_disponibles(lg_df, pcz_df))


def test_tabla_asociaciones_junta_con_barra_y_respeta_orden(tmp_path):
    lg_df, pcz_df, lg, pcz = _cargar_ejemplos(tmp_path)
    s = _trabajo_ejemplo(lg)
    cols = [a.FILA_LG, "PCZ · Nº Novedad", "LG · Transcripcion", "PCZ · Descripcion", a.COMBINADA, "LG · Pagina"]
    t = a.tabla_asociaciones(lg_df, pcz_df, lg, pcz, s, MAPA_LG, MAPA_PCZ, cols)
    assert list(t.columns) == cols and len(t) == 4  # una fila por asociación
    f = t.iloc[0]
    assert f[a.FILA_LG] == 1 and f["PCZ · Nº Novedad"] == "1001 | 1002" and f["LG · Pagina"] == 12
    assert f["LG · Transcripcion"] == ("Se informa falla en señal 14 de estación Boulogne, concurre mecánico "
                                       "Pérez. | Se normaliza señal 14 a las 9:10 hs.")
    assert f["PCZ · Descripcion"] == "Falla señal 14 Boulogne, a peligro 08:10 hs | Señal 14 Boulogne normalizada 09:12"
    assert f[a.COMBINADA] == (f["PCZ · Descripcion"] + " " + f["LG · Transcripcion"].lower())
    assert t.iloc[1]["LG · Transcripcion"] == "Brazo del P.A.N. calle Sarmiento no baja, interviene Gómez."


def test_sin_asociar_conserva_columnas_originales(tmp_path):
    lg_df, pcz_df, lg, pcz = _cargar_ejemplos(tmp_path)
    s = _trabajo_ejemplo(lg)
    lgs = a.lg_sin_asociar(lg_df, lg, s, MAPA_LG)
    assert list(lgs.columns) == list(lg_df.columns)
    # fila 2 (solo su aviso 2), filas 3 y 4 enteras; fila 1 y 5 están completas
    assert list(lgs["Pagina"]) == [12, 13, 13]
    assert lgs.iloc[0]["Transcripcion"] == "Cambio 7 sin comprobación en Villa Adelina, se ajusta."
    assert lgs.iloc[1]["Transcripcion"] == lg_df.iloc[2]["Transcripcion"]
    pzs = a.pcz_sin_asociar(pcz_df, pcz, s)
    assert list(pzs.columns) == list(pcz_df.columns)
    assert len(pzs) == len(pcz_df) - 4 and not {1001, 1002, 1003, 1022} & set(pzs["Nº Novedad"])


def test_exportar_tres_hojas(tmp_path):
    lg_df, pcz_df, lg, pcz = _cargar_ejemplos(tmp_path)
    s = _trabajo_ejemplo(lg)
    cols = a.columnas_por_defecto(MAPA_LG, MAPA_PCZ)
    hojas = pd.read_excel(io.BytesIO(a.exportar(lg_df, pcz_df, lg, pcz, s, MAPA_LG, MAPA_PCZ, cols)),
                          sheet_name=None)
    assert list(hojas) == ["Asociaciones", "LG sin asociar", "PCZ sin asociar"]
    assert list(hojas["Asociaciones"].columns) == cols and len(hojas["Asociaciones"]) == 4
    assert len(hojas["LG sin asociar"]) == 3 and len(hojas["PCZ sin asociar"]) == len(pcz_df) - 4


# ------------------------------------------------ grupos aviso(s) -> novedad(es)
def test_puntaje_solo_con_avisos_elegidos():
    fila = pd.Series({"fecha": F(2025, 3, 4), "hora": None, "avisos": ["Señal 14 Boulogne", "Cambio 7 Villa Adelina"],
                      "texto": "Señal 14 Boulogne Cambio 7 Villa Adelina"})
    pcz = pd.DataFrame({"id": ["1", "2"], "descripcion": ["Señal 14 Boulogne", "Cambio 7 Villa Adelina"],
                        "fecha": [F(2025, 3, 4)] * 2})
    c = a.candidatos(a.fila_con_avisos(fila, [1]), pcz)
    assert list(c["id"]) == ["2", "1"] and c.iloc[1]["puntaje"] == 0


# ---------------------------------------------- columnas elegidas por el usuario
def test_preparar_lg_con_columnas_de_otro_nombre_y_sin_opcionales():
    df = pd.DataFrame({"Día": ["05/03/2025"], "Texto del libro": ["Señal 14\nCambio 7"]})
    lg = a.preparar_lg(df, {"Fecha": "Día", "Transcripción": "Texto del libro"})
    assert lg.loc[0, "fecha"] == F(2025, 3, 5)
    assert lg.loc[0, "avisos"] == ["Señal 14", "Cambio 7"]
    assert lg.loc[0, "pagina"] == "" and lg.loc[0, "hora"] is None


def test_preparar_pcz_con_columnas_de_otro_nombre():
    df = pd.DataFrame({"Detalle": ["Falla"], "F. evento": [45721], "ID": [7.0]})
    pcz = a.preparar_pcz(df, {"Descripción": "Detalle", "Fecha": "F. evento", "N° Novedad": "ID"})
    assert list(pcz["id"]) == ["7"] and pcz.loc[0, "fecha"] == F(2025, 3, 5)


def test_filas_de_tabla_incluye_avisos_sin_asociar_en_orden():
    grupos = [{"avisos": [2], "novedades": ["9"]}, {"avisos": [0], "novedades": ["5", "6"]}]
    assert a.filas_de_tabla(grupos, 4, descartados=[3]) == [
        {"avisos": [0], "novedades": ["5", "6"], "descartado": False},
        {"avisos": [1], "novedades": [], "descartado": False},
        {"avisos": [2], "novedades": ["9"], "descartado": False},
        {"avisos": [3], "novedades": [], "descartado": True},
    ]
    assert a.filas_de_tabla([], 0) == []


def test_preparar_pcz_sin_n_novedad_usa_fila_del_excel():
    df = pd.DataFrame({"Detalle": ["a", "b"], "Día": ["04/03/2025", "05/03/2025"]})
    pcz = a.preparar_pcz(df, {"Descripción": "Detalle", "Fecha": "Día"})
    assert list(pcz["id"]) == ["2", "3"]


def test_hora_con_filas_vacias_se_muestra_bien():
    # Si algunas filas no tienen hora, pandas pasaba las horas a decimales (510.0) y fallaba
    df = pd.DataFrame({"Fecha": ["04/03/2025", "04/03/2025"], "Hora": ["08:30", None],
                       "Transcripción": ["a", "b"]})
    lg = a.preparar_lg(df, {"Fecha": "Fecha", "Hora": "Hora", "Transcripción": "Transcripción"})
    assert a.formatear_hora(lg.loc[0, "hora"]) == "08:30"
    assert a.formatear_hora(lg.loc[1, "hora"]) == ""
    assert a.formatear_hora(510.0) == "08:30" and a.formatear_hora(float("nan")) == ""


def test_hora_de_columna_pcz_suma_al_puntaje():
    df = pd.DataFrame({"Descripción": ["Falla señal 14", "Falla señal 14"], "Fecha": ["04/03/2025"] * 2,
                       "N° Novedad": [1, 2], "Hora": ["08:20", "15:00"]})
    pcz = a.preparar_pcz(df, {"Descripción": "Descripción", "Fecha": "Fecha", "N° Novedad": "N° Novedad",
                              "Hora": "Hora"})
    assert list(pcz["hora"]) == [8 * 60 + 20, 15 * 60]
    lg = pd.Series({"fecha": F(2025, 3, 4), "hora": 8 * 60 + 15, "texto": "Falla señal 14"})
    c = a.candidatos(lg, pcz)
    assert list(c["id"]) == ["1", "2"]  # la de hora cercana primero
    assert c.iloc[0]["puntaje"] == c.iloc[1]["puntaje"] + 3 and "hora a 5 min" in c.iloc[0]["detalle"]
