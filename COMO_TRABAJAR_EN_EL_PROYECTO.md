# Cómo trabajar en el proyecto (guía para quien lo continúa)

Esta guía es para seguir el proyecto desde cualquier cuenta de Claude: qué es la app, cómo abrirla
y cómo pedirle cambios a Claude sin perderse. Los comandos exactos para abrir la app están en
[GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md](GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md); los prompts para empezar
una conversación, en [PROMPTS_PARA_EMPEZAR.md](PROMPTS_PARA_EMPEZAR.md).

---

## 1. Qué es

Una app que corre en la compu y se abre en Chrome (`localhost:8501`). Sirve para automatizar
trabajo con Excels de Ingeniería de Mantenimiento. Cada pantalla del menú de la izquierda es un
**módulo**:

| Módulo | Para qué sirve |
|---|---|
| Transcripciones del LG | Pasa a Excel el PDF escaneado del Libro de Guardia, con la IA de Claude. |
| Asociación LG ↔ PCZ | Asocia a mano las novedades del PCZ con los avisos del Libro de Guardia, día por día. |
| Concatenación | Convierte el CSV del reporte Libro de Novedades en un Excel con una fila por novedad. |

El detalle de cada módulo está en el [README](README.md).

## 2. Dónde está cada cosa

| Qué | Dónde |
|---|---|
| El código «oficial» | GitHub: https://github.com/mateoagueroc98-lang/ferrovias |
| La app en el trabajo | `Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias` (compartida por las compus del trabajo) |
| Accesos directos para probar versiones nuevas | `Y:\...\Claude\accesos app` |
| La app en la Mac (casa de Mateo) | `~/ferrovias` |
| Las reglas que lee Claude | `CLAUDE.md` (Claude lo lee solo al empezar cada conversación) |

Los Excels, PDFs y la clave de Anthropic (`.env`) **nunca** se suben a GitHub.

## 3. Abrir la app

- **Versión estable:** doble clic en el acceso directo **«App Ferrovías»** del escritorio. Baja lo
  último de GitHub y abre Chrome solo (si Chrome muestra error, esperar y apretar **F5**).
- **Versión de prueba** (un módulo que todavía no está terminado): un acceso directo
  «PRUEBA ...» que apunta a un `.bat` de la carpeta `accesos app`. Claude lo arma cuando se lo pedís.
- **Cerrar:** cerrar la ventana negra. Abrir **uno a la vez** (estable o prueba).
- Al terminar de probar, abrir una vez **«App Ferrovías»**: la carpeta es compartida y así queda
  la versión estable para todas las compus.

## 4. Cómo se le piden cambios a Claude

Hay **dos formas**; el proyecto es el mismo en las dos.

- **A. Con GitHub** (como trabajó Mateo): Claude Code en la web (claude.ai/code), eligiendo el
  repositorio `mateoagueroc98-lang/ferrovias`. Pasos abajo.
- **B. Directo en la carpeta compartida** (cuando pase a la cuenta del jefe): Claude trabaja sobre la
  carpeta `ferrovias` de `Y:`, sin GitHub. Ver la sección **4-B**.

### 4-A. Con GitHub

1. **Una conversación (sesión) por módulo.** Si querés tocar dos módulos, abrí dos sesiones.
2. **Arrancá con un prompt** de [PROMPTS_PARA_EMPEZAR.md](PROMPTS_PARA_EMPEZAR.md): le da a Claude el
   contexto y le recuerda las reglas.
3. **Explicá con ejemplos**: qué entra (qué Excel o PDF, qué columnas) y qué tiene que salir. Si podés,
   adjuntá una captura o un ejemplo **inventado** (sin datos reales).
4. Claude trabaja en una **rama** (una copia aparte) y te muestra capturas de cómo quedó.
5. **Probalo** en la compu con el acceso «PRUEBA ...» que te pasa Claude.
6. Si está bien, decile **«pasalo a main»**. Recién ahí llega a la versión estable y a «App Ferrovías».
7. Si se agregaron librerías nuevas, Claude te va a pasar un comando para instalarlas
   (una vez por compu y usuario de Windows).

### 4-B. Directo en la carpeta compartida (sin GitHub)

Se usa Claude **en la compu del trabajo** (app de escritorio de Claude, con Claude Code), abriendo la
carpeta `Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias`.

- **Los cambios son en vivo**: Claude edita la misma carpeta que usan las dos compus. No hay ramas
  ni «pasalo a main»; lo que cambia, cambia para todos.
- **Para ver un cambio**: cerrar la ventana negra y volver a abrir **«App Ferrovías»**.
- **Puntos de restauración**: Claude guarda cada cambio con `git commit` (queda un historial en la
  carpeta). Si algo se rompe, pedile «volvé al último punto que funcionaba».
- **Avisá antes de cambiar algo** si otra persona está usando la app en ese momento.
- Los accesos directos hacen `git pull`: si ya no hay GitHub y muestra un error, la app abre igual.
- Arrancá con el prompt **«Carpeta compartida»** de [PROMPTS_PARA_EMPEZAR.md](PROMPTS_PARA_EMPEZAR.md).

### Palabras que vas a ver

| Palabra | Qué significa |
|---|---|
| `main` | La versión estable, la que abre «App Ferrovías». |
| Rama | Una copia aparte donde Claude hace cambios sin tocar `main`. Tiene un nombre como `claude/...`. |
| Pull request (PR) | El pedido de pasar los cambios de una rama a `main`. |
| Merge / unir | Aceptar ese pedido: los cambios pasan a `main`. |
| `git pull` | Bajar a la carpeta lo último de GitHub (los accesos directos lo hacen solos). |

## 5. Si algo no anda

| Pasa esto | Hacé esto |
|---|---|
| Chrome dice «No se puede acceder a este sitio» | Esperar unos segundos y apretar **F5**: la app tarda en arrancar desde la red. |
| La ventana negra dice `No module named ...` | Faltan librerías: `py -3.13 -m pip install --user -r requirements.txt` en la carpeta (o pedirle el comando a Claude). |
| `git` dice «dubious ownership» o «could not lock config file» | Falta la configuración de Git de esa compu: ver «Instalación» en la guía. |
| No aparece el módulo nuevo | Todavía no está en `main`: abrí el acceso «PRUEBA ...» o pedile a Claude que lo pase a `main`. |
| Cualquier otro error | Copiá lo que dice la ventana negra (o una captura) y pegáselo a Claude. |

No tocar el botón **Deploy** de la app: la publicaría en internet.
