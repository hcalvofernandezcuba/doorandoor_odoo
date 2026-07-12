# -*- coding: utf-8 -*-
{
    'name': 'DoorAndDoor - Botón de Entrega desde Ventas',
    'version': '18.0.1.0.2',
    'category': 'Sales/Inventory',
    'summary': 'Permite al gestor de ventas navegar directamente al picking de entrega desde el pedido de venta confirmado',
    'description': """
DoorAndDoor - Botón de Entrega desde Ventas
============================================

Este módulo agrega un botón "Entregar" en el formulario de pedidos de venta confirmados,
permitiendo al gestor de ventas:

* Navegar directamente al picking de entrega relacionado
* Crear un nuevo picking si no existe uno en borrador
* Operar en el almacén de la empresa activa
* Gestionar entregas parciales (múltiples pickings por venta)

Flujo de negocio:
-----------------
1. Venta se confirma (el picking puede crearse automáticamente o no)
2. Gestor recibe pago/autorización fuera del sistema
3. Gestor presiona "Entregar" → navega al picking
4. Si existe picking en borrador: se abre ese
5. Si no existe: se crea uno nuevo en el almacén correcto
6. Gestor procesa la entrega desde Inventarios

Características:
----------------
* Botón de acción en el header del formulario de ventas
* Botón inteligente (stat button) con contador de entregas
* Campo formal sale_id en stock.picking para relación robusta
* Soporte para entregas parciales (múltiples pickings)
* Determinación automática del almacén según compañía activa
* Filtro de productos stockeables al crear picking
* Bloqueo visual y funcional del botón de entrega hasta pago total de la factura vinculada

Autor: DoorAndDoor Team
    """,
    'author': 'Hanoi Calvo Fernandez https://gestion.doorandoor.com',
    'depends': ['sale', 'stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
