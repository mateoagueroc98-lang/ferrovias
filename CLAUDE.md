# Ferrovías – Automatización de Excels

App local en **Python + Streamlit** para automatizar trabajo con Excels. El usuario la corre en
Windows (`streamlit run app.py`, se abre en `http://localhost:8501`) desde dos computadoras
(trabajo y casa), sincronizadas por GitHub. Es usuario no técnico: explicale en español, simple y
con pasos concretos.

## Estructura

```
app.py                  # punto de entrada: config de página + menú de módulos (st.navigation)
modulos/<modulo>.py     # una pantalla por módulo (solo interfaz)
src/<modulo>.py         # lógica de cada módulo (sin Streamlit, testeable)
src/ia.py               # llamadas a Claude (API de Anthropic), compartido
datos/                  # Excels locales del usuario (ignorados por git)
tests/                  # tests con pytest + tests/ejemplos/ (Excels INVENTADOS, sí se suben)
```

## Módulos

| Módulo (menú) | Pantalla | Lógica | Estado |
|---|---|---|---|
| Cruce de Excels | `modulos/cruce.py` | `src/cruce.py` | Terminado |
| Transcripciones del Libro de Guardia | `modulos/relleno_pdf.py` | — | En desarrollo |
| Asociación LG ↔ PCZ | `modulos/asociacion_lg_pcz.py` | `src/asociacion_lg_pcz.py` | MVP |

**Cruce de Excels**: subir 2+ Excels/CSV, ver sus columnas lado a lado, armar coincidencias
(documento + columna, una o varias, con 2+ documentos cada una), elegir documento principal y
qué filas conservar, tildar columnas finales por documento (botones Todas/Ninguna), cruzar y
descargar con nombre elegido. Las claves se normalizan (101 == 101.0, fechas sin hora, espacios).

**Asociación LG ↔ PCZ**: asociar a mano filas del Libro de Guardia con novedades del PCZ. Candidatos
solo de la MISMA fecha (fechas día primero, nunca MM/DD), ordenados por similitud simple sin IA.
El progreso vive solo en memoria (no hay sesiones guardadas en disco). Cada aviso se asocia o se descarta. Export con hojas
Asociaciones (columnas y orden elegidos), LG sin asociar y PCZ sin asociar (columnas originales). Tests en `tests/` (`python -m pytest`); Excels inventados en `tests/ejemplos/`.

## Reglas

- **Un módulo por sesión.** Al trabajar en un módulo, no modificar los archivos de otro módulo.
  Si hace falta tocar algo compartido (`app.py`, `src/ia.py`, `requirements.txt`, README), que
  sea un cambio mínimo y avisarle al usuario.
- **Agregar un módulo**: crear `modulos/<nombre>.py` y `src/<nombre>.py`, y sumar un
  `st.Page(...)` en `app.py`. No llamar `st.set_page_config` dentro de los módulos.
- Textos de la interfaz, comentarios y mensajes de commit **en español**.
- **Apariencia**: colores, fuente (Overpass, incluida en `static/fuentes/`), logo
  (`static/marca/ferrovias_logo.svg`) y menú lateral se definen en `.streamlit/config.toml` y `app.py`.
  Paleta de la marca Ferrovías: rojo `#D41920` (principal; el del logo es `#ED1E24`), degradados de
  `#E31B22` a `#9E1219` (menú y botones principales), fondo andén `#F4F3F2`, texto grafito `#1C1A19`;
  estados con colores de señal: verde `#2F7D4A`, amarillo `#C98A00`/`#FFE27A` (resaltado), rojo error
  `#B3261E`. Para cambios visuales usar la skill `frontend-design`.
- Nunca subir datos ni secretos: `.xlsx`, `.csv` y `.env` están en `.gitignore`. La clave de
  Anthropic va en `.env` (`ANTHROPIC_API_KEY`), ver `.env.example`.
- Dependencias nuevas → `requirements.txt` y avisar al usuario que corra
  `pip install -r requirements.txt`.
- Antes de subir cambios de interfaz: correr la app y probarla con Excels de ejemplo inventados
  (Playwright + Chromium preinstalado) y mostrarle capturas al usuario.
- Ramas: `main` es la versión estable. Cada sesión trabaja en su rama y los cambios entran a
  `main` por pull request.
