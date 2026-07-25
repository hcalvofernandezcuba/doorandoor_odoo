# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Tax State",
    "version": "18.0.1.0.1",
    "category": "Accounting",
    "summary": "State-based sales tax mapping by company for multi-company flows",
    "description": """
DoorAndDoor Tax State
=====================

Objetivo
--------

Este modulo agrega una capa simple y controlada para manejar impuestos de
venta por estado dentro de un entorno multicompañia en Odoo.

La logica sigue el comportamiento estandar de Odoo:
- el documento pertenece a una compania
- la compania define su estado fiscal
- las ventas y facturas usan el impuesto de venta asociado a ese estado

Alcance funcional
-----------------

- Campo de estado fiscal en la compania.
- Regla por compania y estado para enlazar un impuesto de venta.
- Aplicacion automatica del impuesto en lineas de venta.
- Aplicacion automatica del impuesto en lineas de factura de cliente.

Esta primera version no intenta resolver todavia fiscalidad avanzada de
USA como condados, ciudades, exenciones o destino del cliente.
Su objetivo es dejar una base limpia, consistente y compatible con la
contabilidad multicompañia de Odoo.

Control de versiones
--------------------

- `18.0.1.0.0`
  Version inicial del modulo con mapeo de impuesto de venta por estado y compania.

- `18.0.1.0.1`
  Se alinea la herencia del reporte de factura para conservar el bloque consolidado `Total de impuestos` definido por DoorAndDoor.
    """,
    "author": "Hanoi Calvo Fernandez (doorandoor)",
    "website": "https://doorandoor.com",
    "depends": [
        "account",
        "sale_management",
        "doorandoor_sales_new",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/doorandoor_tax_state_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
