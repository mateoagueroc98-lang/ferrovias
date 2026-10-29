# REFERENCIA PARA TRANSCRIBIR EL LIBRO DE GUARDIA (LG) DE SEÑALAMIENTO
**Ferrovías – línea Belgrano Norte** · Versión R1 (26/10/2026) · Basada en Glosario RAMS V2 + resumen del TFI (F. Luque, UNSAM 2023)

> Este documento es **solo para transcribir**. La clasificación (Sistema / Subsistema / Parte, tipo de falla, atribución) se hace en otra etapa y usa el Glosario completo y el Esquema oficial.
> Marcas: **[A CONFIRMAR]** = deducido sin certeza. **[?]** = lectura dudosa.

---

## 1. Contexto mínimo
- Línea **Retiro – Villa Rosa**, ~54 km, 22 estaciones, sentido Sur → Norte. 43 pasos a nivel (P.A.N.). Señalamiento mayormente analógico, de los años 60.
- El LG lo escribe la **guardia de Señalamiento**: anota los avisos que recibe (de PCZ, auxiliares de estación, conductores) y lo que encontró y reparó.
- Sistemas que aparecen: **barreras** de P.A.N., **señales**, **circuitos de vía** (CV), **máquinas de cambio** (desvíos), **mesas de mando**, **abrigos** (gabinetes junto a la vía, código H###), **salas de relevadores**, **motogeneradores** (MG). También aparecen avisos de **Vía** (riel roto, soldadura) y del **ATS** de la locomotora.
- Una barrera la disparan los circuitos de vía. Por eso "barrera baja a destiempo" suele venir de un CV.

## 2. Estructura física del libro
- Cada página tiene **folio impreso** arriba a la derecha (29, 30…). Cuando se termina un libro, el folio **vuelve a 01**.
- Cada **turno es un bloque**: encabezado `FECHA TURNO DE HH a HH HS. APELLIDO - APELLIDO` → avisos uno debajo del otro → **firma**. En la práctica, **1 párrafo ≈ 1 turno**.
- Turnos: **06-14, 14-22 y 22-06**. El turno 22-06 lleva la fecha del día en que **empieza** (los avisos de 02:00 son de la madrugada siguiente, pero se transcribe la fecha del encabezado).
- **Entradas intercaladas** de otro sector (ej. "ROLDÁN - ALCONTE (T. FIJO)") o **consignas de la jefatura** ("Consigna para el turno Noche: …", con otra firma) → **fila aparte**.
- **Firmas**: antes de la firma suele haber una sigla que se lee `DSSN`, `DSSE`, `DSEN` u `OSEN` [A CONFIRMAR]. Transcribir como `[firma: DSSN]` (no cuenta como dudoso).
- **Notas con asterisco**: `(*)` en el texto + un renglón que empieza con `*` = aclaración del mismo escritor. Transcribir las dos partes en su lugar.
- Continuaciones: `(SIGO C. 7)`, `(POR ANTERIOR C-338)` → transcribir tal cual. `(OMITIDO DE 07.28 HS.)` = entrada cargada tarde.

## 3. Rasgos de letra por escritor (oct 2026)
- **Silva R.** (noche): imprenta mayúscula. La `S` parece `§` u `8`; la `E` parece `S` u `O` ("AVISA" se ve `AUISA`). `Q'` = que, `X` = por. Minutos en superíndice (`02⁴³ HS` = 02:43).
- **Rojas** (mañana): cursiva clara. Escribe **"pct"** donde va **Pcz** (la `z` cursiva parece `t`) → transcribir `pcz`. Usa `Hs.` antes de la hora y `.-` al final de cada aviso. En su letra, la `Y` de los relés se confunde con `4` o `9` (`1YGP` se ve `14GP` / `19GP`) → transcribir lo que se ve con [?].
- **Del Valle A.** (tarde): cursiva muy inclinada y apretada. La `C` mayúscula sale como `Q` o `&`. Giro fijo: "comunicó el Mor [?]" [A CONFIRMAR].
- **Ríos**: cursiva grande y prolija, con trazos verticales de lado a lado (no son tachaduras). Anota tensiones (`2,12 Vcc`).
- **Silva L. / Enríquez J.**: cursiva redonda y clara; firma con legajo debajo (ej. `5232`).

## 4. Personal visto (oct 2026)
Los turnos **rotan**: no deducir el turno por el apellido.
- Rojas (Encg.), Romero (Catalino), Ríos, Olavario [?], Del Valle A., **Silva L. (Luis)**, **Silva R.** (hay dos Silva), Lobigono [?] (también se lee Lobigeno / Codigono), Enríquez J., Mec. Claudio. En los avisos de PCZ de mayo aparecen además: Marotta, Clavario, Contreras, Alcante, Codigone, Marabert, León.
- Turno Fijo: Roldán, Alconte. Jefatura: Sr. Cuevas / Cueva, Adrián [A CONFIRMAR].

## 5. Abreviaturas y jerga
**Personas y comunicación**
| Escrito | Significa |
|---|---|
| AUX. / COND. / AYTE. / INSP. / OP. / GDA. | Auxiliar de estación / Conductor / Ayudante / Inspector / Operador / Guarda |
| MEC. / Encg. | Mecánico de Señalamiento / Encargado de la cuadrilla |
| SR. ... RESG. / c/resg. | Personal de Resguardo (custodia) / con resguardo |
| PCZ, Pcz, pct (cursiva), RZ, RCZ, rez, Op. Pcz, ENC. PCZ | Puesto de Control de trenes (Transporte), su operador y su encargado |
| C/A · C/C | Con aviso · Con conocimiento |
| DA NORMAL · NORMAL SOLO · "se cursa normal" | Se normalizó · se normalizó sin intervención · se da la habilitación a Pcz |
| scio | Servicio ("tomó scio", "dejó scio") |
| T. FIJO | Turno Fijo (trabajos programados de día) |
| V. y O. / VyO / INFRAEST. | Vía y Obras / Infraestructura de vías |
| MAT. ROD. · VIDEO / M.K.S. · SEG. OP. | Material Rodante · cámaras · Seguridad Operacional |
| consigna | Trabajo o prueba programada |
| recargado hasta hs X (100%) | Horas extra (no es falla) |
| b/s · HERSO · mecanizada | [A CONFIRMAR] · posible contratista de vía · máquina de vía trabajando |
| Q' · X | que · por |

**Trenes**: `T. 3029/E712` = tren 3029 con locomotora E712 (también 77xx y EM01/EM02).

**Equipos**
| Escrito | Significa |
|---|---|
| P.A.N. / PAN | Paso a nivel. `(A)` después del nombre = Alberti |
| Brazo ASC / DESC (norte/sur), brazo único | Brazo de barrera de la vía ascendente/descendente |
| Espadín · puntero · paralela · fusible mecánico · contrapeso | Partes del brazo de barrera |
| Cam switch / llave selectora de descenso · contacto N°1 · relé de control · borne B12 UP (2A), 1RF | Mecanismo y circuito de barrera |
| Laberinto · campanilla / sistema sonoro / fonoluminoso · farola | Paso peatonal · alarma · luces para autos |
| Señal 115, 21B, 21D, 7(M), S1 | Señal ferroviaria; letra = brazo o aspecto; (M) = maniobra |
| A peligro / precaución / vía libre · "aclara" / "no aclara" | Rojo / amarillo / verde · pasa o no a aspecto permisivo |
| Indicadora de ruta | Señal que indica a qué vía va el tren |
| Mesa de mando (MM) · clavijero · picket / pique / LED | Panel de la estación · mando manual · indicador luminoso |
| Ruta enclavada / desenclavar | Ruta asegurada |
| Cambio N · A.D.V. · Punta A / B · Normal / Invertido | Desvío · aparato de vía · extremos del cambio · posición recta / desviada |
| Fuera de correspondencia | El cambio no confirma que llegó a su posición |
| Agujas · silletas · camas · detectora · barra de encerrojar · horquilla · bulón · compensador · grampa · tirafoneado · muela | Partes y fijaciones del cambio |
| Máq. A · bomba hidráulica · acople motor | Máquina de cambio electrohidráulica |
| Circuito de vía (CV), "circuito ocupado" | Detecta el tren; ocupado sin tren = falla |
| CV 29ET, 9BT, 3CT, 350T, 307AT, 138T1, 510TA | Designaciones de circuitos |
| Liga · ligas de continuidad · spaguetti · botella · junta / punta aislante · cable volante · morceto · pararrayos | Conexiones eléctricas del CV |
| Lado relé / lado batería | Los dos extremos de un CV |
| Relé / relay · zócalo · 4AWRC, 23RGPR, 335AXR, 1YGPR, 29ETR, XIR [?] | Relevadores y su base |
| Abrigo / H 437 · bungalow · guirnalda · cerramiento antivandálico | Gabinete junto a la vía · sala de relés · mazo de cables · protección de puertas |
| B10, B12, B14, XB12 · vaso de batería · cargador / rectificador · régimen de carga | Bancos de batería y su carga |
| Térmica · M.G. / MG · estabilizador · tablero de transferencia · Edenor | Llave termomagnética · motogenerador · regulador · paso red↔MG · distribuidora |
| JB mástil · portalámpara · lámpara 21W [?] · Vcc | Caja de conexiones de la señal · partes de la señal · volts de continua |
| A.T.S. | Frenado automático de la locomotora |
| Riel roto · soldadura · junta colada · eclisar · precaución a X km/h del km A al km B | Avisos de **Vía** |
| EGM | Aparece en barreras [A CONFIRMAR] |

## 6. Pasos a nivel (nombre + km)
Identificar siempre por **nombre y km**: hay nombres repetidos.

| PAN | km | PAN | km |
|---|---|---|---|
| Lavalle | 14/116 | Beiró (el libro escribe "Beiro") | 36/345 |
| Yrigoyen (sur) | 15/649 | Drago | 39/962 |
| Villate | 16/331 | Tte. Gral. Perón | 40/314 |
| Carlos Calvo | 17/256 | Yrigoyen (norte) | 41/881 |
| R. Obligado | 18/442 | Oliden | 42/634 |
| Soldado de Malvinas | 19/248 | L. de la Torre / Lisandro de la Torre (abrigo H134 [?]) | 43/415 |
| Irigoyen | 21/653 | J. R. Jiménez | 43/630 |
| Arricau (el libro escribe "Aricau") | 28/530 | Ruta 26 | 44/150 |
| E. Perón | 32/093 | Colectora Sur / Norte | 47/313 · 47/435 |
| Rivadavia | 33/026 | Ruta 25 | 51/434 |

Sin km en el libro: **Baroni, Independencia, Urquiza, Irigoyen (Alberti)** [A CONFIRMAR cuál de los Yrigoyen], "Colectora" sin aclarar cuál. Referencia de lugar: Fray Justo Sarmiento [A CONFIRMAR].

## 7. Estaciones y abreviaturas
Abreviaturas vistas en el libro: `Bgne` / `Boulogne` = Boulogne · `BSM` = Boulogne Sur Mer · `G. Bourg` / `G.B.` = Grand Bourg · `V.R.` / `V. Rosa` = Villa Rosa · `D. Viso` = Del Viso · `(A)` = Alberti.

Estaciones de la línea (de sur a norte; lista de referencia general, no sale del TFI [A CONFIRMAR]):
Retiro · Saldías · Ciudad Universitaria · A. del Valle · M. M. Padilla · Florida · Munro · Carapachay · Villa Adelina · Boulogne Sur Mer · Montes · Don Torcuato · A. Sourdeaux · Villa de Mayo · Los Polvorines · Pablo Nogués · Grand Bourg · Tierras Altas · Tortuguitas · M. Alberti · Del Viso · Cecilia Grierson · Villa Rosa

## 8. Correcciones típicas al transcribir
- Palabras cortadas o pegadas por el salto de renglón: `ENCUEN-TRA` → `ENCUENTRA`; `DEMANDO` → `DE MANDO`.
- Topónimos con error evidente: corregir y dejar el original entre corchetes: `GRAGO [DRAGO]`, `ROVADAVIA [RIVADAVIA]`, `JINEMEZ [JIMÉNEZ]`, `BOYLOGNE [BOULOGNE]`, `MUUNRO [MUNRO]`, `ARICAU [ARRICAU]`.
- No corregir apellidos de personas ni la redacción.
