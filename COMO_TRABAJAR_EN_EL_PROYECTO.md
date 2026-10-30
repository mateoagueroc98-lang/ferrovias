# Cómo trabajar en el proyecto (guía para quien lo continúa)

Qué es la app, cómo abrirla y cómo pedirle cambios a Claude sin perderse. Los comandos para abrir y
mantener la app están en [GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md](GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md); los
prompts para empezar una conversación, en [PROMPTS_PARA_EMPEZAR.md](PROMPTS_PARA_EMPEZAR.md).

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

Todo está en **una sola carpeta compartida** (ya no se usa GitHub):

```
Y:\Ingeniería de Mantenimiento\RAMS\PASANTE\_MATEO\Claude\ferrovias
```

| Qué | Dónde (dentro de `ferrovias`) |
|---|---|
| Las reglas que lee Claude | `CLAUDE.md` (Claude lo lee solo al empezar cada conversación) |
| Pantallas de cada módulo | `modulos\` |
| Lógica de cada módulo | `src\` |
| Configuración de Transcripciones | `config\transcripcion_lg\` |
| Clave de Anthropic | `.env` (no compartirla) |
| Historial de cambios (puntos de restauración) | `.git\` (no tocar a mano) |

La usan **dos compus a la vez** (la de Mateo y la del jefe): lo que se cambia, cambia para las dos.

## 3. Abrir la app

- Doble clic en **«App Ferrovías»** del escritorio. A los 20 segundos se abre Chrome (si muestra
  error, esperar y apretar **F5**).
- **Cerrar:** cerrar la ventana negra.
- **Para ver un cambio que hizo Claude:** cerrar la ventana negra y volver a abrir «App Ferrovías».

## 4. Cómo se le piden cambios a Claude

Se usa la **app de escritorio de Claude, con Claude Code**, en la compu del trabajo, abriendo la
carpeta `ferrovias` de `Y:`.

1. **Una conversación por tema o módulo.** Y **una sola conversación cambiando la carpeta a la vez**
   (entre las dos compus): si Mateo y el jefe le piden cambios a Claude al mismo tiempo, se pisan.
2. **Arrancá con un prompt** de [PROMPTS_PARA_EMPEZAR.md](PROMPTS_PARA_EMPEZAR.md): le da a Claude
   el contexto y le recuerda las reglas.
3. **Explicá con ejemplos**: qué entra (qué Excel o PDF, qué columnas) y qué tiene que salir. Si
   podés, adjuntá una captura.
4. Claude **guarda un punto de restauración antes de cambiar** y otro después de cada cambio que
   funciona.
5. **Probalo**: cerrá y volvé a abrir «App Ferrovías».
6. **Los cambios son en vivo**: apenas Claude los guarda, la otra compu también los tiene (al
   reabrir la app). Si alguien está usando la app en ese momento, avisale antes.
7. Si algo se rompe, decile a Claude **«volvé al último punto que funcionaba»**.
8. Si se agregaron librerías nuevas, Claude te va a pasar un comando para instalarlas (una vez por
   compu y usuario de Windows).

## 5. Si algo no anda

| Pasa esto | Hacé esto |
|---|---|
| Chrome dice «No se puede acceder a este sitio» | Esperar unos segundos y apretar **F5**: la app tarda en arrancar desde la red. |
| La ventana negra dice `No module named ...` | Faltan librerías: ver «Si aparece un error de que falta algo» en la guía. |
| No se ve un cambio que hizo Claude | Cerrar la ventana negra y volver a abrir «App Ferrovías». |
| Algo dejó de funcionar después de un cambio | Pedirle a Claude que vuelva al último punto que funcionaba. |
| Cualquier otro error | Copiá lo que dice la ventana negra (o una captura) y pegáselo a Claude. |

No tocar el botón **Deploy** de la app: la publicaría en internet.
