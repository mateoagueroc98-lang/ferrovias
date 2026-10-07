"""Cruce (merge) de tablas por columnas clave."""
import pandas as pd


def cruzar(izq: pd.DataFrame, der: pd.DataFrame, claves: list[str], tipo: str = "left") -> pd.DataFrame:
    """Une dos tablas por las columnas clave indicadas.

    tipo: "left" (todas las filas de la izquierda), "inner" (solo coincidencias),
    "outer" (todas las filas de ambas) o "right".
    """
    # Normalizar claves a texto sin espacios para evitar falsos "no coincide"
    # (ej. 123 vs "123" vs " 123 ").
    izq = izq.copy()
    der = der.copy()
    for c in claves:
        izq[c] = izq[c].astype(str).str.strip()
        der[c] = der[c].astype(str).str.strip()
    return izq.merge(der, on=claves, how=tipo, suffixes=("", "_der"), indicator=True)
