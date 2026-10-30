{
    "name": "DoorAndDoor Initial Inventory Load Report",
    "version": "18.0.1.0.2",
    "category": "Inventory/Inventory",
    "summary": "18.0.1.0.2 - Terminologia gerencial clara y PDF de los movimientos seleccionados en el orden de la vista",
    "author": "Hanoi Calvo",
    "license": "LGPL-3",
    "depends": ["doorandoor_inventory_variant_count"],
    "data": [
        "security/ir.model.access.csv",
        "security/initial_load_report_security.xml",
        "views/initial_load_report_views.xml",
        "reports/initial_load_report_templates.xml",
    ],
    "installable": True,
}
