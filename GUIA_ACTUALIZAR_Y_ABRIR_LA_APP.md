# Guía: actualizar el proyecto y abrir la app

Pasos para traer los últimos cambios de GitHub y usar la app en cada computadora.

- [Casa – Mac](#casa--mac)
- [Trabajo – Windows](#trabajo--windows)

---

## Casa – Mac

Todo se hace en la app **Terminal** (`Cmd + Espacio`, escribir `Terminal`, Enter).

### Uso de todos los días

Copiar y pegar de a una línea:

```bash
cd ~/ferrovias
git checkout main
git pull
source .venv/bin/activate
streamlit run app.py
```

Qué hace cada línea:

| Comando | Para qué sirve |
|---|---|
| `cd ~/ferrovias` | Entra a la carpeta del proyecto (`/Users/mateoaguero/ferrovias`). La línea tiene que terminar en `ferrovias %`. |
| `git checkout main` | Se asegura de estar en `main`, la versión estable. |
| `git pull` | Trae de GitHub los últimos cambios. |
| `source .venv/bin/activate` | Activa el Python del proyecto. La línea empieza con `(.venv)`. |
| `streamlit run app.py` | Abre la app. |

- La app se abre sola en el navegador en `http://localhost:8501` (si no, pegar esa dirección).
- **No cerrar la Terminal** mientras se usa la app: corre ahí.
- Para apagarla: `Ctrl + C` en la Terminal (Control, no Cmd).
- No tocar el botón **Deploy** de la app (la publicaría en internet).

### Si después de `git pull` aparece un error de que falta algo

Se agregó alguna librería nueva. Con el `(.venv)` activo:

```bash
pip install -r requirements.txt
```

y volver a correr `streamlit run app.py`.

### Probar cambios que todavía no están en `main`

Cuando una sesión de Claude Code está trabajando en un módulo, sus cambios quedan en una
**rama** propia (por ejemplo `claude/modulo-lg-pcz-asociacion-...`) hasta que se unen a `main`.
Para probarlos antes:

```bash
cd ~/ferrovias
git fetch
git checkout NOMBRE-DE-LA-RAMA
git pull
source .venv/bin/activate
streamlit run app.py
```

El nombre de la rama se ve en GitHub, en la pestaña **Pull requests** o en el menú de ramas.
Para volver a la versión estable: `git checkout main`.

### Empezar de cero en el módulo Asociación LG ↔ PCZ

La app ya no guarda asociaciones: alcanza con **recargar la página** (o cerrar y volver a abrir la
app). Ojo: lo que no hayas descargado en **3. Exportar** se pierde.

### Instalación (solo la primera vez en esta Mac)

> Ya está hecha. Queda anotada por si hay que rehacerla.

1. **Git**: ya viene; se comprueba con `git --version`.
2. **Python 3.13** desde https://www.python.org/downloads/macos/ (no usar 3.15: algunas
   librerías todavía no funcionan). Después de instalar, doble clic en
   *Aplicaciones → Python 3.13 → Install Certificates.command*.
3. En la Terminal:

   ```bash
   cd ~
   git clone https://github.com/mateoagueroc98-lang/ferrovias.git
   cd ferrovias
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   En esta Mac el comando `python3` es la versión vieja (3.9) que trae el sistema: por eso
   se usa `python3.13` para crear el `.venv`. Una vez activado, `python` ya es el correcto.

4. *(Opcional, para módulos con IA)*: `cp .env.example .env` y `open -e .env` para pegar la
   clave de Anthropic.

---

## Trabajo – Windows

La carpeta del proyecto está en la unidad de red y está conectada a GitHub con Git:

```
Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias
```

### Uso de todos los días

**Con doble clic:** el archivo `abrir_app_windows.bat` (en la carpeta `ferrovias`) hace todo lo de
abajo. Para tenerlo en el escritorio: clic derecho en el archivo → **Enviar a** → **Escritorio
(crear acceso directo)**. Para cerrar la app: `Ctrl + C` en la ventana negra (o cerrarla).

**A mano:** abrir la ventana negra (tecla Windows → escribir `cmd` → Enter), en cualquier carpeta, y pegar
el bloque entero:

```
cd /d "Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias"
git checkout main
git pull
start "" cmd /c "timeout /t 10 >nul & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
```

| Línea | Para qué sirve |
|---|---|
| `cd /d "Y:\...\ferrovias"` | Entra a la carpeta del proyecto, desde donde se esté. |
| `git checkout main` | Se asegura de estar en `main`, la versión estable. |
| `git pull` | Trae de GitHub los últimos cambios. |
| `start "" cmd /c "timeout ... chrome ..."` | Espera 10 segundos a que arranque la app y la abre en Chrome. |
| `py -3.13 -m streamlit run ...` | Abre la app (no se usa `.venv`: las librerías están instaladas en el usuario). |

- Si Chrome muestra «No se puede acceder a este sitio», esperar unos segundos y apretar **F5**:
  desde la unidad de red la app tarda en arrancar.
- **No cerrar la ventana negra** mientras se usa la app: corre ahí. Para apagarla: `Ctrl + C`.
- No tocar el botón **Deploy** de la app (la publicaría en internet).

### Si después de `git pull` aparece un error de que falta algo

Se agregó alguna librería nueva (dice `No module named ...`). En la ventana negra:

```
cd /d "Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias"
py -3.13 -m pip install --user -r requirements.txt
```

y volver a pegar el bloque de todos los días.

### Probar cambios que todavía no están en `main`

```
cd /d "Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias"
git fetch
git checkout NOMBRE-DE-LA-RAMA
git pull
py -3.13 -m streamlit run app.py --server.headless true
```

Para volver a la versión estable, usar de nuevo el bloque de todos los días (empieza con
`git checkout main`).

### Empezar de cero en el módulo Asociación LG ↔ PCZ

Igual que en la Mac: recargar la página o volver a abrir la app (no hay nada guardado que borrar).

### Instalación (solo la primera vez en esta compu)

> Ya está hecha. Queda anotada por si hay que rehacerla (por ejemplo, con otro usuario de Windows:
> Python, librerías y configuración de Git son de cada usuario).

1. **Python 3.13**: bajar el *Python Install Manager* de https://www.python.org/downloads/windows/.
   Si la configuración avisa por los *alias de ejecución de aplicaciones*, activar
   *Python (default)* y *Python install manager*. Después, en `cmd`: `py install 3.13`.
2. **Git** desde https://git-scm.com/download/win (opciones por defecto).
3. En esta compu la carpeta personal (`HOME`) apunta a `Y:\`, donde no se puede escribir. Para que
   Git guarde su configuración en `C:` y no desconfíe de la unidad de red («dubious ownership»):

   ```
   setx HOME "%USERPROFILE%"
   ```

   cerrar la ventana negra, abrir una nueva y:

   ```
   git config --global --add safe.directory "*"
   ```

4. Bajar el proyecto: abrir `cmd` en la carpeta `Claude` y

   ```
   git clone https://github.com/mateoagueroc98-lang/ferrovias.git
   ```

5. Instalar las librerías (en el usuario, sin `.venv`: en la unidad de red sería lento):

   ```
   cd ferrovias
   py -3.13 -m pip install --user -r requirements.txt
   ```

6. *(Opcional, para módulos con IA)*: `copy .env.example .env` y `notepad .env` para pegar la
   clave de Anthropic.
