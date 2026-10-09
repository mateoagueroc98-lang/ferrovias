# Ferrovías – Automatización de Excels

App local (Streamlit) para:
- **Cruzar** dos o más Excels/CSVs por una o más columnas clave (tipo clave primaria), aunque las columnas tengan nombres distintos en cada archivo.
- Elegir de cada documento qué columnas quedan en el resultado y **descargarlo** como `.xlsx`.

Módulos (menú a la izquierda):
- **Cruce de Excels**: lo de arriba.
- **Relleno de Excel mediante PDF**: en desarrollo.
- **Asociación LG ↔ PCZ**: asociar a mano cada párrafo del Libro de Guardia con las novedades del PCZ (ver abajo).

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

**Archivos que necesita** (los nombres de columna toleran mayúsculas, tildes y espacios; ej. "N° Novedad",
"Nº Novedad", "N Novedad", "Descripcion"):
- **LG**: `Página | Fecha | Hora | Transcripción` — cada fila es un párrafo; cada renglón de la
  transcripción es un aviso.
- **PCZ**: `Descripción | Fecha | N° Novedad` — el N° de Novedad identifica cada fila.

**Pasos**
1. **Carga**: subí los dos Excel. Si falta una columna, la app dice cuál. Las filas con fecha que no
   se entiende se listan (no se descartan).
2. **Asociación**: la app recorre LG fila por fila. Abajo aparecen **solo las novedades de PCZ con la
   misma fecha**, ordenadas por puntaje (números compartidos como señal/cambio/km/tren = 3 puntos,
   palabras compartidas = 1, hora cercana = hasta 3), con las coincidencias resaltadas en amarillo.
   Tildá una o varias y confirmá, o marcá "Ninguna corresponde". Si un párrafo tiene varios avisos,
   podés indicar a qué aviso corresponde cada novedad (si no, se usa el párrafo entero).
   - Atajos: **1–9** tildar candidato · **Enter** confirmar y siguiente · **← →** anterior/siguiente ·
     **N** ninguna · **S** saltar (queda pendiente).
   - "Ver también día anterior / siguiente" (apagado por defecto) agrega esas novedades marcadas como
     **OTRO DÍA**, para eventos que cruzan la medianoche.
   - Las novedades ya asociadas a otra fila se marcan en azul; se pueden elegir igual (con aviso).
3. **Exportar**: descarga un Excel nuevo con las hojas `LG_asociado`, `PCZ_completado` (con
   "Texto LG" y "Descripción combinada" = descripción PCZ + texto LG en minúsculas, para la tabla de
   eventos RAMS) y `Resumen`.

**Guardado**: el progreso se guarda solo en `datos/sesiones/` (no se sube a GitHub). Si cerrás la app y
volvés a subir **los mismos dos archivos**, sigue donde quedaste. En el paso 1 podés exportar la
sesión (.json) para llevarla a la otra compu e importarla allá. Los Excel originales nunca se modifican.

**Probarlo con datos inventados**: subí `tests/ejemplos/LG_ejemplo.xlsx` y `tests/ejemplos/PCZ_ejemplo.xlsx`
(se regeneran con `python tests/generar_ejemplos.py`). Tests: `python -m pytest`.

**Limitaciones conocidas**
- Fechas en texto se leen **siempre día primero** (DD/MM/AAAA, D/M/AA). Si en el Excel una fecha ya
  fue guardada mal como fecha (Excel la interpretó mes primero al tipearla), la app no puede saberlo.
- Se lee solo la **primera hoja** de cada Excel.
- El puntaje es una ayuda simple (coincidencia de números y palabras, sin sinónimos ni abreviaturas:
  "PAN" y "P.A.N." no coinciden). Siempre se muestran todas las novedades del día.
- Si cambiás algo en un Excel (aunque sea una celda), la app lo toma como archivos nuevos y empieza una
  sesión nueva: usá "Importar sesión" con el .json exportado para recuperar lo hecho.
- Si cambiás de fila sin confirmar, lo tildado y no confirmado se pierde.
- Una fila de LG sin fecha válida no tiene candidatos automáticos: hay que usar el buscador.
- Al exportar, las horas que venían como hora de Excel quedan como texto (ej. "08:15:00").

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
src/asociacion_lg_pcz.py      # lógica de la asociación (fechas, candidatos, sesión, exportación)
tests/                  # tests (python -m pytest) y Excels de ejemplo inventados
datos/          # poné acá tus Excels (ignorados por git)
```
