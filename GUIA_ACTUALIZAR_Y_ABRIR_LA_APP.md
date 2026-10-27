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

La usan **dos compus**: la de Mateo y la del jefe. Como `Y:` es compartido, es **la misma carpeta**
para las dos: el proyecto no se baja de nuevo en cada compu, pero Python, Git y las librerías se
instalan en cada usuario de Windows.

> **Ojo:** si una compu cambia de rama (`git checkout ...`), la carpeta cambia **para las dos**.
> El acceso directo siempre vuelve a `main`. Para el uso normal (siempre en `main`) no hay problema,
> y la app puede estar abierta en las dos compus a la vez.

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
start "" cmd /c "timeout /t 20 >NUL & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
```

| Línea | Para qué sirve |
|---|---|
| `cd /d "Y:\...\ferrovias"` | Entra a la carpeta del proyecto, desde donde se esté. |
| `git checkout main` | Se asegura de estar en `main`, la versión estable. |
| `git pull` | Trae de GitHub los últimos cambios. |
| `start "" cmd /c "timeout ... chrome ..."` | Espera 20 segundos a que arranque la app y la abre en Chrome. |
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
start "" cmd /c "timeout /t 20 >NUL & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
```

Para volver a la versión estable, usar de nuevo el bloque de todos los días (empieza con
`git checkout main`).

### Empezar de cero en el módulo Asociación LG ↔ PCZ

Igual que en la Mac: recargar la página o volver a abrir la app (no hay nada guardado que borrar).

### Accesos directos (archivos `.bat`)

Hay dos tipos. Reglas para crearlos (también para las sesiones de Claude):

| | Versión estable (`main`) | Probar una rama |
|---|---|---|
| Archivo | `abrir_app_windows.bat`, **dentro** de `ferrovias` (está en GitHub) | `probar_rama_<nombre>.bat`, **afuera**, en la carpeta `Claude` (no está en GitHub) |
| Carpeta | `cd /d "%~dp0"` | `cd /d "%~dp0ferrovias"` |
| Acceso directo | «App Ferrovías» | «PRUEBA <nombre>» |

1. **Los de ramas van afuera de `ferrovias`.** Si estuvieran adentro, el `git checkout` los borra o
   los cambia mientras se ejecutan y el acceso directo deja de andar.
2. **Nunca escribir la ruta de `Y:` adentro del `.bat`**: tiene tildes y espacios. Usar `%~dp0`
   (la carpeta donde está el `.bat`).
3. **Solo letras sin tildes** en el contenido (`Asociacion`, no `Asociación`).
4. **Comandos de Windows, no de Mac/Linux**: para descartar texto se usa `>NUL`, nunca `>/dev/null`
   (si no, la espera no se hace y Chrome se abre antes que la app).
5. **Siempre el mismo orden**: carpeta → `git fetch` (solo en ramas) → `git checkout` → `git pull` →
   `pip install` (solo en ramas, por si agregaron librerías) → abrir Chrome a los 20 segundos → app →
   `pause` (para que la ventana no se cierre si hay un error).
6. **Guardarlos desde el Bloc de notas** con el nombre **entre comillas** (`"probar_rama_x.bat"`);
   si no, Windows agrega `.txt`. El ícono correcto es una ventanita con engranaje.
7. **Uno abierto a la vez**: antes de abrir otro, cerrar la ventana negra del anterior (los dos usan
   `localhost:8501`).
8. **La carpeta es compartida con la compu del jefe**: al terminar de probar una rama, abrir una vez
   «App Ferrovías» para dejar la carpeta en `main`.

Modelo para probar una rama (cambiar `NOMBRE-DE-LA-RAMA` y el título):

```
@echo off
rem Prueba una rama (no es la version estable). Va en la carpeta Claude, al lado de ferrovias.
title Ferrovias - PRUEBA NOMBRE-DE-LA-RAMA
cd /d "%~dp0ferrovias"
git fetch
git checkout NOMBRE-DE-LA-RAMA
git pull
py -3.13 -m pip install --user -q -r requirements.txt
start "" cmd /c "timeout /t 20 >NUL & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
pause
```

Para crear el acceso directo: clic derecho en el `.bat` → **Enviar a** → **Escritorio (crear acceso
directo)**, y renombrarlo.

### Instalación (solo la primera vez en esta compu)

> Ya está hecha en la compu de Mateo y en la del jefe. Queda anotada por si hay que rehacerla
> (otra compu u otro usuario de Windows: Python, librerías y configuración de Git son de cada usuario).
> En una compu nueva **se saltea el paso 4**: la carpeta en `Y:` ya existe.
>
> Si un instalador pide **usuario y contraseña de administrador**, cancelarlo y usar la opción sin
> permisos que se indica en cada paso.

1. **Python 3.13**: bajar el *Python Install Manager* de https://www.python.org/downloads/windows/.
   Si la configuración avisa por los *alias de ejecución de aplicaciones*, activar
   *Python (default)* y *Python install manager*. Después, en `cmd`: `py install 3.13`
   (si `py -3.13 --version` dice *No runtime installed that matches 3.13*, falta este comando).
   - *Sin permisos de administrador:* bajar el **"Windows installer (64-bit)"** de Python 3.13,
     **destildar** *"Use admin privileges when installing py.exe"* y tildar *"Add python.exe to PATH"*.
2. **Git** desde https://git-scm.com/download/win (opciones por defecto).
   - *Sin permisos de administrador:* bajar **"Git for Windows Portable"**, descomprimirlo en
     `%USERPROFILE%\PortableGit` y agregar `%USERPROFILE%\PortableGit\cmd` al **Path** en
     *"Editar las variables de entorno de esta cuenta"*. Abrir una ventana negra nueva y probar
     `git --version`.
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
   clave de Anthropic. (El `.env` queda en la carpeta compartida: sirve para las dos compus.)
7. **Acceso directo:** clic derecho en `abrir_app_windows.bat` → **Enviar a** → **Escritorio
   (crear acceso directo)**.
