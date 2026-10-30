{
    "name": "DoorAndDoor Legacy Delivery OCR",
    "version": "18.0.1.4.0",
    "category": "Operations/Inventory",
    "summary": "Históricos consumen stock existente o se excluyen sin duplicar inventario",
    "description": """
DoorAndDoor Legacy Delivery OCR
===============================

Version 18.0.1.4.0
-------------------

* Obliga a clasificar el tratamiento logístico antes de aprobar cada OCR.
* Usa por defecto stock y labels existentes de Odoo, sin crear una recepción
  ficticia ni códigos nuevos.
* Permite excluir de forma auditada facturas ya controladas en el sistema
  anterior y conserva la regularización como excepción documentada.

Version 18.0.1.3.5
-------------------

* Unifica Zoho y QuickBooks en una recepción inicial obligatoria.
* La aprobación prepara la recepción; no crea anticipadamente una entrega.

Version 18.0.1.3.4
-------------------

* Impide que una coincidencia solo por nombre asocie una puerta o ventana con
  medidas, mano, color o cristal diferentes.
* Mantiene la línea bajo revisión hasta seleccionar o crear el ITEM exacto.

Version 18.0.1.3.3
-------------------

* Reconoce QuickBooks cuando el método de pago aparece en la misma línea que
  el número de factura.
* Extrae productos con cantidad explícita aunque la impresión omita precios e
  importes; nunca usa el número de renglón como cantidad.

Importa por lotes facturas PDF procedentes del sistema anterior, extrae sus
datos mediante texto PDF u OCR y prepara entregas históricas auditadas. No crea
facturas contables. Cada documento conserva su PDF, huella SHA-256, texto
extraído, coincidencias de ITEM y aprobador. Solo Supervisores de importación
histórica o Administrador/Ajustes pueden liberar la operación de almacén.
Detecta automáticamente facturas de Zoho o QuickBooks, incluso exportaciones
con texto superpuesto del panel, y normaliza sus encabezados, pagos y productos
al mismo modelo histórico revisable.
Las asociaciones confirmadas entre nombres anteriores y variantes actuales se
conservan por compañía y firma de atributos para proponer el ITEM en futuras
facturas, manteniendo revisión humana antes de crear operaciones logísticas.
Una equivalencia automática se limita a 60 por ciento de confianza y exige la
confirmación expresa del operador antes de enviar el documento a aprobación.

Version 18.0.1.3.2
-------------------

* Permite crear por nombre un producto especial histórico almacenable y
  serializado mediante labels DoorAndDoor, sin duplicar el seguimiento nativo,
  exigir configuración fabril ni generar una orden de producción durante la
  reconstrucción documental.
* Al aprobar el OCR inicia, cuando está disponible, la cadena histórica
  completa: recepción y labels en origen, traslado y recepción destino si los
  almacenes difieren, y entrega final, conservando los controles Hanger.
* Mantiene fuera de este ciclo el faltante real de fabricación, que se
  clasificará posteriormente y originará órdenes de producción individuales.
""",
    "author": "DoorAndDoor",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "stock",
        "doorandoor_process_control",
        "doorandoor_product_config",
        "doorandoor_special_products",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/cron.xml",
        "views/legacy_delivery_ocr_views.xml",
        "wizard/historical_special_product_wizard_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
