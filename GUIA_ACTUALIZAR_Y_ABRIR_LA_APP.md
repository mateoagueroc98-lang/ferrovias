# Guía: abrir la app y mantenerla

El proyecto vive **solo en la carpeta compartida** del trabajo (ya no se usa GitHub):

```
Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias
```

La usan **dos compus a la vez** (la de Mateo y la del jefe). Lo que se cambia en esa carpeta,
cambia para las dos: no hay que «actualizar» ni descargar nada.

---

## Uso de todos los días

**Doble clic en el acceso directo «App Ferrovías»** del escritorio. Abre una ventana negra, arranca
la app y a los 20 segundos la abre en Chrome (`http://localhost:8501`).

- Si Chrome muestra «No se puede acceder a este sitio», esperar unos segundos y apretar **F5**:
  desde la unidad de red la app tarda en arrancar.
- **No cerrar la ventana negra** mientras se usa la app: corre ahí. Para apagarla: cerrarla o
  `Ctrl + C`.
- **Para ver un cambio** que hizo Claude: cerrar la ventana negra y volver a abrir «App Ferrovías»
  (la app no se da cuenta sola de los cambios).
- No tocar el botón **Deploy** de la app (la publicaría en internet).

**A mano** (si el acceso directo no está): ventana negra (tecla Windows → `cmd` → Enter) y pegar:

```
cd /d "Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias"
start "" cmd /c "timeout /t 20 >NUL & start chrome http://localhost:8501"
py -3.13 -m streamlit run app.py --server.headless true
```

| Línea | Para qué sirve |
|---|---|
| `cd /d "Y:\...\ferrovias"` | Entra a la carpeta del proyecto, desde donde se esté. |
| `start "" cmd /c "timeout ... chrome ..."` | Espera 20 segundos a que arranque la app y la abre en Chrome. |
| `py -3.13 -m streamlit run ...` | Abre la app (no se usa `.venv`: las librerías están instaladas en el usuario). |

### Si aparece un error de que falta algo

La ventana negra o la página dicen `No module named ...`: se agregó una librería nueva. Una vez en
**cada compu y usuario de Windows**:

```
cd /d "Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias"
py -3.13 -m pip install --user -r requirements.txt
```

y volver a abrir «App Ferrovías».

### Empezar de cero en el módulo Asociación LG ↔ PCZ

Recargar la página o volver a abrir la app (no hay nada guardado que borrar). Lo que no se haya
descargado en **3. Exportar** se pierde.

### Configuración de «Transcripciones del LG»

Lo que se guarda en ⚙️ Configuración (instrucciones, referencia, modelo, saldo) queda en la carpeta
del proyecto, así que **las dos compus lo comparten** automáticamente. Conviene editarlo en una sola
compu a la vez.

---

## Trabajar con Claude en la carpeta

Ver [COMO_TRABAJAR_EN_EL_PROYECTO.md](COMO_TRABAJAR_EN_EL_PROYECTO.md). En resumen: Claude (app de
escritorio, con Claude Code) abre la carpeta `ferrovias` de `Y:` y la edita directamente. Guarda
**puntos de restauración** con Git (un historial que queda dentro de la carpeta, en `.git`) para poder
volver atrás si algo se rompe. **Una sola sesión de Claude cambiando la carpeta a la vez.**

---

## Accesos directos (archivos `.bat`)

- `abrir_app_windows.bat` (dentro de `ferrovias`) abre la app. En el escritorio: clic derecho en el
  archivo → **Enviar a** → **Escritorio (crear acceso directo)** y renombrarlo «App Ferrovías».
- Si hace falta otro `.bat`, reglas:
  1. Nunca escribir la ruta de `Y:` adentro (tiene tildes y espacios): usar `%~dp0`, la carpeta
     donde está el `.bat`. Si va en `Claude\accesos app`, entrar con `cd /d "%~dp0..\ferrovias"`.
  2. Solo letras sin tildes en el contenido.
  3. Comandos de Windows: `>NUL`, nunca `>/dev/null` (si no, la espera no se hace y Chrome se abre
     antes que la app).
  4. Terminar con `pause`, para que la ventana no se cierre si hay un error.
  5. Fin de línea de Windows (CRLF). Guardarlos desde el Bloc de notas con el nombre **entre
     comillas** (`"nombre.bat"`); si no, Windows agrega `.txt`.
  6. Uno abierto a la vez: todos usan `localhost:8501`.
- Los accesos «PRUEBA ...» de `accesos app` eran para probar ramas de GitHub: **ya no sirven**
  (borrarlos, junto con sus accesos del escritorio).

---

## Instalación (solo la primera vez en una compu o usuario de Windows)

> Ya está hecha en la compu de Mateo y en la del jefe. Python, librerías y configuración de Git son
> de cada usuario de Windows; la carpeta de `Y:` ya existe y no se copia.
>
> Si un instalador pide **usuario y contraseña de administrador**, cancelarlo y usar la opción sin
> permisos de cada paso.

1. **Python 3.13**: bajar el *Python Install Manager* de https://www.python.org/downloads/windows/.
   Si la configuración avisa por los *alias de ejecución de aplicaciones*, activar
   *Python (default)* y *Python install manager*. Después, en `cmd`: `py install 3.13`
   (si `py -3.13 --version` dice *No runtime installed that matches 3.13*, falta este comando).
   - *Sin permisos de administrador:* bajar el **"Windows installer (64-bit)"** de Python 3.13,
     **destildar** *"Use admin privileges when installing py.exe"* y tildar *"Add python.exe to PATH"*.
2. **Git** (lo usa Claude para los puntos de restauración) desde https://git-scm.com/download/win
   (opciones por defecto).
   - *Sin permisos de administrador:* bajar **"Git for Windows Portable"**, descomprimirlo en
     `%USERPROFILE%\PortableGit` y agregar `%USERPROFILE%\PortableGit\cmd` al **Path** en
     *"Editar las variables de entorno de esta cuenta"*. Abrir una ventana negra nueva y probar
     `git --version`.
3. En estas compus la carpeta personal (`HOME`) apunta a `Y:\`, donde no se puede escribir. Para que
   Git guarde su configuración en `C:` y no desconfíe de la unidad de red («dubious ownership»):

   ```
   setx HOME "%USERPROFILE%"
   ```

   cerrar la ventana negra, abrir una nueva y:

   ```
   git config --global --add safe.directory "*"
   ```

4. Instalar las librerías (en el usuario, sin `.venv`: en la unidad de red sería lento):

   ```
   cd /d "Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias"
   py -3.13 -m pip install --user -r requirements.txt
   ```

5. *(Para Transcripciones del LG)*: si no existe el archivo `.env` en la carpeta,
   `copy .env.example .env` y `notepad .env` para pegar la clave de Anthropic. Como la carpeta es
   compartida, el mismo `.env` sirve para las dos compus.
6. **Acceso directo:** clic derecho en `abrir_app_windows.bat` → **Enviar a** → **Escritorio
   (crear acceso directo)**.

---

## La Mac de casa

La copia de `~/ferrovias` en la Mac **ya no se actualiza** (se sincronizaba por GitHub). Para usar
la versión actual en la Mac habría que copiarle la carpeta del trabajo (por ejemplo con un pendrive)
y abrirla con `source .venv/bin/activate` + `streamlit run app.py`.
