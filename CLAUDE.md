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
  Para crear o cambiar accesos directos (`.bat`) seguir las reglas de la sección «Accesos directos» de
  la guía: los de ramas van **afuera** de `ferrovias`, en `Claude\accesos app` (con
  `cd /d "%~dp0..\ferrovias"`), `%~dp0` en vez de la ruta, sin tildes, `>NUL` (nunca
  `/dev/null`), fin de línea CRLF.

Es usuario no técnico: explicale en español, simple y con pasos concretos.

## Cómo trabajar con el usuario

- El proyecto lo siguen **Mateo** (pasante) y **su jefe**, desde **cuentas de Claude distintas**. No
  hay memoria compartida entre cuentas: todo lo que haga falta saber tiene que estar en este archivo,
  en `COMO_TRABAJAR_EN_EL_PROYECTO.md` (guía para personas) o en la guía de abrir la app. Si el usuario
  no dice quién es, no lo supongas: tratalo igual y usá lenguaje neutro.
- **Cada sesión trabaja en su rama**, partiendo de `main` actualizado. Al terminar, pull request a
  `main`. **Unir a `main` solo cuando el usuario lo pide** («pasalo a main», «unilo»).
- **Siempre decir cómo probarlo** en las compus del trabajo: para una rama, pasarle el `.bat` para
  `Claude\accesos app` según el modelo de la guía (sección «Accesos directos»), además de los
  comandos. Nunca un comando para Windows sin la línea que abre Chrome.
- Si hay **librerías nuevas**, avisar que en cada compu y usuario de Windows hay que correr una vez
  `py -3.13 -m pip install --user -r requirements.txt` (en la Mac: `pip install -r requirements.txt`).
- Las compus del trabajo **solo descargan** de GitHub (no tienen `git push` configurado): los cambios
  los sube la sesión de Claude, no el usuario.
- El repositorio es **público**: nada de datos reales (novedades, nombres de personas) en código,
  tests ni documentación; los ejemplos son inventados.
- Prompts para arrancar sesiones: `PROMPTS_PARA_EMPEZAR.md`.
- **Dos formas de trabajar** (el proyecto es el mismo en las dos):
  - **Con GitHub** (cuenta de Mateo, sesiones en la nube): rama por sesión, pull request, unir a
    `main` solo si se pide, `.bat` de prueba en `accesos app`.
  - **Directo en la carpeta compartida** (cuenta del jefe, Claude en la compu del trabajo, sin GitHub):
    se edita la carpeta `Y:\...\Claude\ferrovias`, que usan **las dos compus a la vez**. No hay ramas,
    pull requests ni `git push`. Antes de cambiar nada, `git status` y `git commit` de lo que haya (punto
    de restauración); después de cada cambio que funcione, otro `git commit` con mensaje en español.
    Correr los tests antes de dar algo por terminado. Avisar que para ver el cambio hay que **cerrar y
    volver a abrir la app** (no vigila archivos). No cambiar de rama en esa carpeta. Si `git pull` de
    los accesos directos da error porque ya no hay GitHub, no es grave: la app abre igual.
  - Cómo darse cuenta: si `git remote -v` no muestra GitHub, o la sesión corre en la carpeta de `Y:`,
    es el modo carpeta compartida.

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
| Transcripciones del LG | `modulos/transcripcion_lg.py` | `src/transcripcion_lg.py` | MVP |
| Asociación LG ↔ PCZ | `modulos/asociacion_lg_pcz.py` | `src/asociacion_lg_pcz.py` | MVP |
| Concatenación | `modulos/concatenacion.py` | `src/concatenacion.py` | MVP |

**Cruce de Excels**: subir 2+ Excels/CSV, ver sus columnas lado a lado, armar coincidencias
(documento + columna, una o varias, con 2+ documentos cada una), elegir documento principal y
qué filas conservar, tildar columnas finales por documento (botones Todas/Ninguna), cruzar y
descargar con nombre elegido. Las claves se normalizan (101 == 101.0, fechas sin hora, espacios).

**Asociación LG ↔ PCZ**: la principal es PCZ. Se recorre día por día (todos los días del PCZ): se
eligen una o varias novedades del día (se unen) y después los avisos del LG (cada renglón de la
transcripción) para asociarlas, o se descartan. Lo resuelto queda en gris hasta cambiar de día.
Cada novedad tiene a la izquierda 🗑️ (descartar solo esa) y ! / !! (marca amarilla / naranja: resalta su
fila en el Excel final; las novedades unidas —tildadas juntas o asociadas— comparten la marca, y al
asociar con marcas distintas gana la naranja).
«📅 Unir con otro día» (st.dialog): suma novedades de PCZ de otros días al grupo, con Fecha y N° Novedad
elegidos para el Excel (`fecha`/`numero` en la asociación, y `extras` con los valores elegidos de
Comienzo de falla / Habilitación: `ELEGIBLES_UNION`); el paso ② propone avisos de todos esos días.
Candidatos solo de la MISMA fecha (fechas día primero, nunca MM/DD), ordenados por similitud simple
sin IA. El progreso vive solo en memoria (no hay sesiones guardadas en disco). Export con hojas
Asociaciones (TODAS las novedades de PCZ ordenadas por día: una fila por asociación y una por novedad sin
asociar; estructura fija de 20 columnas `COLUMNAS_SALIDA`, con «Página» del LG antes de «Descripción» y las últimas 5
copiadas de PCZ: `EXTRAS_PCZ`, N° consecutivo desde el número que se elige,
Fecha d/m/yyyy, Descripción = PCZ en MAYÚSCULAS + renglón vacío + LG) y LG sin asociar (columnas originales). Tests en `tests/` (`python -m pytest`); Excels inventados en `tests/ejemplos/`.

**Transcripciones del LG**: PDF escaneado del Libro de Guardia → Excel con la API de Claude (visión).
Páginas → JPEG de 2576 px (`pypdfium2`), en tandas FIJAS de 3, de a una y en orden, en un **hilo de
fondo** (`tl.trabajar`): se puede navegar mientras transcribe; un `st.fragment(run_every=2)` muestra el
avance, manda el «latido» (sin latido 90 s → el hilo se frena) y refresca al llegar cada tanda. Cada tanda
recibe última fecha + último párrafo de la anterior. System = instrucciones + referencia (con caché). JSON
validado; si viene mal, 1 reintento y si no, tanda con error. Unión: `continuacion_del_anterior` se pega a
la última fila (folio «X-Y»); `cortado_al_final` sin continuación (siguiente ya hecha) → fila para revisar.
① nombre del Excel = «Transcripciones de [fecha] a [fecha]» (Enter salta de fecha; la 1.ª es la fecha de
contexto), en gris mientras transcribe. ② Proceso (barra por tiempo restante, solo tandas fallidas con
Reintentar), resumen, revisión por folio (`paginas_revisables`; palabra + `[?]` en amarillo y `[ilegible]` en rojo claro con `marcar_dudosos`, ✏️ Corregir abre el editor) con corrección guardada por clave de
fila (`tanda:orden`; `aplicar_correccion` suma continuaciones que lleguen después) y vista previa. Sin
respuestas crudas en pantalla. Todo en memoria: recargar = perder todo. Excel de 1 hoja: Folio (texto) |
Fecha (DD/MM/AAAA) | Hora (HH:MM) | Transcripción (ajustar texto). Los 2 documentos, el modelo y el
esfuerzo (`low`/`medium`/`high`/`xhigh`, por defecto `high`; botón Guardar) se editan en ⚙️ Configuración
y se guardan en `config/transcripcion_lg/` (SÍ va a git; con `originales/`, SIN historial de versiones); la app nunca
los modifica sola. Saldo de la API cargado a mano en ⚙️ y descontado por tanda (`saldo.json`, NO va a
git; la API no permite consultarlo). PDF inventado en `tests/ejemplos/LG_ejemplo.pdf`.

**Concatenación**: CSV del reporte LibroNovedades (una fila por renglón) → Excel con una fila por
número de novedad (Nro, Fecha, Hora inicio, Hora fin, Detalle). Hora fin = hora del último renglón cuyo
`descrip` contiene una palabra clave (palabras completas, en orden, sin tildes/puntuación/conectores;
«no» y «sin» nunca son conectores). Palabras clave y conectores se editan en pantalla y NO se guardan
entre usos. Dos descargas: tal como viene (5 columnas) y formato de la hoja «Tabla» del usuario
(`FORMATO_TABLA`, 14 columnas con vacías en el medio para pegar con «Saltar blancos» sin pisar fórmulas).
CSV inventado en `tests/ejemplos/LibroNovedades_ejemplo.csv`.

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
- Nunca subir datos ni secretos: `.xlsx`, `.csv`, `.pdf` y `.env` están en `.gitignore`. La clave de
  Anthropic va en `.env` (`ANTHROPIC_API_KEY`), ver `.env.example`.
- Dependencias nuevas → `requirements.txt` y avisar al usuario que corra
  `pip install -r requirements.txt`.
- Antes de subir cambios de interfaz: correr la app y probarla con Excels de ejemplo inventados
  (Playwright + Chromium preinstalado) y mostrarle capturas al usuario.
- Ramas: `main` es la versión estable. Cada sesión trabaja en su rama y los cambios entran a
  `main` por pull request.
