{
    "name": "DoorAndDoor External Manufacturing",
    "version": "18.0.1.0.0",
    "category": "Purchases/Sales",
    "summary": "18.0.1.0.0 - Compra bajo pedido y rutas logísticas para fabricación externa",
    "description": """
18.0.1.0.0
------------
Clasifica cada plantilla por ruta de abastecimiento y modalidad logística,
hereda esos valores en los productos especiales, crea pedidos externos desde
la cotización y genera órdenes de compra vinculadas únicamente después de
comprobar políticas, pago mínimo, margen y aprobación gerencial. Conserva el
origen de venta en las líneas de compra y ofrece un tablero de seguimiento.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "purchase_stock",
        "doorandoor_special_products",
        "doorandoor_policy_acceptance",
        "doorandoor_purchase_fixed_warehouse",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/external_order_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
