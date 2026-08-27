{
    "name": "DoorAndDoor Transformed and Special Products",
    "version": "18.0.4.6.1",
    "category": "Sales/Manufacturing",
    "summary": "18.0.4.6.1 - Calcula Especiales y Transformados desde el precio administrativo de variante",
    "description": """
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
