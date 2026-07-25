# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Stock Labels",
    "version": "18.0.1.0.40",
    "category": "Inventory",
    "summary": "18.0.1.0.40 - Corrige layout del label de factura y fabricacion en Odoo CE 18",
    "description": """
DoorAndDoor Stock Labels
========================

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

    """,
    "author": "Hanoi Calvo Fernandez for Doorandoor",
    "website": "https://gestion.doorandoor.com",
    "depends": [
        "stock",
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
        "report/document_label_report.xml",
        "report/product_label_report.xml",
        "report/stock_label_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
