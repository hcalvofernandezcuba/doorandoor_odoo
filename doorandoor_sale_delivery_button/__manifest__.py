# -*- coding: utf-8 -*-
{
    'name': 'DoorAndDoor - Botón de Entrega desde Ventas',
    'version': '18.0.1.1.6',
    'category': 'Sales/Inventory',
    'summary': '18.0.1.1.6 - Sustituye Pre Order por prefactura en mensajes operativos',
    'description': """
DoorAndDoor - Botón de Entrega desde Ventas
============================================

Version 18.0.1.1.4
------------------
El botón estándar de Odoo para Entregas y su acción directa se sujetan a la
misma autorización de cobro o crédito. Un picking creado anticipadamente ya
no expone la operación hasta que la venta puede entregarse.

Los botones informativos deshabilitados se eliminan de cotizaciones y
prefacturas para que no induzcan un proceso operativo fuera de secuencia.

Version 18.0.1.1.1
------------------
Actualiza las ayudas visuales: el flujo nuevo se habilita por cobro total o
credito autorizado del PO de Ventas; los documentos historicos conservan la
exigencia de factura fiscal publicada y pagada.

Version 18.0.1.1.0
------------------
La entrega exige una factura fiscal publicada y totalmente pagada. La regla se
comprueba al abrir o crear la entrega y al crear, confirmar o reservar el
picking, cerrando tambien las rutas manuales desde Inventario.

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
    'author': 'Hanoi Calvo',
    'maintainer': 'doorandoor',
    'website': 'https://doorandoor.com',
    'depends': ['sale', 'stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
