# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor User Access Matrix",
    "version": "18.0.1.0.1",
    "category": "Administration",
    "summary": "18.0.1.0.1 - Añade matriz de usuarios, compañías y grupos compatible con Odoo 18",
    "description": """
DoorAndDoor User Access Matrix
==============================

Proporciona a Administración/Ajustes una vista de solo consulta para auditar
los accesos efectivos configurados para cada usuario interno.

La matriz muestra usuario, acceso activo, compañías permitidas, condición de
administrador, cantidad de grupos y el detalle de los grupos/roles asignados.
No crea, elimina ni modifica permisos desde la propia matriz.
    """,
    "author": "DoorAndDoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "views/res_users_access_views.xml",
    ],
    "installable": True,
    "application": False,
}
