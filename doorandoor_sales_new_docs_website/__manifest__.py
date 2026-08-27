# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Sales New Docs Website",
    "version": "18.0.1.3.0",
    "category": "Website",
    "summary": "18.0.1.3.0 - Publica capacitación de cobros, inventarios y conteo móvil",
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
Publica las guias integrales de pruebas del proyecto y de configuracion de
productos normales, variantes, Transformados, Especiales y plantillas maestras.
La guia de pruebas consolida la secuencia vigente de producto, venta, pago,
fabricacion, credito, documentos, inventario y despacho.

18.0.1.3.0
------------
Publica tres guias operativas independientes para la capacitacion: cobros y
pagos controlados, ciclo integral de inventarios y conteo fisico mediante
hanger o movil. Las guias quedan visibles en el indice del website y describen
roles, pasos, resultados esperados y controles de cada operacion.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
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
