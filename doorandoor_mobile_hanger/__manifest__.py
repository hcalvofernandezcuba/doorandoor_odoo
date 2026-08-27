# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Mobile Hanger",
    "version": "18.0.1.5.8",
    "category": "Inventory/Operations",
    "summary": "18.0.1.5.8 - Activa cámara y conteo automático en recepciones",
    "description": """
DoorAndDoor Mobile Hanger
=========================

Primera fase de la interfaz móvil para operadores de almacén. Incorpora un
acceso independiente para escanear el código de una entrega, recepción,
traslado o entrada de fábrica, comprueba los almacenes autorizados del usuario
y abre una vista simplificada del movimiento nativo. Los QR de las entregas
apuntan a esta vista móvil sin alterar la lógica de inventario, pago o entrega.

Version 18.0.1.1.0
------------------

Convierte el icono informativo en un control funcional de cámara. Solicita la
cámara trasera del dispositivo, detecta QR y Code128 mediante las capacidades
seguras del navegador, completa el código leído y comunica claramente los
casos de permiso denegado o navegador incompatible.

Version 18.0.1.2.0
------------------

Integra html5-qrcode 2.3.8 (Apache-2.0) como lector alternativo. Usa la
detección nativa cuando está disponible y recurre a ZXing cuando Chrome o el
dispositivo no proporcionan BarcodeDetector, manteniendo QR y Code128 dentro
del mismo asistente de Odoo.

Version 18.0.1.2.1
------------------

Mantiene el contenedor HTML del lector montado durante todo el ciclo de la
vista y valida su referencia antes de iniciar la cámara. Evita la condición de
carrera de OWL que podía intentar crear html5-qrcode antes de renderizar el
elemento de video.

Version 18.0.1.2.2
------------------

Elimina el recorte cuadrado que podía excluir los extremos de Code128 largos,
decodifica todos los formatos soportados sobre el cuadro completo y agrega la
captura de una foto como alternativa móvil estándar usando el mismo motor
integrado, sin aplicaciones externas.

Version 18.0.1.3.0
------------------

Sustituye la deteccion en vivo de html5-qrcode y del detector incompleto del
navegador por el motor ZXing que incorpora Odoo 18. Solicita la camara trasera
en alta resolucion, analiza el cuadro completo y admite QR, Code128, EAN y los
demas formatos soportados por Odoo. La captura fotografica queda como respaldo
para QR y comunica que los codigos lineales se leen con la camara en vivo.

Version 18.0.1.4.0
------------------

Integra el lector movil con las sesiones auditables de conteo fisico por
variantes e items. Cada barcode reconocido registra automaticamente la cantidad
configurada, muestra existencias teoricas, conteo y diferencias, y conserva la
revision gerencial antes de aplicar cualquier ajuste de inventario.

Version 18.0.1.4.1
------------------

Agrega dentro del formulario movil un boton visible para iniciar la sesion,
cargar las existencias y activar el lector, evitando que el control quede
oculto en el encabezado compacto de Odoo. Traduce las acciones principales y
muestra una guia clara mientras la sesion permanece en borrador.

Version 18.0.1.4.2
------------------

Envia el barcode detectado directamente a la operacion de conteo, sin guardar
previamente todo el formulario movil. Elimina la carrera que producia el error
de barcode vacio y reduce el tiempo entre la lectura y su registro.

Version 18.0.1.4.3
------------------

Integra el boton de registro manual dentro del lector movil y conserva en el
componente el valor visible. Camara y escritura usan la misma operacion directa,
evitando una segunda llamada vacia desde el boton convencional del formulario.

Version 18.0.1.5.0
------------------

Optimiza la camara movil para EAN, UPC, Code128 y QR con resolucion equilibrada
y enfoque continuo. Muestra inmediatamente el producto, barcode, cantidad
acumulada y hora de la ultima lectura, y prioriza las lineas ya contadas.

Version 18.0.1.5.1
------------------

Restringe la lectura de labels DoorAndDoor a Code128 y exige dos detecciones
consecutivas iguales. Evita que un fragmento desenfocado sea interpretado como
un EAN corto distinto del barcode impreso.

Version 18.0.1.5.2
------------------

Agrega una lista operativa independiente con los productos ya contados,
ordenados por la lectura mas reciente, mostrando barcode, esperado, contado y
diferencia para evitar escaneos repetidos por falta de confirmacion visual.

Version 18.0.1.5.3
------------------

Prioriza el detector nativo optimizado de Chrome/Android y conserva ZXing como
respaldo. Lee una vez el Code128 verificado y usa una resolucion equilibrada,
reduciendo el tiempo de captura sin volver a habilitar EAN parciales.

Version 18.0.1.5.4
------------------

Sustituye el análisis manual de cuadros por el lector continuo html5-qrcode,
optimizado para la cámara trasera y una región horizontal Code128. Mantiene QR
para documentos y envía la primera lectura válida directamente al conteo.

Version 18.0.1.5.5
------------------

Analiza el cuadro completo para no recortar los extremos ni las zonas blancas
del Code128. Solicita alta definición y aplica enfoque continuo y zoom moderado
cuando la cámara Android los ofrece, conservando un ritmo estable de lectura.

Version 18.0.1.5.6
------------------

Conserva la región horizontal preferida por los operadores para encuadrar el
Code128 y mantiene el enfoque continuo y zoom cuando el móvil los soporte.

Version 18.0.1.5.7
------------------

Elimina la captura fotográfica alternativa y deja como única opción visual el
lector continuo Usar cámara, ya validado por los operadores en dispositivos
móviles. Conserva la entrada escrita para contingencias y lectores físicos.

Version 18.0.1.5.8
------------------

Integra el lector continuo Usar cámara dentro de Recibir con hanger. Cada
Code128 reconocido registra una unidad directamente, refresca las cantidades
contadas y conserva la escritura manual como contingencia.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "doorandoor_process_control",
        "doorandoor_stock_labels",
        "doorandoor_sales_new",
        "doorandoor_inventory_variant_count",
    ],
    "data": [
        "security/mobile_inventory_count_security.xml",
        "security/ir.model.access.csv",
        "views/mobile_picking_views.xml",
        "wizard/document_scan_wizard_views.xml",
        "views/menu_views.xml",
        "views/mobile_inventory_count_views.xml",
        "views/mobile_receipt_scan_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_mobile_hanger/static/lib/html5_qrcode/html5-qrcode.min.js",
            "doorandoor_mobile_hanger/static/src/js/camera_barcode_field.js",
            "doorandoor_mobile_hanger/static/src/xml/camera_barcode_field.xml",
        ],
    },
    "installable": True,
    "application": True,
}
