# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Purchase Fixed Warehouse",
    "version": "18.0.1.0.5",
    "category": "Purchases/Inventory",
    "summary": "18.0.1.0.5 - Incorpora identidad corporativa de doorandoor a compras por almacén",
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
        "doorandoor_stock_labels",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/purchase_order_views.xml",
        "views/stock_receipt_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
