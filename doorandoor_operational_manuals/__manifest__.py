{
    "name": "DoorAndDoor Centro de Guias Operativas",
    "version": "18.0.1.0.2",
    "category": "Operations",
    "summary": "18.0.1.0.2 - Publica la guia 1.2 completa de logistica historica",
    "description": """
DoorAndDoor Centro de Guias Operativas
=======================================

Version 18.0.1.0.0
-------------------

* Crea un centro interno independiente de la documentacion general.
* Permite consultar, abrir, descargar e imprimir el PDF vigente de cada
  operacion sin conceder permisos de edicion.
* Limita cada manual por usuario o grupo funcional y conserva version,
  vigencia, area, modulo, audiencia y registro de cambios.
* Publica el primer paquete de guias de logistica historica e inventario.

Version 18.0.1.0.1
-------------------

* Abre todas las guias publicadas a todos los usuarios internos del sistema,
  sin compartimentarlas por area, usuario o almacen.
* Mantiene bloqueada la consulta para usuarios publicos y de portal y conserva
  la edicion exclusivamente para administradores de guias.

Version 18.0.1.0.2
-------------------

* Publica la version 1.2 de la guia de logistica historica con la matriz de
  procedimientos, ruta diaria unica y casos de productos especiales.
""",
    "author": "DoorAndDoor",
    "maintainer": "DoorAndDoor Soporte",
    "license": "LGPL-3",
    "depends": ["base", "mail", "web", "website"],
    "data": [
        "security/operational_manual_security.xml",
        "security/ir.model.access.csv",
        "views/operational_manual_views.xml",
        "views/operational_manual_templates.xml",
        "data/operational_manual_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "doorandoor_operational_manuals/static/src/css/manual_center.css",
        ],
    },
    "installable": True,
    "application": True,
}
