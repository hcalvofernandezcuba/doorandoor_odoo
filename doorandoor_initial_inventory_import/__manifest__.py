# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Initial Inventory Import",
    "version": "18.0.1.3.1",
    "category": "Inventory/Inventory",
    "summary": "18.0.1.3.1 - Permite forzar solo ITEMs coincidentes y protege ediciones reales",
    "description": """
DoorAndDoor Initial Inventory Import
====================================
Asistente de preparación para inventarios iniciales. Lee los formatos PDF de
Tampa Warehouse y Tampa Store, convierte cada fila en una línea auditable,
intenta identificar la variante Odoo correspondiente y bloquea cualquier
ajuste mientras existan filas ambiguas, incompletas o sin ITEM equivalente.

El análisis no modifica stock. Tras corregir y validar todas las líneas, un
responsable puede aplicar las cantidades físicas a la ubicación seleccionada.

Version 18.0.1.2.0
------------------

Adapta el formato Tampa Warehouse a las filas reales del PDF. Conserva puertas
con celdas vacías, herrajes, marcos y molduras; recompone la fila de molding que
pdftotext divide en dos líneas y mantiene como pendientes las cantidades
realmente ausentes, sin asumir ceros ni descartar productos.

Version 18.0.1.2.1
------------------

En filas de puertas sin color propone white y en cantidades vacías propone
cero. Ambos valores permanecen editables, quedan marcados con su motivo y deben
confirmarse expresamente antes de validar el lote.

Version 18.0.1.3.0
------------------

Agrega Force matched ITEMs only para excluir de una carga las líneas pendientes
o ambiguas que nunca fueron editadas. Las conserva como evidencia y protege las
correcciones manuales; validar y aplicar procesan únicamente las líneas
incluidas.

Version 18.0.1.3.1
------------------

Evita que el emparejamiento automático marque como edición humana las líneas
pendientes o ambiguas, para que el forzado proteja únicamente correcciones
reales realizadas por el usuario.
""",
    "author": "Hanoi Calvo Fernández -- DoorAndDoor",
    "license": "LGPL-3",
    "depends": ["stock", "mail", "doorandoor_product_config"],
    "data": [
        "security/ir.model.access.csv",
        "data/inventory_import_sequence.xml",
        "views/inventory_import_views.xml",
        "wizards/inventory_import_wizard_views.xml",
        "views/inventory_import_menus.xml",
    ],
    "installable": True,
    "application": False,
}
