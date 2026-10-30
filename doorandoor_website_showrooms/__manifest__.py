{
    "name": "DoorAndDoor Website Showrooms",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "18.0.1.0.0 - Bloque web administrable de oficinas con videos",
    "description": """
DoorAndDoor Website Showrooms
=============================
Centraliza las oficinas y salas de exposición publicadas en el website. Cada
oficina puede tener su imagen, datos de contacto y un video externo o MP4.
El bloque reutilizable se inserta desde el editor de Website sin editar código.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["website", "mail", "doorandoor_website_brand"],
    "data": [
        "security/ir.model.access.csv",
        "views/showroom_views.xml",
        "views/showroom_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "doorandoor_website_showrooms/static/src/scss/showrooms.scss",
        ],
    },
    "installable": True,
    "application": False,
}
