# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Ficha de Cliente",
    "version": "18.0.1.0.9",
    "category": "Contacts",
    "summary": "18.0.1.0.4 - Corrige visualización del campo constructor en facturas y completa acciones de dashboard",
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

- 18.0.1.0.3
  Se añade persistencia para el campo `ddfc_pricing_source` en cotizaciones
  y facturas, con migración que crea la columna en la base de datos
  cuando la instancia ya existe.

- 18.0.1.0.7
  Se ajusta el anclaje de la vista de `account.move` para que el campo
  `ddfc_builder_id` aparezca de forma estable en el flujo
  `Cotización -> Prefactura -> Factura` de `doorandoor_sales_new`,
  con una vista fallback para otros formularios de `account.move`.

- 18.0.1.0.8
  Se corrige la propagación del constructor en `account.move` para
  respetar cambios manuales, heredar en notas de crédito desde la
  factura origen (`reversed_entry_id`) y usar el constructor del cliente
  como fallback cuando aplique.

- 18.0.1.0.9
  El campo de constructor en cotizaciones y facturas se ajusta para
  crear solo constructores nuevos desde el flujo, bloqueando la
  seleccion de constructores existentes. El descuento y los campos
  inferiores se aplican solo cuando el constructor fue creado en este
  proceso nuevo.
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
