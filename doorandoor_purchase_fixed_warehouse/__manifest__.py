# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Purchase Fixed Warehouse",
    "version": "18.0.1.3.0",
    "category": "Purchases/Inventory",
    "summary": "18.0.1.3.0 - Enruta por ITEM las compras entre lote y predespacho",
    "description": """
DoorAndDoor Purchase Fixed Warehouse
===================================

Este modulo obliga a que las ordenes de compra usen siempre el almacen configurado
en Ajustes para determinar el tipo de operacion de recepcion.

Comportamiento:
- permite seleccionar un almacen obligatorio desde Ajustes
- asigna automaticamente el tipo de recepcion de ese almacen en compras
- bloquea cambios manuales al tipo de operacion cuando la configuracion existe

Historial resumido
------------------

- 18.0.1.3.0
  Clasifica cada cantidad recibida según su origen logístico. Las reposiciones
  proponen un lote compatible; las cantidades vinculadas a factura u orden de
  entrega proponen predespacho, incluso dentro de una recepción mixta.

- 18.0.1.2.2
  Adapta la herencia del reporte de recepción al formato físico 3x1 y presenta
  el origen de la compra en una línea compacta sin impedir la actualización
  del módulo de etiquetas.

- 18.0.1.2.1
  Permite imprimir desde la recepción todos los productos comprados aunque no
  estén marcados individualmente y añade a esos labels el origen logístico.

- 18.0.1.2.0
  Selecciona el almacén a abastecer y distribuye automáticamente cada compra
  entre ventas pendientes y reposición, evitando asociaciones duplicadas.

- 18.0.1.1.0
  Registra por cantidad si una compra atiende una venta o una reposicion,
  muestra facturas y documentos origen en la orden/PDF y los imprime en los
  labels enviados al proveedor.

- 18.0.1.0.0
  Se crea el modulo para forzar el almacen de recepcion en compras, resaltar el boton de validar orden, agregar un reporte de entradas por almacen y exponer desde compras el flujo de lotes, seriales y labels.

- 18.0.1.0.1
  Se corrige el reporte de entradas para compatibilidad con Odoo 18 CE, reemplazando la vista `tree` por `list`.

- 18.0.1.0.2
  Se corrigen los campos del reporte de entradas para esta base Odoo 18 CE, eliminando el uso de `qty_done` en `stock.move.line` y reemplazandolo por cantidad planificada del movimiento y cantidad de linea compatible.

- 18.0.1.0.3
  Se mueven las acciones de `Registrar lotes/seriales` e `Imprimir labels` fuera del `header` de compras hacia el `button_box`, para no interferir visualmente con los reportes y acciones nativas del formulario de compra.

- 18.0.1.0.4
  Se ajusta el reporte de inventario con el nombre `Recepciones por almacen`, ubicado bajo Inventario, filtrado a recepciones validadas y orientado a mostrar por dia los productos y las cantidades recibidas por almacen.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": [
        "purchase_stock",
        "sale_management",
        "doorandoor_stock_labels",
        "doorandoor_sales_new",
        "doorandoor_inventory_variant_count",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_order_report.xml",
        "views/stock_receipt_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
