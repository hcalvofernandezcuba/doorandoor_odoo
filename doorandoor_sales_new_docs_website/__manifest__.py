# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Sales New Docs Website",
    "version": "18.0.1.0.3",
    "category": "Website",
    "summary": "Publish DoorAndDoor Sales New Markdown docs on the website",
    "description": """
DoorAndDoor Sales New Docs Website
==================================

Este modulo publica en el website la documentacion Markdown del proyecto
`doorandoor_sales_new` leyendo directamente los archivos del directorio `docs`.

Objetivo:
- mantener la documentacion en el mismo repositorio
- editarla desde el IDE habitual del proyecto
- mostrarla en el website sin duplicar contenido

Incluye las guias informativas usadas para capacitacion de usuarios
despues de cada mejora operativa importante del modulo principal,
incluyendo reglas de reserva temporal, stock visible y documentos operativos.
    """,
    "author": "Hanoi Calvo Fernández (doorandoor)",
    "website": "https://doorandoor.com",
    "depends": [
        "website",
        "doorandoor_sales_new",
    ],
    "data": [
        "data/website_menu.xml",
        "views/docs_templates.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
