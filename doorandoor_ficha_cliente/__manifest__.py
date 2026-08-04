# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Ficha de Cliente",
    "version": "18.0.1.0.2",
    "category": "Contacts",
    "summary": "18.0.1.0.2 - Añade trazabilidad de constructores en clientes, cotizaciones, facturas y tablero de gestión",
    "description": """
DoorAndDoor Ficha de Cliente
============================

Objetivo
--------

Extender la ficha del cliente para registrar el constructor o
instalador asociado a la venta, creando una referencia cruzada util
para marketing, garantias comerciales y trazabilidad operativa.

Alcance inicial
---------------

- catalogo propio de constructores o instaladores
- campo asociado en la ficha del contacto
- vista operativa de clientes por constructor
- agrupaciones base para analisis comercial

Historial resumido
------------------

- 18.0.1.0.0
  Se crea el modulo `doorandoor_ficha_cliente` con un catalogo propio
  de constructores o instaladores, un campo asociado en `Contactos` y
  un reporte base para consultar que clientes quedan vinculados a cada
  constructor.

- 18.0.1.0.1
  El constructor asociado del cliente se propaga tambien a
  `sale.order` mediante un campo relacionado almacenado. Con esto la
  informacion queda lista para tableros y reportes comerciales basados
  en ventas reales por constructor.

- 18.0.1.0.2
  Se amplía el modulo para dejar trazabilidad de constructores en
  clientes, cotizaciones, facturas y un tablero de gestión con métricas
  por vendedor y volumen de constructores asociados.
    """,
    "author": "Hanoi Calvo Fernandez for Doorandoor",
    "website": "https://gestion.doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "contacts",
        "mail",
        "sale",
        "account",
        "crm",
        "doorandoor_sales_new",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/builder_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
