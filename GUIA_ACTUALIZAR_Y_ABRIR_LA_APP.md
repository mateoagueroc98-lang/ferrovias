# Guía: actualizar el proyecto y abrir la app

Pasos para traer los últimos cambios de GitHub y usar la app en cada computadora.

- [Casa – Mac](#casa--mac)
- [Trabajo – Windows](#trabajo--windows) *(pendiente)*

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

*Pendiente: se completa cuando se configure la computadora del trabajo.*

### Empezar de cero en el módulo Asociación LG ↔ PCZ

Igual que en la Mac: recargar la página o volver a abrir la app (no hay nada guardado que borrar).
