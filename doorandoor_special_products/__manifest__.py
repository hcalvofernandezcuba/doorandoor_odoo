{
    "name": "DoorAndDoor Transformed and Special Products",
    "version": "18.0.4.8.1",
    "category": "Sales/Manufacturing",
    "summary": "18.0.4.8.1 - Programa el archivo de cada LdM especial a los 30 días",
    "description": """
18.0.4.8.1
------------
Todo producto especial nuevo queda programado desde su creación para archivarse
junto con su LdM a los 30 días. La actividad comercial posterior renueva el
plazo y el proceso conserva los bloqueos por stock, movimientos, fabricación,
ventas o facturas abiertas para no romper la trazabilidad.

18.0.4.8.0
------------
Incorpora el rol Ventas / Creador de plantillas maestras especiales. Sus
usuarios pueden declarar desde una cotizacion o factura abierta que la
plantilla no existe y crearla junto con el primer Especial, conservando
familia, atributos, componentes, operaciones, precio y autor. No concede
edicion general del catalogo ni permisos de Administrador/Ajustes.

18.0.4.7.2
------------
La confirmación de una factura por un vendedor limitado actualiza con elevación
técnica únicamente las fechas de venta, actividad y archivo del producto
Especial. El vendedor conserva bloqueada toda edición general del catálogo.

18.0.4.7.1
------------
Los asistentes continúan heredando internamente el costo del producto base sin
exponerlo al vendedor, aun cuando el campo de costo queda restringido a
Administrador/Ajustes.

18.0.4.7.0
------------
Las plantillas Especiales autorizadas, inicialmente EMC WINDOWS, permiten al
comercial introducir el precio vigente del proveedor. El valor se conserva en
la cotizacion o factura sin abrir la edicion de precios de otros productos.

18.0.4.6.2
------------
Los comerciales pueden agregar un producto Especial desde cotizaciones y
facturas sin recibir permiso general para modificar el catalogo. La fecha de
actividad y archivo del Especial se actualiza de forma tecnica y controlada.

18.0.4.6.1
------------
Especiales y Transformados muestran un precio de solo lectura calculado como
precio base mas adicional administrativo de la variante. El servidor recalcula
el importe al confirmar y no acepta el valor enviado por el navegador.

18.0.4.6.0
------------
El precio de los asistentes de Especiales y Transformados es de solo lectura
para Ventas y únicamente puede cambiarlo un administrador de Ajustes.

18.0.4.5.2
------------
El acceso para agregar productos Especiales queda oculto y bloqueado cuando
una prefactura ya fue confirmada.

18.0.4.5.1
------------
Cotizaciones, prefacturas y facturas muestran el nombre limpio del producto en
la primera linea y cada atributo/valor debajo, tanto para productos normales
como Especiales y Transformados.

18.0.4.5.0
------------
El asistente de Especial permite seleccionar una variante como configuración
base, conserva todos sus atributos y modifica únicamente los marcados. La LDM
se construye seleccionando componentes y operaciones de la receta maestra,
permitiendo excluir, ajustar o agregar elementos sin alterar la plantilla.

18.0.4.4.0
------------
La interfaz, los mensajes, los documentos y los nombres generados usan ahora el
concepto Producto transformado. Se conservan los identificadores tecnicos para
mantener compatibilidad con los datos y flujos existentes. La variante final se
crea explicitamente cuando los atributos del producto son dinamicos.
Los productos transformados quedan fuera de los selectores de nuevas lineas
comerciales y permanecen visibles en los documentos donde ya fueron usados.
Se incorporan familias WINDOWS y DOORS, seleccion de LDM maestra, copia de sus
componentes y operaciones al transformado, trazabilidad en la MO y mensajes de
salida a Produccion en cotizaciones, prefacturas y facturas impresas.
Se separan los flujos: Transformado consume un producto terminado existente;
Especial nace desde una plantilla maestra, crea todos sus valores de variante,
su producto almacenable y su LDM de materias primas desde el documento de venta.
Incluye una guia operativa detallada para configurar WINDOWS SH como plantilla
maestra y hacerla visible en el asistente de Ventas.
El asistente Especial permite seleccionar atributos existentes, agregar o
quitar filas y crear valores nuevos sin incorporarlos previamente al catalogo.
Tambien permite definir atributos completamente nuevos; el Especial se crea
como producto independiente sin quedar limitado por los atributos de la maestra.
La LDM maestra pasa a ser opcional. Sin receta se genera automaticamente una
LDM editable con tres bisagras por unidad, y las reglas sin componente se omiten.
Cotizaciones, prefacturas y facturas conservan el codigo y nombre del Especial,
mostrando debajo cada atributo y su valor en una linea independiente.
Cada producto personalizado recibe automaticamente un barcode EAN-13 unico,
separado de su referencia interna ESP y compatible con lectores y etiquetas.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "doorandoor_sales_new",
        "doorandoor_control_cobros",
        "doorandoor_product_config",
        "mrp",
        "stock",
    ],
    "data": [
        "security/special_product_security.xml",
        "security/ir.model.access.csv",
        "data/special_product_sequence.xml",
        "data/special_product_cron.xml",
        "wizard/special_product_wizard_views.xml",
        "wizard/special_from_master_wizard_views.xml",
        "views/ddpc_variant_selector_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/product_template_views.xml",
        "views/mrp_bom_views.xml",
        "views/mrp_production_views.xml",
        "views/commercial_report_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_special_products/static/src/js/product_configurator_special.js",
            "doorandoor_special_products/static/src/xml/product_configurator_special.xml",
        ],
    },
    "installable": True,
    "application": False,
}
