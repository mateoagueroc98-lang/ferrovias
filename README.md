# Ferrovías – Automatización de Excels

> **Uso diario (actualizar y abrir la app en casa o en el trabajo):** ver [GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md](GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md).

App local (Streamlit) para:
- **Cruzar** dos o más Excels/CSVs por una o más columnas clave (tipo clave primaria), aunque las columnas tengan nombres distintos en cada archivo.
- Elegir de cada documento qué columnas quedan en el resultado y **descargarlo** como `.xlsx`.

Módulos (menú a la izquierda):
- **Cruce de Excels**: lo de arriba.
- **Relleno de Excel mediante PDF**: en desarrollo.
- **Asociación LG ↔ PCZ**: asociar a mano cada párrafo del Libro de Guardia con las novedades del PCZ (ver abajo).
- **Libro de Novedades**: pasar el CSV del reporte LibroNovedades a un Excel con una fila por novedad (ver abajo).

Corre en tu compu y se abre en el navegador en `http://localhost:8501`. Los Excels **nunca** se suben a GitHub (están en `.gitignore`).

## Instalación en Windows (una vez por computadora)

1. Instalá **Python 3.11+** desde https://www.python.org/downloads/ (tildá *"Add python.exe to PATH"*).
2. Instalá **Git** desde https://git-scm.com/download/win.
3. Abrí *PowerShell* y cloná el repo:
   ```powershell
   cd $HOME\Documents
   git clone https://github.com/mateoagueroc98-lang/ferrovias.git
   cd ferrovias
   ```
4. Creá y activá un entorno virtual, e instalá dependencias:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   Si PowerShell bloquea el script de activación, corré una vez:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
5. Copiá `.env.example` a `.env` y pegá tu clave de API (https://console.anthropic.com/):
   ```powershell
   copy .env.example .env
   notepad .env
   ```

## Uso

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Se abre el navegador. Subí los archivos, armá las coincidencias, elegí las columnas finales y cruzá.

## Módulo: Asociación LG ↔ PCZ

Sirve para asociar cada fila del **Libro de Guardia (LG)** con la(s) novedad(es) del **PCZ** que le
corresponden. La app propone candidatos y vos elegís. Todo corre en tu compu: no usa IA ni internet.

**Archivos que necesita** (las columnas pueden llamarse como sea: al cargar elegís cuál es cada dato):
- **LG**: Fecha y Transcripción (cada fila es un párrafo; cada renglón es un aviso) y, si hay, Hora.
- **PCZ**: Fecha, Descripción, N° Novedad y, si hay, Hora.
- **N° Novedad** es lo que identifica cada novedad. En la hoja `Asociaciones`, si una asociación tiene
  varias novedades, sus N° se juntan en la misma celda separados por ` | `. Si el archivo no tiene esa
  columna, se puede usar el número de fila del Excel.
- **Hora** (LG y PCZ, opcional): suma puntos a las novedades con hora cercana a la del aviso, además
  de las horas escritas dentro de los textos.

**Pasos**
1. **Carga**: subí los dos Excel y, debajo de cada uno, elegí qué columna es cada dato (si se llaman
   como siempre, ya vienen elegidas). La vista previa muestra cómo entiende la app cada fecha. Las
   filas con fecha que no se entiende se listan (no se descartan).
2. **Asociación**: la app recorre LG fila por fila. Arriba están Anterior / Siguiente y el progreso.
   La fila se ve como una tabla: a la izquierda los avisos del Libro de Guardia y a la derecha, en la
   misma línea, las novedades de PCZ asociadas (o "pendiente" / "descartado"). Se trabaja en dos pasos:
   - **① Elegí los avisos**: tocás una o varias tarjetas de avisos y "Elegir novedades", o
     **🗑️ Descartar** si no tienen novedad en PCZ (se puede deshacer con "↩️ Recuperar"). Si la fila
     tiene un solo aviso sin resolver, este paso se saltea.
   - **② Elegí las novedades de PCZ**: abajo aparecen **solo las novedades con la misma fecha**,
     ordenadas por parecido con los avisos elegidos (números compartidos como señal/cambio/km/tren
     = 3 puntos, palabras compartidas = 1, hora cercana = hasta 3), con las coincidencias en amarillo.
     Las que tildás aparecen a la derecha de la "nueva asociación"; después tocás **Asociar**.
   - Cada asociación se guarda al instante (se puede quitar o deshacer). Cuando todos los avisos de
     la fila están asociados o descartados, pasa sola a la siguiente; si quedan, vuelve al paso ①.
   - Abajo: Deshacer, "Ir a…" (fila o próxima pendiente) y la ayuda de atajos.
   - Se muestran primero las 15 novedades con mejor puntaje; con "Mostrar 15 más" o "Mostrar todas"
     aparecen las demás (el buscador busca siempre entre todas).
   - Avisos y novedades se muestran como tarjetas: un clic en cualquier parte de la tarjeta la
     tilda o destilda (las elegidas se pintan de color).
   - Atajos: **1–9** tildar aviso (paso ①) o novedad (paso ②) · **Enter** pasar al paso ② / asociar ·
     **D** descartar · **← →** fila anterior/siguiente.
   - "Ver también día anterior / siguiente" (apagado por defecto) agrega esas novedades marcadas como
     **OTRO DÍA**, para eventos que cruzan la medianoche.
   - Las novedades ya asociadas a otra fila se marcan en azul; se pueden elegir igual (con aviso).
3. **Exportar**: descarga un Excel nuevo con 3 hojas:
   - **Asociaciones**: una fila por asociación. Las columnas y su orden se eligen en un menú antes de
     descargar (cualquier columna de LG o de PCZ, más "Descripción combinada" = descripción PCZ +
     texto LG en minúsculas, para la tabla de eventos RAMS, y "Fila LG"). La transcripción de LG trae
     solo los avisos de esa asociación y, si hay varios avisos o varias novedades, los valores se
     juntan en la misma celda separados por ` | `.
   - **LG sin asociar**: los avisos que no quedaron en ninguna asociación (descartados o sin revisar),
     con las mismas columnas del Excel de LG.
   - **PCZ sin asociar**: las novedades que no se usaron, con las mismas columnas del Excel de PCZ.

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

## Módulo: Libro de Novedades (CSV → Excel)

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
   el nombre del archivo y descargalo.

El Excel tiene una hoja con: Nro novedad, Fecha, Hora inicio (primer renglón), Hora fin (vacía si
ningún renglón coincide) y Detalle (todos los renglones, uno por línea, tal cual vienen). Fecha y horas
son valores reales de Excel; hay filtros y el Detalle tiene *ajustar texto*.

**La configuración no se guarda**: las palabras y conectores que agregues duran hasta que cierres la
app. Cada CSV se procesa desde cero.

**Avisos**: archivo sin novedades, números de novedad separados por otros (se juntan igual), fechas u
horas inválidas (la celda queda vacía) y detalles de más de 32.767 caracteres (se recortan). Si el
encabezado `numero,Descripción_Estado,fecha,hora,descrip` no está, el archivo se rechaza.

**Probarlo con datos inventados**: subí `tests/ejemplos/LibroNovedades_ejemplo.csv` (se regenera con
`python tests/generar_ejemplo_libro_novedades.py`).

## Trabajar desde dos computadoras

- Antes de empezar: `git pull`
- Al terminar: `git add . ; git commit -m "lo que hice" ; git push`

El `.env` (tu clave) y los Excels quedan solo en cada máquina; hay que crear el `.env` en cada una.

## Estructura

```
app.py                  # punto de entrada y menú de módulos
modulos/cruce.py        # pantalla: Cruce de Excels
modulos/relleno_pdf.py  # pantalla: Relleno de Excel mediante PDF (en desarrollo)
src/cruce.py            # lógica del cruce por coincidencias
modulos/asociacion_lg_pcz.py  # pantalla: Asociación LG ↔ PCZ
src/ia.py               # llamadas a Claude (para el módulo de relleno)
src/asociacion_lg_pcz.py      # lógica de la asociación (fechas, candidatos, exportación)
modulos/libro_novedades.py    # pantalla: Libro de Novedades (CSV → Excel)
src/libro_novedades.py        # lógica: lectura del CSV, agrupación, hora fin, Excel
tests/                  # tests (python -m pytest) y Excels de ejemplo inventados
datos/          # poné acá tus Excels (ignorados por git)
```
