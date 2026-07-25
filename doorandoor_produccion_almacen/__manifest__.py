# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Produccion Almacen",
    "version": "18.0.1.0.4",
    "category": "Manufacturing",
    "summary": "Warehouse origin and destination flow for manufacturing orders",
    "description": """
DoorAndDoor Produccion Almacen
==============================

Objetivo
--------

Este modulo extiende la fabricacion para controlar el almacen origen y el almacen destino de entrega en cada orden de manufactura.
Fue disenado y se mantiene especificamente para Odoo Community Edition 18.

Alcance funcional
-----------------

- mostrar el almacen origen en la orden de manufactura
- permitir editar el almacen destino de entrega
- soportar ordenes creadas desde ventas y tambien ordenes creadas manualmente desde manufactura
- crear traslado interno al almacen destino antes del despacho al cliente
- alinear el picking de salida con el almacen destino definido en la produccion

Compatibilidad
--------------

- Odoo Community Edition 18
- No se asumen componentes de Enterprise
- Las herencias XML y el flujo se ajustan a la estructura real disponible en esta base CE 18

Historial resumido
------------------

- 18.0.1.0.0
  Version inicial del modulo.
  Se agrega soporte de almacen origen, almacen destino editable y traslado interno posterior a la fabricacion.

- 18.0.1.0.1
  Se habilita definir manualmente el almacen origen en ordenes de manufactura creadas directamente desde el modulo de Manufactura.
  Cuando la orden no viene desde ventas, el sistema propone un almacen por defecto de la compania y replica ese valor al almacen destino si aun no fue definido.

- 18.0.1.0.2
  La venta pasa a ser la fuente de verdad para `almacen origen` y `almacen destino`.
  Se agregan ambos campos en `sale.order`, se heredan a la `MO` al momento de crearla y quedan visibles en manufactura como referencia del flujo definido desde ventas.

- 18.0.1.0.3
  Se simplifica el flujo: el `almacen origen` de la orden de manufactura sale siempre del `warehouse_id` de la venta.
  En ventas solo queda editable el `almacen destino` del delivery, que tambien se hereda a la `MO` para el flujo logistico posterior.

- 18.0.1.0.4
  Se documenta de forma explicita la compatibilidad objetivo con Odoo Community Edition 18.
  Tambien se deja asentado que los errores de integracion y los ajustes correctivos forman parte del proceso normal de evolucion del modulo.
    """,
    "author": "Hanoi Calvo Fernández (doorandoor)",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "stock",
        "doorandoor_sales_new",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
}
