# Ferrovías – Automatización de Excels

App local (Streamlit) para:
- **Cruzar** dos Excels/CSVs por una o más columnas clave (tipo clave primaria).
- **Rellenar** celdas vacías de una columna usando Claude (API de Anthropic).
- **Descargar** el resultado como `.xlsx`.

Corre en tu compu y se abre en el navegador en `http://localhost:8501`. Los Excels **nunca** se suben a GitHub (están en `.gitignore`).

## Instalación en Windows (una vez por computadora)

1. Instalá **Python 3.11+** desde https://www.python.org/downloads/ (tildá *"Add python.exe to PATH"*).
2. Instalá **Git** desde https://git-scm.com/download/win.
3. Abrí *PowerShell* y cloná el repo:
   ```powershell
   cd $HOME\Documents
   git clone https://github.com/mateoagueroc98-lang/ferrov-as.git
   cd ferrov-as
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

Se abre el navegador. Subí los dos archivos, elegí las columnas clave, cruzá, y opcionalmente rellená columnas con IA.

## Trabajar desde dos computadoras

- Antes de empezar: `git pull`
- Al terminar: `git add . ; git commit -m "lo que hice" ; git push`

El `.env` (tu clave) y los Excels quedan solo en cada máquina; hay que crear el `.env` en cada una.

## Estructura

```
app.py          # interfaz Streamlit
src/cruce.py    # lógica de cruce por claves
src/ia.py       # relleno de celdas con Claude
datos/          # poné acá tus Excels (ignorados por git)
```
