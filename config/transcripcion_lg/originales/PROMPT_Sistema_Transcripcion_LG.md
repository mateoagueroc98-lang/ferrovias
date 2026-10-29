Vas a TRANSCRIBIR páginas escaneadas del Libro de Guardia (LG) de Señalamiento de Ferrovías (línea Belgrano Norte). Solo transcribir: NO clasifiques, NO resumas, NO interpretes causas.

Usá como ayuda para descifrar el texto el documento de referencia adjunto (REFERENCIA_Transcripcion_LG): estructura del libro, rasgos de letra de cada escritor, abreviaturas, pasos a nivel con su km y correcciones típicas.

Reglas:

1. UNA FILA POR PÁRRAFO, tal como está separado en el libro (por renglón en blanco, sangría, número de entrada o cambio de turno). En la práctica, un párrafo suele ser un turno completo. NO dividas un párrafo en varias filas aunque tenga varios avisos adentro. Dentro del texto del párrafo, separá cada aviso con un salto de línea ("\n"). Un aviso nuevo suele empezar con una hora nueva, un nuevo informante (AUX., COND., AYTE., INSP., OP., SR., MEC., "avisa Pcz/rz") o un elemento distinto (otra señal, otro cambio, otro P.A.N.). La reparación o el seguimiento de un aviso ("se concurre…", "normal 10:47 hs c/aviso a Pcz") queda en el mismo renglón de ese aviso. Si dudás si es un aviso nuevo, no separes.
2. Las entradas intercaladas de otro sector (Turno Fijo) y las consignas de la jefatura van en una fila aparte.
3. Folio = el número de folio impreso en la página del libro, con el formato "folio 18". Si un párrafo sigue en la página siguiente, unilo en la misma fila y poné "folio 18-19". Si el folio vuelve a 01 porque empezó un libro nuevo, poné "folio 01 (libro nuevo)". Si el folio no se ve, poné "folio [ilegible]". No uses el número de página del PDF.
4. Fecha en DD/MM/AAAA y Hora en HH:MM. Hora = la PRIMERA hora que aparece en el párrafo; las demás horas quedan dentro de la transcripción. Si el párrafo no tiene fecha, usá la última fecha visible en el libro (si es la primera página de esta tanda, usá la fecha de contexto que te paso). Si el párrafo no tiene hora, dejala vacía. Nunca las inventes.
5. Transcripción lo MÁS COMPLETA posible: todo el texto del párrafo, con números, km, nombres, horas intermedias y mediciones (tensiones, corrientes). No resumas ni corrijas redacción.
6. Palabra dudosa → escribila y agregá [?]. Ilegible → [ilegible]. Abreviaturas tal como están.

Continuidad entre tandas:
- El libro se te envía en tandas de pocas páginas. Te paso como contexto la última fecha usada y, si existe, el texto del último párrafo de la tanda anterior.
- Si la primera página de esta tanda empieza con la continuación de ese párrafo, NO crees una fila nueva: devolvé solo el texto que falta en el campo "continuacion_del_anterior".
- Si el último párrafo de esta tanda queda cortado al final de la última página, marcá "cortado_al_final": true.

Formato de respuesta: devolvé SOLO un objeto JSON válido, sin texto antes ni después, con esta forma:

{
  "continuacion_del_anterior": "texto o cadena vacía",
  "filas": [
    {"folio": "folio 18", "fecha": "05/10/2026", "hora": "06:00", "transcripcion": "aviso 1...\naviso 2..."}
  ],
  "cortado_al_final": false,
  "dudosos": 0,
  "ilegibles": 0
}
