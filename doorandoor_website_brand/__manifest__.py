# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Website Brand",
    "version": "18.0.1.1.4",
    "category": "Website/Theme",
    "summary": "18.0.1.1.4 - Restaura la edición visual del logo del encabezado",
    "description": """
DoorAndDoor Website Brand
=========================

Centraliza la identidad visual provisional de DoorAndDoor en el website:

- logo y favicon propios;
- nombre y metadatos de marca;
- sustitución de promociones visibles de Odoo en website y portal;
- estilos compatibles con escritorio y dispositivos móviles.

El módulo no modifica la marca ni la interfaz técnica del backend. Los recursos
se mantienen aislados para poder reemplazarlos cuando se entregue el manual de
identidad corporativa definitivo.

18.0.1.1.0
------------
Aplica la propuesta visual minimalista con Navy, Oro Suave, Gris Claro y Blanco.
Incorpora wordmark adaptable, lema comercial y estilos coherentes para navegación,
botones, enlaces, títulos, tarjetas y pie de página.

18.0.1.1.1
------------
Agrega un wordmark SVG nítido basado en la propuesta de identidad y un isotipo
cuadrado independiente para favicon y tamaños reducidos.

18.0.1.1.2
------------
Evita el recorte de la imagen provisional del bloque inicial de la portada.
La imagen se muestra completa, centrada y sin repetición sobre un fondo Navy,
hasta que Diseño entregue el banner panorámico definitivo.

18.0.1.1.3
------------
Sustituye una función de CSS no compatible con el compilador Sass de Odoo por
una regla equivalente, restaurando la compilación de estilos de la portada.

18.0.1.1.4
------------
El encabezado vuelve a renderizar el campo editable `website.logo`, conservando
las dimensiones corporativas para que el logo pueda sustituirse desde el editor
visual del website sin modificar archivos del módulo.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["website", "portal", "website_livechat"],
    "data": [
        "data/website_data.xml",
        "views/website_brand_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "doorandoor_website_brand/static/src/scss/website_brand.scss",
        ],
    },
    "installable": True,
    "application": False,
}
