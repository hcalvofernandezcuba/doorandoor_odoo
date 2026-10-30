{
    "name": "Zoho Books Import (Unidirectional)",
    "version": "18.0.1.2.13",
    "category": "Accounting",
    "summary": "Restringe menús e importaciones de Zoho al grupo administrativo específico",
    "description": """
        Unidirectional Zoho Books to Odoo Connector
        ===========================================
        Import only - No export functionality:
        - Products & Stock
        - Customers & Vendors
        - Sale Orders
        - Invoices & Vendor Bills
        - Payments
        - Credit Notes
        
        Features:
        - OAuth2 Authentication
        - Incremental sync support
        - Detailed import logs
        - Background jobs via cron
    """,
    "author": "Hanoi Calvo Fernández (doorandoor)",
    "website": "https://github.com/hanoicuba",
    "depends": [
        "base",
        "mail",
        "product",
        "sale",
        "account",
        "stock",
        "uom",
    ],
    "data": [
        "data/category.xml",
        "security/zoho_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/zoho_connector_views.xml",
        "views/zoho_auth_templates.xml",
        "views/zoho_import_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
}   
