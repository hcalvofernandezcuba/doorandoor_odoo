# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Ficha de Cliente",
    "version": "18.0.1.1.9",
    "category": "Contacts",
    "summary": "18.0.1.1.9 - Mantiene el descuento automático bajo el control administrativo de precios",
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

- 18.0.1.1.0
  Se añade un wizard para completar los datos del constructor al crearlo,
  permitiendo llenar la información del contacto asociado y marcarlo
  automáticamente con la etiqueta "Constructor" para que siempre quede
  identificado como tal, aunque funcione como cliente normal del negocio.

- 18.0.1.1.4
  Se deja el módulo preparado para un flujo de versionado más riguroso,
  registrando en la versión actual el resumen de cambios del desarrollo
  del flujo de constructor para ventas y facturas.

- 18.0.1.1.5
  Se simplifica la interfaz del flujo de constructor dejando un único
  campo de entrada visible para ventas y facturas, sin mostrar campos
  redundantes del constructor en el formulario.

- 18.0.1.1.6
  Se deja visible solo la acción de crear constructor en factura y se
  muestra el campo asociado únicamente cuando ya existe un constructor
  enlazado al documento.

- 18.0.1.1.7
  Se aplica el mismo criterio en ventas para que el usuario vea solo la
  acción de crear constructor y el campo asociado únicamente cuando ya
  exista un constructor enlazado.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
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
        "views/builder_profile_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
