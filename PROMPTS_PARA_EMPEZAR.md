# Prompts para empezar una conversación con Claude

Copiar el que corresponda como **primer mensaje** de una conversación nueva de Claude Code (app de
escritorio, con la carpeta `ferrovias` de `Y:` abierta) y completar lo que está entre `[corchetes]`.
Claude ya lee `CLAUDE.md` solo; estos prompts le marcan qué hacer y quién le escribe.

---

## Módulo nuevo

```
Hola, soy [nombre], de Ingeniería de Mantenimiento (RAMS) de Ferrovías. Vamos a crear un módulo
nuevo en la app. Trabajamos directo en esta carpeta compartida (la usan dos compus a la vez, sin
GitHub). Antes de empezar, leé CLAUDE.md, COMO_TRABAJAR_EN_EL_PROYECTO.md y
GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md, y seguí sus reglas.

Nombre del módulo en el menú: [nombre]
Qué tiene que hacer: [explicación con ejemplos]
Qué archivo entra: [Excel / CSV / PDF, de dónde sale, qué columnas tiene]
Qué tiene que salir: [qué Excel, qué columnas, en qué orden]

Si algo no queda claro, preguntame antes de programar. Antes de cambiar nada, guardá un punto de
restauración con git; armá un ejemplo inventado para probarlo, corré los tests y mostrame capturas.
Cuando esté, guardá otro punto de restauración y decime cómo verlo en la app.
```

## Seguir con un módulo que ya existe

```
Hola, soy [nombre]. Vamos a seguir con el módulo [Transcripciones del LG / Asociación LG ↔ PCZ /
Concatenación]. Trabajamos directo en esta carpeta compartida (dos compus, sin GitHub). Leé
CLAUDE.md, COMO_TRABAJAR_EN_EL_PROYECTO.md y la parte de ese módulo en el README antes de empezar.

Lo que quiero cambiar: [explicación, con un ejemplo o captura]

Guardá un punto de restauración con git antes de cambiar nada, corré los tests, mostrame capturas
y guardá otro punto al terminar. Recordame cerrar y volver a abrir la app para verlo.
```

## Algo no anda (error al abrir o al usar la app)

```
Hola, soy [nombre]. Tengo un problema con la app en [mi compu / la compu de mi jefe]. Leé
CLAUDE.md y GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md (cómo están armadas las compus) antes de contestar.

Qué hice: [qué acceso directo o comando usé]
Qué pasó: [pegar lo que dice la ventana negra, o adjuntar captura]

Explicámelo simple y con pasos concretos. Si hace falta cambiar algo del proyecto, guardá antes un
punto de restauración con git.
```

## Cosas generales (apariencia, menú, accesos directos, guías)

```
Hola, soy [nombre]. Quiero hacer un cambio general en la app (no de un módulo en particular):
[explicación]. Leé CLAUDE.md, COMO_TRABAJAR_EN_EL_PROYECTO.md y la guía antes de empezar.
Si toca archivos compartidos (app.py, .streamlit/config.toml, requirements.txt, README, guías),
que sea un cambio mínimo y avisame. Para cambios visuales usá la skill frontend-design.
Guardá un punto de restauración antes y después, y mostrame capturas.
```

---

## Frases útiles durante la conversación

| Para | Decile |
|---|---|
| Ver cómo quedó sin abrir la app | «Mostrame capturas.» |
| Deshacer lo último | «Volvé al último punto que funcionaba.» |
| Ver qué se cambió | «Mostrame la lista de puntos de restauración.» |
| Cerrar ordenado | «Resumime qué hicimos, qué falta, guardá un punto de restauración y actualizá CLAUDE.md si cambió algo del módulo.» |
