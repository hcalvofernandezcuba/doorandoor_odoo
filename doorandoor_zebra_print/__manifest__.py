# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Zebra Direct Print",
    "version": "18.0.1.0.1",
    "category": "Inventory",
    "summary": "18.0.1.0.1 - Compatibilidad HTTPS de Browser Print en macOS",
    "description": """
DoorAndDoor Zebra Direct Print
==============================

Integra los asistentes de etiquetas de DoorAndDoor con Zebra Browser Print.
Genera ZPL nativo para una Zebra ZD421 a 203 DPI y conserva la vista previa PDF
como alternativa segura.

- Almacén, producto y fabricación: 3x1 pulgadas (609x203 puntos).
- Factura y entrega: 4x6 pulgadas (812x1218 puntos).
- Descubrimiento automático de la impresora Zebra predeterminada del equipo.
- Mensajes explícitos de éxito o error antes de cerrar el asistente.
- Conexión segura mediante localhost para aceptar correctamente el certificado
  local de Zebra Browser Print en macOS.
""",
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": ["web", "doorandoor_stock_labels"],
    "data": [
        "views/zebra_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_zebra_print/static/src/js/zebra_print_action.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
