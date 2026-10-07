"""Cruce (merge) de varias tablas por columnas clave."""
import datetime as dt

import pandas as pd

TIPOS = {
    "Todas las filas del principal": "left",
    "Solo filas que coinciden": "inner",
    "Todas las filas de ambos": "outer",
}


def _normalizar_valor(v):
    """Lleva un valor a texto comparable: 123 == 123.0 == " 123 ", fechas sin hora."""
    if pd.isna(v):
        return None
    if isinstance(v, (pd.Timestamp, dt.datetime)):
        return v.strftime("%Y-%m-%d") if v.time() == dt.time(0) else v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, dt.date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def normalizar(serie: pd.Series) -> pd.Series:
    return serie.map(_normalizar_valor)


def cruzar_varios(tablas: list[tuple[str, pd.DataFrame]], uniones: list[dict]):
    """Une las tablas en cadena: la 1ª con la 2ª, el resultado con la 3ª, etc.

    uniones[i] describe cómo se une tablas[i + 1]:
      {"pares": [((idx_tabla_anterior, columna), columna_de_esta_tabla), ...],
       "tipo": "left" | "inner" | "outer"}

    Devuelve (resultado, resumen) donde resumen es una lista de dicts con
    cuántas filas coincidieron en cada unión.
    """
    nombre0, df0 = tablas[0]
    resultado = df0.copy()
    # (idx_tabla, columna original) -> nombre de la columna en `resultado`
    ubicacion = {(0, c): c for c in df0.columns}
    resumen = []

    for i, (nombre, df) in enumerate(tablas[1:], start=1):
        union = uniones[i - 1]
        der = df.copy()

        # Renombrar columnas que ya existen en el resultado para no pisarlas
        renombres = {c: f"{c} ({nombre})" for c in der.columns if c in resultado.columns}
        der = der.rename(columns=renombres)
        for c in df.columns:
            ubicacion[(i, c)] = renombres.get(c, c)

        claves = []
        for k, ((idx_izq, col_izq), col_der) in enumerate(union["pares"]):
            clave = f"__clave{k}"
            resultado[clave] = normalizar(resultado[ubicacion[(idx_izq, col_izq)]])
            der[clave] = normalizar(der[ubicacion[(i, col_der)]])
            claves.append(clave)

        resultado = resultado.merge(der, on=claves, how=union["tipo"], indicator=True)
        conteo = resultado["_merge"].value_counts()
        resumen.append({
            "archivo": nombre,
            "coinciden": int(conteo.get("both", 0)),
            "sin coincidencia (anterior)": int(conteo.get("left_only", 0)),
            "sin coincidencia (este archivo)": int(conteo.get("right_only", 0)),
        })
        resultado = resultado.drop(columns=claves + ["_merge"])

    return resultado, resumen
