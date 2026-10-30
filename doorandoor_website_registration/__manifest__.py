{
    "name": "DoorAndDoor Website Registration",
    "version": "18.0.1.2.1",
    "category": "Website",
    "summary": "18.0.1.2.1 - OTP de registro a lista interna Telegram, términos, perfil y compras",
    "description": """
Registro público DoorAndDoor para clientes particulares, constructores y
clientes asociados a una constructora. Crea exclusivamente usuarios de portal,
recoge los datos de contacto y dirección necesarios, y permite al cliente
mantener su información y consultar sus compras sin acceso al backend.

La asociación con constructor se captura como texto libre. Nunca se publica ni
se entrega al navegador la lista interna de constructores registrados.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "auth_signup",
        "portal",
        "sale_management",
        "account",
        "doorandoor_ficha_cliente",
        "doorandoor_website_brand",
    ],
    "data": [
        "views/res_partner_views.xml",
        "views/signup_templates.xml",
        "views/portal_templates.xml",
        "views/legal_templates.xml",
        "data/website_menu.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "doorandoor_website_registration/static/src/scss/registration.scss",
            "doorandoor_website_registration/static/src/js/registration.js",
        ],
    },
    "installable": True,
    "application": False,
}
