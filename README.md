# Ferrovías – Automatización de Excels

> **Uso diario (actualizar y abrir la app en casa o en el trabajo):** ver [GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md](GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md).

App local (Streamlit) para:
- **Cruzar** dos o más Excels/CSVs por una o más columnas clave (tipo clave primaria), aunque las columnas tengan nombres distintos en cada archivo.
- Elegir de cada documento qué columnas quedan en el resultado y **descargarlo** como `.xlsx`.

Módulos (menú a la izquierda):
- **Cruce de Excels**: lo de arriba.
- **Transcripciones del LG**: pasar a Excel el PDF escaneado del Libro de Guardia, con la IA de Claude (ver abajo).
- **Asociación LG ↔ PCZ**: asociar a mano cada párrafo del Libro de Guardia con las novedades del PCZ (ver abajo).
- **Concatenación**: pasar el CSV del reporte LibroNovedades a un Excel con una fila por novedad (ver abajo).

Corre en tu compu y se abre en el navegador en `http://localhost:8501`. Los Excels **nunca** se suben a GitHub (están en `.gitignore`).

## Instalación y uso

Los pasos para instalar, actualizar y abrir la app en cada computadora (Mac en casa, Windows en el
trabajo) están en [GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md](GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md).
En la compu del trabajo **no se usa `.venv`**: se abre con `py -3.13 -m streamlit run app.py`.

## Módulo: Asociación LG ↔ PCZ

Sirve para asociar las novedades del **PCZ** con los avisos del **Libro de Guardia (LG)** que les
corresponden, día por día. La app propone candidatos y vos elegís. Todo corre en tu compu: no usa IA ni internet.

**Archivos que necesita** (las columnas pueden llamarse como sea: al cargar elegís cuál es cada dato):
- **LG**: Fecha y Transcripción (cada fila es un párrafo; cada renglón es un aviso) y, si hay, Hora.
  Si tiene una columna «Página» (o «Pág»), se copia sola al Excel final (sin desplegable).
- **PCZ**: Fecha, Descripción, N° Novedad y, si hay, Hora. Además, si el archivo las tiene (se reconocen
  solas por nombre, sin desplegable), se copian al Excel final: Zona, VER, Falla, Comienzo de falla y
  Habilitación.
- **N° Novedad** es lo que identifica cada novedad. En la hoja `Asociaciones`, si una asociación tiene
  varias novedades, sus N° se juntan en la misma celda separados por ` | `. Si el archivo no tiene esa
  columna, se puede usar el número de fila del Excel.
- **Hora** (LG y PCZ, opcional): suma puntos a los avisos con hora cercana a la de la novedad, además
  de las horas escritas dentro de los textos.
- **Cómo se reconocen las columnas**: no es búsqueda aproximada, son reglas fijas sobre el encabezado
  (sin tildes, mayúsculas ni signos). La Hora de PCZ es la columna que empieza con «Hora»; si no hay
  ninguna, se usa «Comienzo de falla» (de su fecha y hora se toma solo la hora). Una misma columna puede
  usarse como Hora y además copiarse al Excel final. Siempre se puede cambiar a mano en el desplegable.

**Pasos**
1. **Carga**: subí los dos Excel y, debajo de cada uno, elegí qué columna es cada dato (si se llaman
   como siempre, ya vienen elegidas). La vista previa muestra cómo entiende la app cada fecha. Las
   filas con fecha que no se entiende se listan (no se descartan).
2. **Asociación**: la app recorre **los días del PCZ** (del más viejo al más nuevo). En cada día se
   ven **todas las novedades de PCZ de ese día** como una tabla: a la izquierda las novedades y a la
   derecha, en la misma línea, los avisos del LG asociados. Se trabaja en dos pasos:
   - **① Elegí las novedades de PCZ**: tildás una o varias (se unen en una misma asociación) y
     "Elegir avisos del LG", o **🗑️ Descartar** si no tienen nada en el LG. Si el día tiene una sola
     novedad, este paso se saltea.
   - **② Elegí los avisos del LG**: abajo aparecen **solo los avisos del LG de ese día** (cada renglón
     de una transcripción es un aviso), ordenados por parecido con las novedades elegidas (números
     compartidos como señal/cambio/km/tren = 3 puntos, palabras compartidas = 1, hora cercana = hasta
     3), con las coincidencias en amarillo. Los que tildás aparecen a la derecha; después tocás
     **Asociar**.
   - Lo ya resuelto **sigue a la vista en gris** hasta cambiar de día: las asociadas con sus avisos al
     lado ("🗑️ Quitar asociación" para deshacerla) y las descartadas solas ("↩️ Recuperar").
     Cuando no queda nada pendiente en el día, pasa solo al siguiente; en el último día el botón de
     arriba es "📥 Exportar".
   - Se muestran primero los 15 avisos con mejor puntaje; con "Mostrar 15 más" o "Mostrar todos"
     aparecen los demás (el buscador busca siempre entre todos).
   - Novedades y avisos se muestran como tarjetas: un clic en cualquier parte de la tarjeta la
     tilda o destilda (las elegidas se pintan de color).
   - A la izquierda de cada novedad de PCZ hay 3 botones chicos: **🗑️** la descarta al instante (solo
     esa, sin tocar lo tildado), **!** (amarillo) y **!!** (naranja) la marcan para que su fila salga
     **resaltada en ese color en el Excel final** (hoja «Asociaciones», esté asociada o no). Tocar otra vez el mismo botón saca la marca.
     Las novedades unidas (tildadas juntas o ya asociadas entre sí) llevan siempre la misma marca:
     marcar, cambiar el color o sacar la marca de una lo hace en todas. Si al asociar tenían marcas
     distintas, gana la naranja. Las novedades ya resueltas (en gris) muestran solo ! y !!.
   - Los botones de acción (Elegir avisos del LG / Asociar, Descartar, Todas, Volver) quedan **fijos abajo
     de la pantalla** mientras hacés scroll.
   - Atajos: **1–9** tildar novedad (paso ①) o aviso (paso ②) · **Enter** pasar al paso ② / asociar ·
     **D** descartar · **← →** día anterior/siguiente.
   - "Ver también día anterior / siguiente" (apagado por defecto) agrega esos avisos marcados como
     **OTRO DÍA**, para eventos que cruzan la medianoche.
   - Un aviso ya usado en otra asociación se puede elegir igual: se marca "ya asociado a N° …".
3. **Exportar**: descarga un Excel nuevo con 2 hojas:
   - **Asociaciones**: **todas las novedades de PCZ, ordenadas por día** (dentro del día, en el orden
     del PCZ; las de fecha no reconocida al final). Una fila por asociación (las novedades unidas de PCZ
     con sus avisos del LG) y una fila por cada novedad sin asociar (descartada o sin revisar), con una
     **estructura fija** igual a la tabla madre, para copiar las filas y pegarlas a continuación:
     N° · ID · Fecha · Mes · N° Novedad · Sistema · Subsistema · Parte · Elemento · Nombre correcto ·
     Km. INPAN · BuscarV (Km. INPAN) · Modelo · Página · Descripción · Zona · VER · Falla · Comienzo de falla ·
     Habilitación.
     - **N°**: consecutivo; el de la primera fila se escribe en pantalla y sube de a uno hacia abajo.
     - **Fecha**: la de la novedad de PCZ, con formato 19/9/2026.
     - **N° Novedad**: el de PCZ (si se unieron varias, separados por ` | `).
     - **Página**: la del LG de los avisos asociados (si son de varias páginas, separadas por ` | `;
       vacía si la novedad no tiene avisos).
     - **Descripción**: el texto de PCZ en MAYÚSCULAS, un renglón vacío y debajo el texto de los avisos
       del LG tal como viene (cada uno en su renglón). Si la novedad no tiene avisos, solo el texto de PCZ.
     - ID, Mes, Sistema, Subsistema, Parte, Elemento, Nombre correcto, Km. INPAN, BuscarV y Modelo
       van **vacías**, para completarlas después.
     - **Zona, VER, Falla, Comienzo de falla y Habilitación**: copiadas de PCZ tal como vienen (si se
       unieron varias novedades, sus valores distintos separados por ` | `; vacías si el PCZ no las tiene).
   - **LG sin asociar**: los avisos que no quedaron en ninguna asociación, con las columnas del Excel
     de LG.

**El progreso no se guarda**: lo asociado vive solo mientras la app está abierta. Si cerrás la app,
recargás la página o cargás otros archivos, se empieza de cero. Antes de cerrar, descargá el Excel en
**3. Exportar**. Los Excel originales nunca se modifican.

**Probarlo con datos inventados**: subí `tests/ejemplos/LG_ejemplo.xlsx` y `tests/ejemplos/PCZ_ejemplo.xlsx`
(se regeneran con `python tests/generar_ejemplos.py`). Tests: `python -m pytest`.

**Limitaciones conocidas**
- Fechas en texto se leen **siempre día primero** (DD/MM/AAAA, D/M/AA). Si en el Excel una fecha ya
  fue guardada mal como fecha (Excel la interpretó mes primero al tipearla), la app no puede saberlo.
- Se lee solo la **primera hoja** de cada Excel.
- El puntaje es una ayuda simple (coincidencia de números y palabras, sin sinónimos ni abreviaturas:
  "PAN" y "P.A.N." no coinciden). Siempre se muestran todas las novedades del día.
- Si cambiás de fila sin tocar «Asociar», lo tildado y no asociado se pierde.
- Una fila de LG sin fecha válida no tiene candidatos automáticos: hay que usar el buscador.
- Al exportar, las horas que venían como hora de Excel quedan como texto (ej. "08:15:00").

La configuración de la app está en `.streamlit/config.toml`: solo se abre en tu compu (`localhost`),
no manda estadísticas y no vigila los archivos (más rápido en discos de red; si se actualiza el código,
cerrá y volvé a abrir la app).

## Módulo: Concatenación (Libro de Novedades, CSV → Excel)

Convierte el CSV del reporte **LibroNovedades** (Reportes Grupo Emepa → Ferroviario → Operaciones →
transporte → PCZ) en un Excel con **una fila por número de novedad**. El CSV trae una fila por cada
renglón de texto; la app junta los renglones del mismo número. Todo corre en tu compu: no usa IA.

**Pasos**
1. Subí el CSV. El encoding en *Automático* sirve casi siempre (si las tildes o la Ñ se ven raras,
   elegí Windows-1252 o UTF-8).
2. Elegí las **palabras clave de fin** (viene tildada NORMAL; tocá las otras para sumarlas o escribí
   una nueva y tocá *Agregar*). La **hora fin** es la hora del último renglón que tiene alguna de esas
   palabras, buscadas solo en el texto, como palabras completas (NORMAL no coincide con ANORMAL ni con
   NORMALIZADO; «recibe via» tiene que estar junto y en ese orden). Se ignoran mayúsculas, tildes,
   puntuación y los **conectores** (de, el, la…, se editan en el desplegable; «no» y «sin» nunca).
3. Revisá la vista previa (la última columna muestra qué renglón marcó el fin; no va al Excel), poné
   el nombre del archivo y elegí cómo descargarlo:
   - **Tal como viene**: las 5 columnas una al lado de la otra.
   - **Formato de la hoja «Tabla»**: las 14 columnas de la hoja Tabla en su orden (Fecha, Mes,
     N° Novedad, Sistema, Subsistema, Parte, Elemento, Nombre correcto, Descripción, Zona, VER, Falla,
     Comienzo de falla, Habilitación), con datos solo en Fecha, N° Novedad, Descripción, Comienzo de
     falla y Habilitación. Para pegarlo sin borrar las fórmulas: copiá las filas (sin el encabezado),
     hacé clic en la celda de Fecha de la hoja Tabla, **Ctrl+Alt+V** → tildá **Saltar blancos** →
     Aceptar. Las celdas vacías no pisan lo que ya había.

El Excel tiene una hoja con: Nro novedad, Fecha, Hora inicio (primer renglón), Hora fin (vacía si
ningún renglón coincide) y Detalle (todos los renglones, uno por línea, tal cual vienen). Fecha y horas
son valores reales de Excel; hay filtros y el Detalle tiene *ajustar texto*.

**La configuración no se guarda**: las palabras y conectores que agregues duran hasta que cierres la
app. Cada CSV se procesa desde cero.

**Avisos**: archivo sin novedades, números de novedad separados por otros (se juntan igual), fechas u
horas inválidas (la celda queda vacía) y detalles de más de 32.767 caracteres (se recortan). Si el
encabezado `numero,Descripción_Estado,fecha,hora,descrip` no está, el archivo se rechaza.

**Probarlo con datos inventados**: subí `tests/ejemplos/LibroNovedades_ejemplo.csv` (se regenera con
`python tests/generar_ejemplo_concatenacion.py`).

## Módulo: Transcripciones del LG (PDF escaneado → Excel)

Transcribe el **Libro de Guardia de Señalamiento** (manuscrito, escaneado a PDF) a un Excel, usando la
API de Claude (lee la letra a mano en las imágenes). **Usa internet y cuesta plata**: hace falta la
clave de Anthropic en el archivo `.env` (`ANTHROPIC_API_KEY=...`, ver `.env.example`).

Tiene 3 secciones arriba:

**① Transcribir**
1. Subí el PDF. Opcional: la **fecha de contexto** (la del primer turno, por si la primera página no
   la muestra). Se ve cuántas páginas tiene, en cuántas tandas se manda y un costo estimado.
2. **▶️ Transcribir**. El PDF se manda en **tandas de 3 páginas** (fijo), de a una y en orden, con una
   barra «Tanda X de N». Cada tanda tarda 1-2 minutos. **No toques nada mientras trabaja**: si se
   corta, lo hecho queda y aparece «Continuar con las que faltan».
   - Cada página va como **imagen JPEG de 2576 px** de lado largo (el máximo que aprovecha el modelo):
     así la letra llega lo más nítida posible y la imagen que ves al revisar es exactamente la que
     leyó Claude. (Mandar el PDF tal cual no mejora nada: la API igual lo convierte en imágenes, sin
     dejar elegir la resolución.)
   - Cada tanda lleva: las instrucciones, la referencia, las imágenes y la **continuidad** (última
     fecha usada y el texto del último párrafo de la tanda anterior).
   - La respuesta es un JSON. Si viene mal armado, se reintenta **una vez**; si vuelve a fallar, la
     tanda queda con error y se sigue con las demás.
   - **Unión**: si una tanda trae `continuacion_del_anterior`, ese texto se pega al final de la
     última fila de la anterior y el folio pasa a «folio 18-19». Si una tanda terminó
     `cortado_al_final` y la siguiente no trae continuación, esa fila queda **para revisar** (⚠️).

**② Revisar y exportar**
- **Resumen**: filas, cantidad de `[?]` y `[ilegible]`, tandas con error, filas para revisar y el
  **costo real** (con los tokens, incluidos los reintentos).
- **Tandas**: estado de cada una y botón **🔁 Reintentar**. Como cada tanda usa el final de la
  anterior, al reintentar una se avisa que la siguiente puede quedar desalineada y se ofrece
  «Reintentar solo esta» o «Reintentar desde esta hasta el final».
- **Comparar con el libro**: elegís una fila; a la izquierda su texto (se corrige ahí) y a la derecha
  la página escaneada (ya elegida la que corresponde por el folio; se puede cambiar).
- **Tabla completa**: todas las filas, también editables con doble clic.
- **Exportar**: Excel con **una hoja y 4 columnas**: Folio (texto: «folio 18», «folio 18-19»,
  «folio 01 (libro nuevo)»), Fecha (fecha DD/MM/AAAA), Hora (HH:MM) y Transcripción (con los saltos
  de línea y *ajustar texto*). Nombre sugerido: `LG_transcripcion_<primera fecha>_<última fecha>.xlsx`.
- **Respuestas crudas del modelo**: lo que devolvió Claude en cada intento, tal cual, con el contexto
  que se le pasó (también se descargan en un `.json`).

Lo transcripto vive **solo mientras la app está abierta** (igual que Asociación LG ↔ PCZ): descargá el
Excel antes de cerrar. Si reintentás una tanda, se pierden las correcciones hechas a mano.

**⚙️ Configuración** (queda guardada)
- **Modelo**: Claude Opus 5.5 (por defecto, el mejor) o Claude Sonnet 5.5 (la mitad de precio).
- **Esfuerzo**: cuánto analiza Claude cada página antes de responder: bajo, medio, **alto** (por
  defecto) o muy alto. Más esfuerzo = lee la letra con más cuidado, pero tarda y cuesta más (ese
  análisis se cobra como salida). Queda guardado, igual que el modelo, y se ve en ① Transcribir y en
  las respuestas crudas de cada intento.
- **Conexión con Claude**: muestra si la app encontró la clave en el `.env` y el botón **🔌 Probar la
  conexión con Claude**, que comprueba la clave, que la red deje llegar a `api.anthropic.com` y que el
  modelo esté disponible, sin gastar crédito. Si en plena transcripción falla la clave, la conexión o
  el crédito, la app frena y explica qué pasó (las tandas que faltan se reintentan después).
- **Instrucciones** (`PROMPT_Sistema_Transcripcion_LG.md`, va como *system prompt*; define el formato
  del JSON) y **Documento de referencia** (`REFERENCIA_Transcripcion_LG.md`: jerga, letra de cada
  escritor, pasos a nivel). Se editan en pantalla y se **💾 Guardan**. Al lado se ve cuántos tokens
  tiene cada uno, con aviso si crece mucho (cada tanda lo manda entero; desde la 2.ª tanda sale más
  barato por la caché).
- Al guardar, la versión anterior va al **historial** (con fecha y hora): se puede ver y restaurar.
  **⏮️ Restaurar original** vuelve a la versión inicial (y lo que había también queda en el historial).
- La app **nunca** cambia estos documentos sola.
- Todo se guarda en `config/transcripcion_lg/` (`originales/` no se toca nunca, `historial/`, los
  documentos vigentes y `ajustes.json` con el modelo y el esfuerzo). **Esa carpeta va a git**: para llevar los
  cambios a la otra compu hay que subirlos a GitHub (ver la guía).

**Costo aproximado** (a ojo): con Opus 5.5 y esfuerzo alto, unos US$ 0,08 por página (un PDF de 11
páginas ≈ US$ 0,90; con esfuerzo medio ≈ US$ 0,70); con Sonnet 5.5, la mitad.

**Probarlo con datos inventados**: `tests/ejemplos/LG_ejemplo.pdf` es un libro inventado de 7 páginas
(se regenera con `python tests/generar_ejemplo_transcripcion.py`). Los PDFs reales **no se suben** a
GitHub (`*.pdf` está en `.gitignore`). Tests: `python -m pytest`.

## Trabajar desde dos computadoras

- Antes de empezar: `git pull`
- Al terminar: `git add . ; git commit -m "lo que hice" ; git push`

El `.env` (tu clave) y los Excels quedan solo en cada máquina; hay que crear el `.env` en cada una.

## Estructura

```
app.py                  # punto de entrada y menú de módulos
modulos/cruce.py        # pantalla: Cruce de Excels
modulos/transcripcion_lg.py   # pantalla: Transcripciones del LG (PDF escaneado → Excel con Claude)
src/transcripcion_lg.py       # lógica: PDF → imágenes, tandas, llamada a Claude, unión, Excel
config/transcripcion_lg/      # instrucciones y referencia de la transcripción (editables, van a git)
src/cruce.py            # lógica del cruce por coincidencias
modulos/asociacion_lg_pcz.py  # pantalla: Asociación LG ↔ PCZ
src/ia.py               # llamadas a Claude (relleno de columnas; hoy sin uso en el menú)
src/asociacion_lg_pcz.py      # lógica de la asociación (fechas, candidatos, exportación)
modulos/concatenacion.py      # pantalla: Concatenación (Libro de Novedades CSV → Excel)
src/concatenacion.py          # lógica: lectura del CSV, agrupación, hora fin, Excel
tests/                  # tests (python -m pytest) y Excels de ejemplo inventados
datos/          # poné acá tus Excels (ignorados por git)
```
