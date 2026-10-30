# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Commercial Offices and Tax",
    "version": "18.0.1.5.1",
    "category": "Accounting",
    "summary": "18.0.1.5.1 - Evita solapamientos en la cabecera PDF de ventas y facturas",
    "description": """
DoorAndDoor Commercial Offices and Tax
======================================

Una sola compañía puede operar varias oficinas comerciales. Cada vendedor se
asocia a una oficina y cada oficina define su dirección, teléfono y tasa de
venta. La oficina se copia y conserva en cotizaciones y facturas para aplicar
el impuesto correspondiente y mantener trazabilidad documental.

18.0.1.5.1 retira el bloque duplicado del comercial de la cabecera fija de
cotizaciones y facturas. El comercial y su teléfono permanecen en la sección
de firma del documento, sin invadir las líneas de productos al imprimir PDF.

18.0.1.5.0 impide a los comerciales cambiar el almacén comercial, de entrega
o proveedor de las líneas. Todas las ventas quedan ligadas al almacén operativo
de la oficina del vendedor; los procesos logísticos posteriores conservan sus
traslados internos independientes.

18.0.1.4.1 muestra junto al comercial su teléfono configurado en cotizaciones,
prefacturas y facturas. Si no tiene teléfono propio usa el de su oficina
asignada, sin sustituirlo por el teléfono general de otra sucursal.

18.0.1.4.0 vincula cada oficina con un almacén operativo y lo propaga a la
venta interna y al almacén de entrega. Las necesidades de fabricación,
entregas y Pickup Orders conservan así la oficina de origen y no caen en el
primer almacén configurado de la compañía.

18.0.1.3.0 sincroniza la regla fiscal desde la oficina comercial y muestra su
dirección y teléfono en cotizaciones, prefacturas y facturas.
""",
    "author": "Hanoi Calvo Fernández -- DoorAndDoor",
    "license": "LGPL-3",
    "depends": ["sale_management", "account", "doorandoor_tax_state", "doorandoor_sales_new"],
    "data": [
        "security/ir.model.access.csv",
        "views/commercial_office_views.xml",
        "views/res_users_views.xml",
        "views/sale_account_views.xml",
        "views/report_office_invoice.xml",
    ],
    "installable": True,
    "application": False,
}
