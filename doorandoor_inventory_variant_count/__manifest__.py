{
    "name": "Inventory Count by Variant and Items",
    "version": "18.0.1.9.2",
    "category": "Inventory/Inventory",
    "summary": "18.0.1.9.2 - Labels verticales Zebra 4x6, uno por hoja completa",
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["stock", "barcodes", "mail", "doorandoor_stock_labels"],
    "data": [
        "security/inventory_count_security.xml",
        "security/ir.model.access.csv",
        "data/inventory_count_sequence.xml",
        "views/product_count_item_views.xml",
        "views/product_barcode_views.xml",
        "wizard/product_label_wizard_views.xml",
        "views/inventory_count_session_views.xml",
        "report/product_item_label_report.xml",
        "views/inventory_count_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_inventory_variant_count/static/src/scss/inventory_count.scss",
        ],
    },
    "application": True,
    "installable": True,
}
