# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Auditoría General",
    "version": "18.0.1.1.0",
    "category": "Administration/Audit",
    "summary": "18.0.1.1.0 - Reporte PDF filtrable de las trazas de auditoría",
    "description": """
DoorAndDoor Auditoría General
=============================

Registra de forma inmutable quién, cuándo y desde qué contexto crea, modifica
o elimina datos maestros sensibles. La primera versión cubre precios y costos
de productos, precios adicionales de variantes, valores de atributos, productos
especiales, permisos de usuarios y almacenes asignados.

Historial de versiones
----------------------

18.0.1.1.0
~~~~~~~~~~~~

* Incorpora reporte PDF por rango de fechas, usuario, modelo y operación.
* Permite imprimir directamente las trazas seleccionadas en la lista.

18.0.1.0.0
~~~~~~~~~~~~

* Crea el registro central de auditoría protegido contra edición y borrado.
* Captura valores anteriores y nuevos por campo.
* Registra usuario, compañía, fecha, IP, URL, sesión y origen técnico disponible.
* Añade búsquedas por modelo, documento, usuario, operación, campo y fecha.
* Restringe la consulta a Administrador/Ajustes.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "DoorAndDoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "stock",
        "doorandoor_product_config",
        "doorandoor_process_control",
        "doorandoor_special_products",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/audit_log_views.xml",
        "views/audit_report_wizard_views.xml",
        "reports/audit_log_report.xml",
    ],
    "installable": True,
    "application": True,
}
