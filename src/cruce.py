"""Cruce (merge) de varias tablas por coincidencias de columnas."""
import datetime as dt

import pandas as pd

TIPOS = {
    "Todas las filas del documento principal": "left",
    "Solo filas que coinciden en todos": "inner",
    "Todas las filas de todos los documentos": "outer",
}

SEP = "::"  # separador interno documento::columna


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


def _fechas_sin_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas de fecha cuyos valores no tienen hora -> solo fecha (sin 00:00:00)."""
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            s = df[c].dropna()
            if (s == s.dt.normalize()).all():
                df[c] = df[c].dt.date
    return df


def cruzar(
    tablas: dict[str, pd.DataFrame],
    coincidencias: list[list[tuple[str, str]]],
    principal: str,
    tipo: str,
    columnas_finales: dict[str, list[str]],
):
    """Une todos los documentos según las coincidencias.

    coincidencias: cada una es una lista de (documento, columna) cuyos valores
        tienen que ser iguales, ej. [("eventos", "N° INFRA"), ("mant", "Infraestructura")].
    principal: documento desde el que se arranca.
    tipo: "left" | "inner" | "outer".
    columnas_finales: por documento, qué columnas quedan en el resultado (en orden).

    Devuelve (resultado, resumen). Lanza ValueError si algún documento no está
    conectado al resto por ninguna coincidencia.
    """
    def prefijar(doc):
        return tablas[doc].rename(columns=lambda c: f"{doc}{SEP}{c}")

    unidos = [principal]
    resultado = prefijar(principal)
    pendientes = [d for d in tablas if d != principal]
    resumen = []

    while pendientes:
        # Siguiente documento que tenga al menos una coincidencia con los ya unidos
        for doc in pendientes:
            pares = []
            for coinc in coincidencias:
                docs = dict(coinc)
                if doc in docs:
                    izq = next((d for d, _ in coinc if d in unidos), None)
                    if izq is not None:
                        pares.append((f"{izq}{SEP}{docs[izq]}", f"{doc}{SEP}{docs[doc]}"))
            if pares:
                break
        else:
            raise ValueError(
                "Estos documentos no tienen ninguna coincidencia con los demás: "
                + ", ".join(pendientes)
            )

        der = prefijar(doc)
        claves = []
        for k, (col_izq, col_der) in enumerate(pares):
            clave = f"__clave{k}"
            resultado[clave] = normalizar(resultado[col_izq])
            der[clave] = normalizar(der[col_der])
            claves.append(clave)

        resultado = resultado.merge(der, on=claves, how=tipo, indicator=True)
        conteo = resultado["_merge"].value_counts()
        resumen.append({
            "documento": doc,
            "unido por": " + ".join(f"{a.split(SEP, 1)[1]} = {b.split(SEP, 1)[1]}" for a, b in pares),
            "filas que coinciden": int(conteo.get("both", 0)),
            "sin coincidencia (ya unidos)": int(conteo.get("left_only", 0)),
            "sin coincidencia (este documento)": int(conteo.get("right_only", 0)),
        })
        resultado = resultado.drop(columns=claves + ["_merge"])
        unidos.append(doc)
        pendientes.remove(doc)

    # Columnas finales: nombre original; si se repite entre documentos, "col (doc)"
    elegidas = [(d, c) for d in tablas for c in columnas_finales.get(d, [])]
    nombres = [c for _, c in elegidas]
    renombre = {
        f"{d}{SEP}{c}": (c if nombres.count(c) == 1 else f"{c} ({d})") for d, c in elegidas
    }
    resultado = resultado[list(renombre)].rename(columns=renombre)
    return _fechas_sin_hora(resultado), resumen
