{
    "name": "DoorAndDoor Website Catalog",
    "version": "18.0.2.1.3",
    "category": "Website",
    "summary": "18.0.2.1.3 - Recupera la página Galería y enlaza su bloque de Inicio",
    "description": """
Catálogo público administrable para presentar puertas, ventanas y soluciones
fabricadas bajo pedido. Permite organizar artículos por categorías, publicar
fotografías, descripciones y especificaciones, y dirigir cada oportunidad a
una solicitud de cotización sin habilitar precios ni carrito electrónico.

18.0.1.0.1 corrige la construcción del enlace dinámico de cotización en la
ficha pública de cada artículo.

18.0.1.0.2 coloca Catálogo como segundo acceso de la navegación y retira
Eventos del menú público sin desinstalar la aplicación ni borrar eventos.

18.0.1.0.3 aplica el orden tanto al menú predeterminado como al menú activo
creado por el tema visual del website.

18.0.2.1.0 sustituye las listas extensas de atributos por un configurador
progresivo que solo permite combinaciones correspondientes a variantes activas.

18.0.2.1.1 compacta los datos enviados al navegador para productos con miles
de variantes, conservando el filtrado progresivo y la variante seleccionada.

18.0.2.1.2 restaura los accesos históricos de Galería hacia la tienda nativa
sin mezclar sus productos, imágenes y variantes con el catálogo editorial.

18.0.2.1.3 recupera la galería histórica como página independiente en
/galeria y enlaza correctamente las imágenes y el botón del bloque de Inicio.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["website", "mail", "doorandoor_website_brand"],
    "data": [
        "security/catalog_security.xml",
        "security/ir.model.access.csv",
        "data/catalog_categories.xml",
        "views/catalog_backend_views.xml",
        "views/catalog_templates.xml",
        "data/website_menu.xml",
        "data/website_menu_adjustments.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "doorandoor_website_catalog/static/src/scss/catalog.scss",
            "doorandoor_website_catalog/static/src/js/catalog_configurator.js",
        ],
    },
    "installable": True,
    "application": False,
}
