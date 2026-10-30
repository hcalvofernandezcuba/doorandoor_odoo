{
    "name": "Inventory Count by Variant and Items",
    "version": "18.0.1.29.1",
    "category": "Inventory/Inventory",
    "summary": "18.0.1.29.1 - Albaranes generan, imprimen y auditan todos sus labels asociados",
    "description": """
Version 18.0.1.21.0
-------------------

Permite continuar de forma auditable un lote serializado previamente validado.
La sesión aditiva conserva sus lecturas históricas aplicadas y, al reabrirse,
valida únicamente los seriales nuevos para evitar duplicar inventario. Agrega
la acción Imprimir labels nuevos, limitada a seriales que todavía no han creado
existencia, manteniendo intactos los labels históricos.

Version 18.0.1.22.0
-------------------

Incorpora el ingreso operativo de mercancía serializada enlazado a recepciones
y traslados. Los traslados reutilizan labels DoorAndDoor existentes; las
recepciones de proveedor pueden adoptar códigos compatibles o generar labels
nuevos. El producto, lote y seriales históricos permanecen protegidos, y el
cambio de almacén solo se confirma después de validar la operación de stock.

Version 18.0.1.23.0
-------------------

Ordena el nuevo ingreso comenzando por el almacén. Los administradores pueden
seleccionarlo y los operadores conservan visible su almacén autorizado. Los
documentos y lotes quedan limitados al almacén elegido; al escoger un lote de
almacenamiento se completa automáticamente el producto que contiene. Los
traslados para entrega mantienen su flujo independiente sin lote de almacén.

Version 18.0.1.24.0
-------------------

Permite cerrar traslados recibidos parcialmente usando únicamente los labels
contados con Hanger. Los faltantes permanecen fuera del almacén destino y se
notifican a Gerencia con documento, origen, destino, chofer, vehículo,
observación y evidencias. Separa este caso de la devolución por daño, disponible
solo para mercancía recibida físicamente y documentada con descripción e imagen;
la devolución reutiliza el movimiento inverso nativo de Odoo y conserva los
seriales afectados.

Version 18.0.1.25.0
-------------------

Restringe a Administrador/Ajustes los campos de costo del producto, costo y
valoración de existencias, costo de movimientos y capas de valoración. Los
vendedores conservan los precios comerciales de venta, mientras vendedores y
operadores de almacén dejan de recibir datos de costo en vistas o lecturas RPC.

Version 18.0.1.26.0
-------------------

Permite marcar productos de alto volumen, como Baseboard y molduras, para usar
un unico serial compartido por lote. La impresion conserva la cantidad de
labels solicitada con el mismo codigo; cada disparo repetido suma unidades y el
campo Cantidad por lectura permite registrar de una vez un conteo manual,
manteniendo usuario, fecha, numero de lecturas y cantidad auditables.

Version 18.0.1.26.1
--------------------

Garantiza que la validación de cargas serializadas aplique realmente el ajuste
de stock en Odoo 18. Evita cerrar una sesión dejando pendiente el asistente
nativo de trazabilidad cuando el producto usa el label compartido del módulo.

Version 18.0.1.26.2
--------------------

Selecciona primero el ITEM del documento para proponer únicamente lotes
compatibles del mismo producto. Los ingresos que generan un label compartido
reconocen la cantidad física completa sin duplicar el serial del lote.

Version 18.0.1.26.3
--------------------

Corrige el inicio del ingreso de mercancía para usuarios con acceso a varios
almacenes. Respeta el almacén operativo predeterminado y, si no existe uno,
permite buscar recepciones y traslados de todos los almacenes autorizados para
completar automáticamente el destino. Los operadores multialmacén pueden elegir
entre sus almacenes asignados sin ampliar el alcance de sus permisos.

Version 18.0.1.27.0
--------------------

Incorpora en cada recepción un flujo único por ITEM: prepara controles,
genera o reutiliza labels, propone lote compatible para reposición y permite
validar en una sola operación el inventario físico y lógico. Las cantidades
destinadas a ventas pueden dirigirse a predespacho sin contaminar un lote de
almacenamiento, incluso cuando el documento contiene destinos mixtos.

Version 18.0.1.27.1
--------------------

Valida directamente producto, almacén y estado del lote recién creado para
permitir continuar el flujo sin depender de una lista calculada aún no
refrescada.

Version 18.0.1.27.2
--------------------

La preparación por ITEM lee técnicamente la definición de su propia ventana
antes de abrirla. Los responsables de Inventario pueden completar Preparar
líneas sin recibir acceso general a acciones del sistema ni a Ajustes.

Version 18.0.1.27.3
--------------------

Los labels generados durante recepciones imprimen todos los valores del ITEM
aunque el producto histórico u operativo no tenga atributos relacionales. La
descripción entre paréntesis se distribuye en una segunda línea legible y evita
que el formato Zebra recorte medidas, mano, color o cristal.

Version 18.0.1.27.4
--------------------

Hace prevalecer los almacenes operativos asignados sobre los grupos
administrativos al consultar sesiones, líneas, lotes, seriales, reclamaciones y
recepciones. Evita que un responsable de Tampa y Central Warehouse cargue
sesiones de otras ciudades y reciba errores al resolver sus ubicaciones.

Version 18.0.1.27.5
--------------------

Al agregar unidades a un lote con serial compartido, imprime exactamente la
cantidad nueva de la operación y no la existencia acumulada del lote. Conserva
el mismo código compartido, los labels históricos y la trazabilidad del ingreso.

Version 18.0.1.27.6
--------------------

Permite crear un lote nuevo con una referencia física previamente cancelada
cuando el registro anterior ya no conserva labels activos. El lote histórico
se mantiene con una referencia de archivo única y una nota de trazabilidad,
mientras el nombre físico original queda libre para la nueva operación.

Version 18.0.1.27.7
--------------------

Separa la liberación física de una posición de la anulación documental. Un lote
sin contenido actual pasa a Posición liberada, conserva campaña, sesiones y
labels históricos, y deja su referencia disponible en cualquier campaña. La
anulación queda reservada para operaciones inválidas y se impide que dos lotes
activos ocupen simultáneamente la misma referencia del almacén.

Version 18.0.1.27.8
--------------------

Permite reutilizar en una sesión nueva la referencia física de un lote marcado
como Posición liberada. La sesión anterior permanece terminada y auditable,
mientras las referencias sin lote serializado o asociadas a lotes activos
continúan protegidas contra duplicados.

Version 18.0.1.27.9
--------------------

Centraliza en el modelo de sesión la comprobación de referencias históricas.
Solo desbloquea el proceso actual cuando el lote anterior está liberado o
anulado y no conserva contenido activo; la sesión, sus labels y su auditoría
permanecen intactos.

Version 18.0.1.28.0
--------------------

Permite marcar una posición como lote mixto para recibir labels de varios ITEM.
Cada serial conserva su producto y la impresión usa el ITEM real de cada label,
sin relajar unicidad, almacén ni historial. El lote mixto admite cantidades
superiores a 33 para combinar unidades de distinto volumen, como puertas y
bisagras; los lotes normales conservan su límite físico.

Version 18.0.1.28.1
--------------------

Al activar Lote mixto conserva el producto y cantidad ya seleccionados, los
procesa como primera carga y genera sus labels. Luego permite incorporar otros
ITEM sin perder la carga inicial ni su trazabilidad.

Version 18.0.1.28.2
--------------------

Evita que un traslado interno exija Administración/Ajustes al leer el
porcentaje técnico de costo de subproductos. Los importes de costo, costo
promedio y valoración continúan restringidos exclusivamente al administrador.

    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["stock", "barcodes", "mail", "doorandoor_stock_labels", "doorandoor_product_config", "doorandoor_process_control"],
    "data": [
        "security/inventory_count_security.xml",
        "security/ir.model.access.csv",
        "data/inventory_count_sequence.xml",
        "views/product_count_item_views.xml",
        "views/product_barcode_views.xml",
        "wizard/product_label_wizard_views.xml",
        "wizard/inventory_variant_selector_views.xml",
        "views/inventory_count_session_views.xml",
        "views/inventory_serial_views.xml",
        "views/inventory_serial_receipt_views.xml",
        "views/stock_quant_views.xml",
        "report/product_item_label_report.xml",
        "report/serial_audit_report.xml",
        "views/inventory_count_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_inventory_variant_count/static/src/scss/inventory_count.scss",
        ],
    },
    "application": True,
    "installable": True,
}
