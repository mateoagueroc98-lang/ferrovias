# Ferrovías – Automatización de Excels

App local en **Python + Streamlit** para automatizar trabajo con Excels. Se abre en
`http://localhost:8501` desde la Mac de casa y las compus del trabajo, sincronizadas por GitHub (comandos exactos en
`GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md`):
- **Casa – Mac**: `~/ferrovias`, con `.venv` (`source .venv/bin/activate` + `streamlit run app.py`).
- **Trabajo – Windows**: `Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias`
  (unidad de red), con Git. **Sin `.venv`**: librerías con `py -3.13 -m pip install --user`, la app
  con `py -3.13 -m streamlit run app.py --server.headless true`. No pasarle comandos con `.venv`.
  Esa carpeta la usan **dos compus** (la de Mateo y la del jefe): un `git checkout` en una cambia la
  carpeta para las dos. Acceso directo del escritorio: `abrir_app_windows.bat` (siempre vuelve a `main`).

Es usuario no técnico: explicale en español, simple y con pasos concretos.

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
| Cruce de Excels | `modulos/cruce.py` | `src/cruce.py` | Terminado, **oculto del menú** (comentado en `app.py`) |
| Transcripciones del Libro de Guardia | `modulos/relleno_pdf.py` | — | En desarrollo |
| Asociación LG ↔ PCZ | `modulos/asociacion_lg_pcz.py` | `src/asociacion_lg_pcz.py` | MVP |
| Concatenación | `modulos/concatenacion.py` | `src/concatenacion.py` | MVP |
| Informes PowerPoint | `modulos/informes_pptx.py` | `src/informes_pptx/` (paquete) | Etapas 1 y 2 de 3 (plantillas, configuraciones) |

**Cruce de Excels**: subir 2+ Excels/CSV, ver sus columnas lado a lado, armar coincidencias
(documento + columna, una o varias, con 2+ documentos cada una), elegir documento principal y
qué filas conservar, tildar columnas finales por documento (botones Todas/Ninguna), cruzar y
descargar con nombre elegido. Las claves se normalizan (101 == 101.0, fechas sin hora, espacios).

**Asociación LG ↔ PCZ**: la principal es PCZ. Se recorre día por día (todos los días del PCZ): se
eligen una o varias novedades del día (se unen) y después los avisos del LG (cada renglón de la
transcripción) para asociarlas, o se descartan. Lo resuelto queda en gris hasta cambiar de día.
Candidatos solo de la MISMA fecha (fechas día primero, nunca MM/DD), ordenados por similitud simple
sin IA. El progreso vive solo en memoria (no hay sesiones guardadas en disco). Export con hojas
Asociaciones (una fila por asociación; estructura fija de 14 columnas `COLUMNAS_SALIDA`, N° consecutivo
desde el número que se elige, Fecha d/m/yyyy, Descripción = PCZ en MAYÚSCULAS + renglón vacío + LG), LG sin asociar y PCZ sin asociar
(columnas originales). Tests en `tests/` (`python -m pytest`); Excels inventados en `tests/ejemplos/`.

**Concatenación**: CSV del reporte LibroNovedades (una fila por renglón) → Excel con una fila por
número de novedad (Nro, Fecha, Hora inicio, Hora fin, Detalle). Hora fin = hora del último renglón cuyo
`descrip` contiene una palabra clave (palabras completas, en orden, sin tildes/puntuación/conectores;
«no» y «sin» nunca son conectores). Palabras clave y conectores se editan en pantalla y NO se guardan
entre usos. Dos descargas: tal como viene (5 columnas) y formato de la hoja «Tabla» del usuario
(`FORMATO_TABLA`, 14 columnas con vacías en el medio para pegar con «Saltar blancos» sin pisar fórmulas).
CSV inventado en `tests/ejemplos/LibroNovedades_ejemplo.csv`.

**Informes PowerPoint** (3 etapas: 1. plantillas ✅, 2. configuraciones ✅, 3. generación). Automatiza el
informe mensual que el jefe arma con capturas/gráficos del Excel. Lógica en el paquete `src/informes_pptx/`:
`plantillas.py` (detecta con python-pptx textos —también en grupos, marcadores y celdas de tabla— y lugares
de imagen —imágenes, gráficos, objetos incrustados, marcadores de imagen vacíos—; guarda/lista/duplica/elimina),
`reemplazo.py` (reemplaza un texto entero o un fragmento conservando el formato aunque esté partido en varios
runs), `esquema.py` (SVG con recuadros a escala), `configuraciones.py` (etapa 2: por lugar de imagen hoja +
rango o gráfico, modo captura/gráfico pegado —pegado solo si es gráfico—, ajuste encajar/ancho/alto centrado,
estilo vacío para la etapa 3; por variable texto libre con valor por defecto o celda `Hoja!D32`; validaciones
contra la plantilla y contra el Excel subido), `excel_zip.py` (lee hojas visibles/ocultas, gráficos —también
chartEx en mc:AlternateContent y dentro de grupos— y valores guardados directo del zip, sin Excel). **Solo
`office.py` (PowerPoint) y `excel.py` (Excel) usan COM** (Windows + pywin32), cada uno con versión simulada
para la Mac (`INFORMES_OFFICE=simulado` fuerza las dos). `excel.py`: instancia propia de Excel (DispatchEx)
invisible sobre una copia temporal, UpdateLinks=0, solo lectura, RefreshAll + CalculateUntilAsyncQueriesDone,
CopyPicture vectorial (EMF) → PNG al triple con Pillow (si falla, mapa de bits / Chart.Export), reintentos del
portapapeles, CoInitialize por ejecución y cierre sin guardar en try/finally (si no cierra, se mata solo ese
proceso); `exportar()` hace todo con una sola apertura. Se guarda en `informes/plantillas/<id>/` (base.pptx +
plantilla.json + miniaturas/ opcional) e `informes/configuraciones/<id>.json` (formato legible: `rango` o
`grafico`); `informes/` y `muestras/` (archivos reales) están en `.gitignore`. Una plantilla con
configuraciones no se puede eliminar. Diagnóstico: `python -m src.informes_pptx.excel_zip x.xlsx` (hojas y
gráficos) y en Windows `py -3.13 -m src.informes_pptx.excel x.xlsx "Hoja!A5:N41" "Hoja!Gráfico 3"` (capturas
de prueba en muestras/prueba_capturas/).
Cada lugar de imagen tiene id estable `img_DD_NN` escrito como nombre del shape en base.pptx; cada texto se
ubica por diapositiva + shape_id (+ celda). Ver lo detectado: `python -m src.informes_pptx.plantillas x.pptx`.
PowerPoint inventado en `tests/ejemplos/Informe_ejemplo.pptx` (`tests/generar_ejemplo_informe.py`) y Excel
inventado con treemap en `tests/ejemplos/Indicadores_ejemplo.xlsx` (`tests/generar_ejemplo_excel.py`).

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
