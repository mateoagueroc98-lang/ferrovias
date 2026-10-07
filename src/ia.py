"""Relleno de celdas vacías usando la API de Anthropic."""
import os

import anthropic
import pandas as pd

MODELO = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")


def rellenar_columna(df: pd.DataFrame, columna: str, instruccion: str, contexto: list[str]) -> pd.DataFrame:
    """Completa las celdas vacías de `columna` fila por fila.

    instruccion: qué tiene que poner Claude (ej. "Clasificá el material en ...").
    contexto: columnas de la misma fila que Claude puede leer para decidir.
    """
    client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno / .env
    df = df.copy()
    if columna not in df.columns:
        df[columna] = None

    vacias = df[columna].isna() | (df[columna].astype(str).str.strip() == "")
    for idx in df.index[vacias]:
        datos_fila = "\n".join(f"{c}: {df.at[idx, c]}" for c in contexto)
        response = client.beta.messages.create(
            model=MODELO,
            max_tokens=1024,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system="Completás una celda de una planilla. Respondé solo con el valor, sin explicaciones.",
            messages=[{
                "role": "user",
                "content": f"{instruccion}\n\nDatos de la fila:\n{datos_fila}\n\nValor para '{columna}':",
            }],
        )
        if response.stop_reason == "refusal":
            continue
        texto = "".join(b.text for b in response.content if b.type == "text").strip()
        df.at[idx, columna] = texto
    return df
