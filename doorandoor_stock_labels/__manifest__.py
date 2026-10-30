# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Stock Labels",
    "version": "18.0.1.4.1",
    "category": "Inventory",
    "summary": "18.0.1.4.1 - Acceso comercial prepara despacho y labels serializados",
    "description": """
DoorAndDoor Stock Labels
========================

Version 18.0.1.0.47
-------------------

Renderiza cada módulo del Code128 con tres píxeles para conservar el ancho y
la separación de las barras al convertir el reporte a PDF e imprimirlo. Evita
que las cámaras móviles reciban líneas mezcladas por reducción subpíxel.

Este modulo agrega una primera version de etiquetas para recepcion de
inventario en DoorAndDoor.

Objetivos funcionales
---------------------

- Configurar en el producto si imprime etiqueta al recibir.
- Definir si la etiqueta usa codigo interno o codigo de barras.
- Imprimir etiquetas desde recepciones de inventario.
- Generar etiquetas por numero de serie o, si no existe seguimiento
  individual, por cantidad recibida.
- Incluir QR con URL navegable al registro del producto en Odoo para
  escaneo desde moviles.
- Incluir Code128 para lectura por hand scanners / hangers.

Alcance inicial
---------------

- Se apoya en el tracking estandar de Odoo.
- No fuerza la generacion automatica de seriales; usa los ya registrados
  en la recepcion.
- Si el producto no usa seriales o lotes, permite imprimir etiquetas por
  cantidad recibida.

Historial resumido
------------------

- 18.0.1.4.1
  Renombra la acción comercial para expresar que prepara el despacho antes de
  imprimir y añade la referencia de la operación al label 4x6. La reserva y
  auditoría de seriales se implementan en Mobile Hanger sin alterar las reglas
  existentes de pago ni fulfillment.

- 18.0.1.4.0
  Generaliza el conteo con hanger para operaciones autorizadas por módulos
  operativos. Las recepciones conservan productos adicionales; entregas y
  traslados solo pueden contar productos ya previstos en el documento.

- 18.0.1.3.2
  Incorpora un punto de extensión para autorizar conteos con hanger en otras
  operaciones controladas, conservando por defecto la restricción a recepciones.

- 18.0.1.3.1
  Devuelve al lector móvil el producto y la cantidad acumulada después de cada
  disparo, permitiendo continuar el conteo sin recargar el formulario.

- 18.0.1.3.0
  Separa las cantidades esperadas de las cantidades fisicamente contadas,
  conserva las lecturas por recepcion y permite agregar productos no previstos
  mediante barcode, referencia interna o codigo propio del label. Las lecturas
  no modifican existencias; las cantidades se preparan al aplicarlas y solo la
  validacion normal de la recepcion actualiza el inventario.

- 18.0.1.2.2
  Separa la resolución física de la Zebra (203 DPI) de la resolución CSS del
  PDF (96 DPI). Evita que wkhtmltopdf reduzca texto y barcode a menos de la
  mitad del área disponible en la hoja 3x1.

- 18.0.1.2.1
  Amplía tipografías, área informativa y código de barras en los reportes
  pequeños para aprovechar visualmente toda la hoja física 3x1 sin recortes.

- 18.0.1.2.0
  Ajusta el label pequeño al rollo Zebra real de 3 pulgadas de ancho por
  1 pulgada de alto, una etiqueta por página. Lo mantiene predeterminado para
  producto, recepción y fabricación; las facturas destinadas a entregas usan
  4x6 vertical de forma predeterminada.

- 18.0.1.1.4
  Recupera para los labels grandes la geometría estable de papel 102x152 mm
  gestionada por Odoo. Evita el desborde introducido al forzar dimensiones
  decimales simultáneamente en wkhtmltopdf y CSS, sin modificar el formato
  pequeño ni el selector de tamaño.

- 18.0.1.1.3
  Eleva cuatro puntos en total el bloque textual de la etiqueta pequeña,
  conservando sin cambios la posición y el tamaño del código de barras.

- 18.0.1.1.2
  Eleva dos puntos el bloque textual de la etiqueta pequeña y conserva intactos
  la posición y el tamaño del código de barras. Muestra la variante del producto
  inmediatamente debajo del almacén y lo selecciona por defecto desde Producto.

- 18.0.1.1.1
  Añade tolerancia interna de 0,6 mm al formato grande sin modificar el papel
  físico 4x6, evitando que el contenido salga del área visible por redondeo.

- 18.0.1.1.0
  Agrega el selector Tamaño de etiqueta a los asistentes de productos,
  recepciones, facturas y fabricación. Permite escoger el formato grande Zebra
  4x6 o el formato pequeño correspondiente a cada flujo antes de imprimir.

- 18.0.1.0.55
  Conserva el salto físico estable entre etiquetas y evita generar una hoja
  vacía después de la última etiqueta del lote.

- 18.0.1.0.54
  Elimina el ancho adaptable del contenedor HTML y fuerza un salto físico por
  etiqueta para que la posición no se desplace en impresiones multipágina.

- 18.0.1.0.53
  Usa las medidas físicas exactas 101,6 x 152,4 mm del papel Zebra 4x6 tanto
  en el formato PDF como en cada página, evitando desplazamiento acumulado a
  partir de la tercera o cuarta etiqueta.

- 18.0.1.0.52
  Los labels de factura muestran todos los atributos reales de la variante y
  las opciones informativas guardadas en la línea, incluyendo Marca, Alto y
  Ancho/Medidas, sin duplicarlos.

- 18.0.1.0.51
  Declara la dependencia de Manufactura usada por los labels de OF para que el
  modulo pueda instalarse correctamente en una base limpia.

- 18.0.1.0.50
  Ajusta el reporte al rollo Zebra real de 4 pulgadas de ancho por 6 de alto.
  El contenido se mantiene vertical y se distribuye de arriba hacia abajo para
  ocupar todo el espacio disponible, con un único label ampliado por página.

- 18.0.1.0.49
  Define un papel PDF real de 4x6 pulgadas en orientación vertical para Zebra.
  Los labels de producto se amplían al ancho útil y se imprimen hasta dos por
  hoja, sin rotación horizontal ni escalado desde un formato A4.

- 18.0.1.0.48
  El conteo de recepciones acepta el barcode detectado directamente por el
  lector móvil, incrementa una unidad de la variante esperada y limpia el campo
  para la siguiente lectura sin depender de guardar manualmente el wizard.

- 18.0.1.0.24
  Continúa el autoserie diario por producto y actualiza manuales de uso y pruebas.

- 18.0.1.0.25
  Amplia la impresion de labels para emitir una etiqueta por lote completo en productos con tracking por lote y agrega un modo de impresion por codigo de producto para preparar etiquetas uniformes destinadas a proveedores.

- 18.0.1.0.26
  Agrega el wizard `Recibir con hanger` para pruebas completas del flujo de recepcion, abriendolo desde `Comprobar disponibilidad` en recepciones entrantes y permitiendo contar una unidad por cada disparo escaneado.

- 18.0.1.0.27
  Ajusta la visibilidad del boton `Recibir con hanger` para mostrarlo siempre en recepciones entrantes, sin depender del estado operativo visible en esta base Odoo 18 CE.

- 18.0.1.0.28
  Extiende el asistente de registro previo para soportar tanto productos con tracking por lote como por serial, evitando que `Print Labels` siga bloqueando productos por lote por falta de un tracking cargado en la recepcion.

- 18.0.1.0.29
  Ajusta la edicion del campo `Lot / Serial Number` en el wizard de registro previo para que el usuario pueda capturar el numero de lote o serial directamente en la grilla de Odoo 18 CE.

- 18.0.1.0.30
  Corrige la carga de lineas en los wizards de recepcion usando `move_ids` en lugar de `move_ids_without_package`, de modo que los productos esperados se muestren correctamente en esta base Odoo 18 CE.

- 18.0.1.0.32
  Corrige el flujo de `Recibir con hanger` creando el wizard ya poblado desde servidor, evitando que la UI abra registros transitorios con lineas vacias y permitiendo reconocer correctamente referencias como `DTP-00080`.

- 18.0.1.0.33
  Ajusta `Recibir con hanger` para preservar el lote ya registrado en productos con tracking por lote y bloquear con mensaje claro los productos con tracking por serie hasta que se registren sus seriales reales.

- 18.0.1.0.34
  Agrega un flujo independiente de `Labels de productos` desde la vista de producto.
  Incorpora un wizard con almacen seleccionable, campos propios de label en el producto y un reporte dedicado cuyo barcode usa el nuevo `Codigo de producto`.

- 18.0.1.0.35
  Corrige la insercion del boton `Labels de productos` en la vista real de `product.template` usada por Odoo CE 18.
  Se actualiza tambien el `summary` para mantener visible en el manifest el avance actual del modulo.

- 18.0.1.0.36
  Refuerza la visibilidad del acceso a `Labels de productos` agregando tambien un boton directo en el encabezado del formulario de producto.
  Esto evita depender solo del layout de botones estadisticos de la vista en Odoo CE 18.

- 18.0.1.0.37
  Reubica el boton `Labels de productos` junto al boton estandar `Imprimir etiquetas` en la vista de producto.
  Se mantiene ademas el acceso tipo stat para no perder redundancia funcional en Odoo CE 18.

- 18.0.1.0.38
  Agrega el permiso de acceso faltante para `ddsl.product.label.wizard`.
  Esto permite abrir el asistente de `Labels de productos` desde la vista de producto sin error de acceso.

- 18.0.1.0.39
  Agrega una primera version del flujo comun de `Labels de factura` y `Labels de fabricacion`.
  Se incorporan botones en `Factura` y `MO`, un wizard comun y un reporte PDF compartido que muestra documento, cliente, datos del producto, usuario que preparo el documento y usuario que lanza el label.

- 18.0.1.0.40
  Simplifica el layout del label de `Factura / Fabricacion` para evitar salidas en blanco por maquetacion inestable.
  El reporte usa una composicion mas lineal y robusta para su primera validacion en PDF dentro de Odoo CE 18.

- 18.0.1.0.41
  Reestructura el reporte de `Labels de factura / fabricacion` usando una pagina QWeb por etiqueta.
  Esto busca evitar PDFs en blanco cuando el reporte se ejecuta desde wizard en Odoo CE 18.

- 18.0.1.0.42
  Reemplaza el renderer del label documental por el mismo patron visual estable usado en labels funcionales del modulo.
  Ademas bloquea el wizard con mensaje claro si una factura no genera payloads, evitando PDFs vacios silenciosos.

- 18.0.1.0.43
  Corrige la deteccion de lineas validas en `Labels de factura` para esta base Odoo CE 18.
  Ahora el wizard incluye lineas con `display_type = product`, evitando que facturas validas queden sin payloads y muestren error falso.

- 18.0.1.0.45
  `Labels de productos` deja de bloquear plantillas sin Codigo de producto,
  referencia interna o barcode. Se reutiliza el codigo de la variante unica
  cuando existe y, como ultimo respaldo, se genera una referencia estable
  `DDSL-P<id>` para poder imprimir el label sin alterar el producto.

- 18.0.1.0.46
  El asistente muestra y permite editar `Codigo de producto para label`.
  Cuando esta vacio presenta una advertencia clara y una vista previa del
  codigo automatico que se imprimira, evitando depender de conocimiento
  previo del usuario.

    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": [
        "stock",
        "mrp",
        "product",
        "doorandoor_product_config",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/stock_serial_wizard_views.xml",
        "wizard/stock_label_wizard_views.xml",
        "wizard/product_label_wizard_views.xml",
        "wizard/document_label_wizard_views.xml",
        "wizard/stock_receipt_scan_wizard_views.xml",
        "views/product_views.xml",
        "views/account_move_views.xml",
        "views/mrp_production_views.xml",
        "views/stock_picking_views.xml",
        "report/label_paperformat.xml",
        "report/document_label_report.xml",
        "report/product_label_report.xml",
        "report/stock_label_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
