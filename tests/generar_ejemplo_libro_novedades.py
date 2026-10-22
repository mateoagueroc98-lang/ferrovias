"""Genera un CSV de prueba INVENTADO para el módulo Libro de Novedades.

Uso:  python tests/generar_ejemplo_libro_novedades.py
Crea tests/ejemplos/LibroNovedades_ejemplo.csv con el mismo formato que el export del reporte
(Windows-1252, fin de línea de Windows, 3 filas descartables antes del encabezado).
Los textos son inventados pero reproducen los casos del documento del módulo: comas internas
entre comillas, comillas internas, tildes y Ñ, palabras cortadas con guion, novedades con
varias horas, una pendiente de un día anterior y un número separado por otros.
"""
from pathlib import Path

ARCHIVO = Path(__file__).parent / "ejemplos" / "LibroNovedades_ejemplo.csv"

LINEAS = [
    "Textbox5,Textbox12",
    "*Se muestran las novedades pendientes anteriores a la fecha seleccionada,21/10/2026",
    "",
    "numero,Descripción_Estado,fecha,hora,descrip",
    # Pendiente de un día anterior: se procesa igual
    "790,PENDIENTE,20/10/2026,22:10,\"PAN CALLE IBAÑEZ BARRERA SIN COMPROBACION, SE AVISA A MEC. DE TURNO.-\"",
    "799,NORMAL,21/10/2026,03:16,INSP. BELTRAN RECIBE VIA DESC. SECTOR BOULOGNE - MUNRO DE PARTE DEL SR",
    "799,NORMAL,21/10/2026,03:16,ARMAS DE INFRAEST.-",
    # Tres horas distintas, ninguna con NORMAL (sí "ANORMAL" y "NORMALIZACION", que no cuentan)
    "800,NORMAL,21/10/2026,00:43,T.3001 DETE-",
    "800,NORMAL,21/10/2026,00:43,NIDO EN SEÑAL 41 POR FUNCIONAMIENTO ANORMAL DE DERIVACIÓN.-",
    "800,NORMAL,21/10/2026,01:05,MEC. ROJAS EN EL LUGAR.-",
    "800,NORMAL,21/10/2026,02:30,SE ESPERA NORMALIZACION DE LA DERIVACIÓN.-",
    "802,NORMAL,21/10/2026,01:20,INSP. GALVAN RECIBE VIA ASC. SECTOR MUNRO - CARAPACHAY.-",
    "802,NORMAL,21/10/2026,01:40,ENTREGA VIA A CUADRILLA DE VIA Y OBRAS.-",
    "802,NORMAL,21/10/2026,01:55,INSP. GALVAN RECIBE VIA ASC. SECTOR CARAPACHAY - VILLA ADELINA.-",
    "803,NORMAL,21/10/2026,00:50,\"MITAD DE PLATAFORMA DESC., EL FUE ADVERTIDO POR UNA PERSONA QUE ESTABA\"",
    "803,NORMAL,21/10/2026,00:50,EN EL ANDEN.-",
    "804,NORMAL,21/10/2026,01:30,COND. PEREYRA RECIBE CUADRO EN ESTACION VILLA ROSA.-",
    "805,NORMAL,21/10/2026,02:18,\"AUX. DIAZ EST. TORTUGUITAS INF. QUE CONTROLO PAN, FUNCIONANDO TODO NORMAL\"",
    "807,NORMAL,21/10/2026,04:48,CORTE DE ENERGIA SECTOR DON TORCUATO - GRAND BOURG.-",
    "807,NORMAL,21/10/2026,07:45,NORMAL EL SECTOR.-",
    "808,NORMAL,21/10/2026,04:49,AUX. BOGADO EST. G.BOURG INF. QUE SEÑAL 23 NO ACLARA PARA T.3012 LOC.",
    "808,NORMAL,21/10/2026,04:49,\"E703, COND. CAPPELLETTI INF. QUE ESTA APAGADA.-\"",
    "808,NORMAL,21/10/2026,05:10,MEC. ENRIQUEZ C/A.-",
    "808,NORMAL,21/10/2026,05:50,MEC. SILVA DA NORMAL.-",
    "813,NORMAL,21/10/2026,06:41,CAMBIO 12 BOULOGNE SIN COMPROBACION.-",
    "813,NORMAL,21/10/2026,07:52,NORMAL.-",
    # Comillas internas sin escapar, como vienen en el reporte
    "817,PENDIENTE,21/10/2026,09:06,HABILITAN ESTACIONES \"B\" CON CUSTODIA POR FALTA DE PERSONAL.-",
    "820,NORMAL,21/10/2026,10:14,PAN AV. MARQUEZ BARRERA ROTA.-",
    "820,NORMAL,21/10/2026,10:58,\"MEC. ACUÑA REPARA, DA NORMAL, SIN CUSTODIA.-\"",
    "821,NORMAL,21/10/2026,10:31,FALTA ENERGIA EN SUBESTACION PILAR.-",
    "821,NORMAL,21/10/2026,10:41,NORMAL ENERGIA.-",
    # 790 vuelve a aparecer separado por otros números
    "790,PENDIENTE,20/10/2026,22:50,SIGUE SIN COMPROBACION.-",
    "824,NORMAL,21/10/2026,10:45,TENSION BAJA EN ABRIGO 3.-",
    "824,NORMAL,21/10/2026,11:51,MEC. LOPEZ COMPRUEBA EL NORMAL FUNCIONAMIENTO.-",
]


def generar():
    ARCHIVO.parent.mkdir(exist_ok=True)
    ARCHIVO.write_bytes(("\r\n".join(LINEAS) + "\r\n").encode("cp1252"))


if __name__ == "__main__":
    generar()
    print(f"Creado {ARCHIVO}")
