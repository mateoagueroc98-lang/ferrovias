# Prompts para empezar una conversación con Claude

Copiar el que corresponda como **primer mensaje** de una sesión nueva de Claude Code (con el
repositorio `mateoagueroc98-lang/ferrovias` elegido) y completar lo que está entre `[corchetes]`.
Claude ya lee `CLAUDE.md` solo; estos prompts le marcan qué hacer y quién le escribe.

---

## Módulo nuevo

```
Hola, soy [nombre], de Ingeniería de Mantenimiento (RAMS) de Ferrovías. Vamos a crear un módulo
nuevo en la app. Antes de empezar, leé CLAUDE.md, COMO_TRABAJAR_EN_EL_PROYECTO.md y la guía
GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md, y seguí sus reglas (un módulo por sesión, textos en español,
paleta de Ferrovías, nada de datos reales en GitHub).

Nombre del módulo en el menú: [nombre]
Qué tiene que hacer: [explicación con ejemplos]
Qué archivo entra: [Excel / CSV / PDF, de dónde sale, qué columnas tiene]
Qué tiene que salir: [qué Excel, qué columnas, en qué orden]

Si algo no queda claro, preguntame antes de programar. Armá un ejemplo inventado para probarlo,
mostrame capturas y, cuando esté para probar, pasame el .bat para la carpeta "accesos app".
No lo pases a main hasta que te lo pida.
```

## Seguir con un módulo que ya existe

```
Hola, soy [nombre]. Vamos a seguir con el módulo [Transcripciones del LG / Asociación LG ↔ PCZ /
Concatenación]. Leé CLAUDE.md, COMO_TRABAJAR_EN_EL_PROYECTO.md y la parte de ese módulo en el
README antes de empezar, y respetá sus reglas.

Lo que quiero cambiar: [explicación, con un ejemplo o captura]

Trabajá en una rama nueva partiendo de main actualizado. Mostrame capturas, pasame el .bat para
probar la rama desde "accesos app" y no lo pases a main hasta que te lo pida.
```

## Algo no anda (error al abrir o al usar la app)

```
Hola, soy [nombre]. Tengo un problema con la app en [la compu del trabajo / la compu de mi jefe /
la Mac]. Leé CLAUDE.md y la guía GUIA_ACTUALIZAR_Y_ABRIR_LA_APP.md (cómo es cada compu) antes de
contestar.

Qué hice: [qué acceso directo o comando usé]
Qué pasó: [pegar lo que dice la ventana negra, o adjuntar captura]

Explicámelo simple y con pasos concretos. Si hace falta cambiar algo del proyecto, hacelo en una
rama y avisame antes de pasarlo a main.
```

## Cosas generales (apariencia, menú, accesos directos, guías)

```
Hola, soy [nombre]. Quiero hacer un cambio general en la app (no de un módulo en particular):
[explicación]. Leé CLAUDE.md, COMO_TRABAJAR_EN_EL_PROYECTO.md y la guía antes de empezar.
Si toca archivos compartidos (app.py, .streamlit/config.toml, requirements.txt, README, guías),
que sea un cambio mínimo y avisame. Para cambios visuales usá la skill frontend-design.
Mostrame capturas y no lo pases a main hasta que te lo pida.
```

---

## Frases útiles durante la conversación

| Para | Decile |
|---|---|
| Probar en la compu del trabajo | «Pasame el .bat para probar esta rama desde accesos app.» |
| Aceptar los cambios | «Pasalo a main.» |
| Ver cómo quedó sin abrir la app | «Mostrame capturas.» |
| Cerrar la sesión ordenada | «Resumime qué hicimos, qué falta y actualizá CLAUDE.md si cambió algo del módulo.» |
