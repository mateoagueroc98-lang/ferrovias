# Guía: actualizar el proyecto y abrir la app

Pasos para traer los últimos cambios de GitHub y usar la app en cada computadora.

- [Casa – Mac](#casa--mac)
- [Trabajo – Windows](#trabajo--windows) *(sin Git: se actualiza con ZIP)*

---

## Casa – Mac

Todo se hace en la app **Terminal** (`Cmd + Espacio`, escribir `Terminal`, Enter).

### Uso de todos los días

Copiar y pegar de a una línea:

```bash
cd ~/Documents/ferrovias
git checkout main
git pull
source .venv/bin/activate
streamlit run app.py
```

Qué hace cada línea:

| Comando | Para qué sirve |
|---|---|
| `cd ~/Documents/ferrovias` | Entra a la carpeta del proyecto. La línea tiene que terminar en `ferrovias %`. |
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
cd ~/Documents/ferrovias
git fetch
git checkout NOMBRE-DE-LA-RAMA
git pull
source .venv/bin/activate
streamlit run app.py
```

El nombre de la rama se ve en GitHub, en la pestaña **Pull requests** o en el menú de ramas.
Para volver a la versión estable: `git checkout main`.

### Borrar las asociaciones guardadas (módulo Asociación LG ↔ PCZ)

Las asociaciones guardadas están en la carpeta `datos/sesiones`. Para empezar de cero:

1. Cerrar la app con `Ctrl + C` en la Terminal.
2. Borrar la carpeta:

   ```bash
   cd ~/Documents/ferrovias
   rm -rf datos/sesiones
   ```

3. Abrir la app de nuevo (con el `(.venv)` activo):

   ```bash
   streamlit run app.py
   ```

4. En el navegador, **cerrar la pestaña vieja** de la app y abrir una nueva en
   `http://localhost:8501`. Si no, la pestaña vieja puede seguir mostrando lo que tenía en memoria.

> **Ojo:** esto borra todo el progreso guardado **en esta Mac**, de todos los pares de Excel.
> Las asociaciones de la compu del trabajo no se tocan, porque están guardadas allá.

### Instalación (solo la primera vez en esta Mac)

> Ya está hecha. Queda anotada por si hay que rehacerla.

1. **Git**: ya viene; se comprueba con `git --version`.
2. **Python 3.13** desde https://www.python.org/downloads/macos/ (no usar 3.15: algunas
   librerías todavía no funcionan). Después de instalar, doble clic en
   *Aplicaciones → Python 3.13 → Install Certificates.command*.
3. En la Terminal:

   ```bash
   cd ~/Documents
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

En esta compu **no hay Git**: el proyecto se actualiza bajando un ZIP de GitHub y pegándolo
encima de la carpeta. La carpeta del proyecto está en la unidad de red:

```
Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias
```

### Actualizar (cuando hay cambios nuevos en GitHub)

1. Si la app está abierta, cerrarla con `Ctrl + C` en la ventana negra.
2. Entrar a https://github.com/mateoagueroc98-lang/ferrovias, botón verde **Code** →
   **Download ZIP**. (Baja la versión estable, `main`.)
3. En **Descargas**, clic derecho en `ferrovias-main.zip` → **Extraer todo** → **Extraer**.
4. Entrar a la carpeta extraída `ferrovias-main` hasta ver `app.py` (a veces hay una carpeta
   `ferrovias-main` adentro de otra). Seleccionar todo (`Ctrl + A`) y copiar (`Ctrl + C`).
5. Ir a la carpeta `ferrovias` de `Y:`, pegar (`Ctrl + V`) y elegir
   **Reemplazar los archivos en el destino**.

> **Ojo:** pegar **encima**, no borrar la carpeta `ferrovias` vieja. El ZIP no trae `datos\`
> (Excels y asociaciones guardadas) ni `.env` (clave), así que si se borra la carpeta se pierden.

Para probar una rama que todavía no está en `main`: en GitHub elegirla en el menú de ramas
(arriba a la izquierda, dice `main`) **antes** de tocar **Code → Download ZIP**.

### Abrir la app

1. Abrir la carpeta `ferrovias` en el Explorador, hacer clic en la barra de direcciones,
   escribir `cmd` y Enter. Se abre una ventana negra ya ubicada en la carpeta.
2. Escribir:

   ```
   python -m streamlit run app.py --server.headless true
   ```

3. Abrir **Chrome** en `http://localhost:8501`.

- **No cerrar la ventana negra** mientras se usa la app: corre ahí. Para apagarla: `Ctrl + C`.
- Si dice que `python` no se reconoce, usar `py` en su lugar: `py -m streamlit run app.py --server.headless true`.
- Si dice `No module named ...` (falta una librería, por ejemplo después de actualizar):

  ```
  python -m pip install --user -r requirements.txt
  ```

  y volver a abrir la app.

### Instalación (solo la primera vez en esta compu)

1. **Python 3.13** desde https://www.python.org/downloads/windows/ — en el instalador tildar
   *"Add python.exe to PATH"*. (No hace falta Git.)
2. Bajar el proyecto como en [Actualizar](#actualizar-cuando-hay-cambios-nuevos-en-github)
   y pegarlo en la carpeta de `Y:`.
3. Abrir `cmd` en la carpeta (como en *Abrir la app*) e instalar las librerías:

   ```
   python -m pip install --user -r requirements.txt
   ```

   El `--user` las instala en el usuario (disco `C:`), sin permisos de administrador y sin
   crear un `.venv` en la unidad de red, que sería lento.
4. *(Opcional, para módulos con IA)*: `copy .env.example .env` y `notepad .env` para pegar la
   clave de Anthropic.

### Borrar las asociaciones guardadas (módulo Asociación LG ↔ PCZ)

1. Cerrar la app con `Ctrl + C` en la ventana negra.
2. En el Explorador, entrar a `ferrovias\datos` y borrar la carpeta `sesiones`.
3. Abrir la app de nuevo y, en Chrome, cerrar la pestaña vieja y abrir una nueva en
   `http://localhost:8501`.

Esto borra solo lo guardado en la compu del trabajo; lo de la Mac no se toca.
