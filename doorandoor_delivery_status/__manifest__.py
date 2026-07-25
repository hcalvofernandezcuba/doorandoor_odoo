# -*- coding: utf-8 -*-
{
    'name': 'DoorAndDoor - Estado de Entrega en Picking',
    'version': '18.0.1.0.8',
    'category': 'Inventory/Sales',
    'summary': 'Muestra cantidad pedida, entregada y pendiente en las líneas de movimiento de entregas',
    'description': """
DoorAndDoor - Estado de Entrega en Picking
===========================================

Este módulo extiende las vistas de stock.picking para mostrar en cada línea
de movimiento (stock.move) la información de entrega relacionada con la venta:

* **Cantidad Pedida**: Lo que el cliente ordenó en la venta original
* **Cantidad Entregada**: Lo que se ha entregado en ESTE picking específico
* **Cantidad Pendiente**: Lo que falta por entregar (Pedida - Entregada)

Las columnas son visibles en:
- Formulario de Picking (líneas de movimiento)
- Operaciones Detalladas (líneas de movimiento detalladas)
- Vista Tree de Movimientos
- Vista Form de Movimiento

Características:
----------------
* Campos compute que se actualizan en tiempo real
* Columnas readonly excepto la cantidad entregada
* Colores decorativos: verde si pendiente = 0, rojo si negativo
* Integrado con el módulo doorandoor_sale_delivery_button

Autor: DoorAndDoor Team
    """,
    'author': 'DoorAndDoor',
    'website': 'https://doorandoor.com',
    'depends': [
        'doorandoor_sale_delivery_button',
        'stock',
        'sale',
        'sale_stock',
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
