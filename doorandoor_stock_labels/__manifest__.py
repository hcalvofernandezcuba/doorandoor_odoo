# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Stock Labels",
    "version": "18.0.1.0.33",
    "category": "Inventory",
    "summary": "18.0.1.0.33 - Preserva lotes en recibir con hanger y bloquea seriales",
    "description": """
DoorAndDoor Stock Labels
========================

Este modulo agrega una primera version de etiquetas para recepcion de
inventario en DoorAndDoor.

Objetivos funcionales
---------------------

- Configurar en el producto si imprime etiqueta al recibir.
- Definir si la etiqueta usa codigo interno o codigo de barras.
- Imprimir etiquetas desde recepciones de inventario.
- Generar etiquetas por numero de serie o, si no existe seguimiento
  individual, por cantidad recibida.
- Incluir QR con URL navegable al registro del producto en Odoo para
  escaneo desde moviles.
- Incluir Code128 para lectura por hand scanners / hangers.

Alcance inicial
---------------

- Se apoya en el tracking estandar de Odoo.
- No fuerza la generacion automatica de seriales; usa los ya registrados
  en la recepcion.
- Si el producto no usa seriales o lotes, permite imprimir etiquetas por
  cantidad recibida.

Historial resumido
------------------

- 18.0.1.0.24
  Continúa el autoserie diario por producto y actualiza manuales de uso y pruebas.

- 18.0.1.0.25
  Amplia la impresion de labels para emitir una etiqueta por lote completo en productos con tracking por lote y agrega un modo de impresion por codigo de producto para preparar etiquetas uniformes destinadas a proveedores.

- 18.0.1.0.26
  Agrega el wizard `Recibir con hanger` para pruebas completas del flujo de recepcion, abriendolo desde `Comprobar disponibilidad` en recepciones entrantes y permitiendo contar una unidad por cada disparo escaneado.

- 18.0.1.0.27
  Ajusta la visibilidad del boton `Recibir con hanger` para mostrarlo siempre en recepciones entrantes, sin depender del estado operativo visible en esta base Odoo 18 CE.

- 18.0.1.0.28
  Extiende el asistente de registro previo para soportar tanto productos con tracking por lote como por serial, evitando que `Print Labels` siga bloqueando productos por lote por falta de un tracking cargado en la recepcion.

- 18.0.1.0.29
  Ajusta la edicion del campo `Lot / Serial Number` en el wizard de registro previo para que el usuario pueda capturar el numero de lote o serial directamente en la grilla de Odoo 18 CE.

- 18.0.1.0.30
  Corrige la carga de lineas en los wizards de recepcion usando `move_ids` en lugar de `move_ids_without_package`, de modo que los productos esperados se muestren correctamente en esta base Odoo 18 CE.

- 18.0.1.0.32
  Corrige el flujo de `Recibir con hanger` creando el wizard ya poblado desde servidor, evitando que la UI abra registros transitorios con lineas vacias y permitiendo reconocer correctamente referencias como `DTP-00080`.

- 18.0.1.0.33
  Ajusta `Recibir con hanger` para preservar el lote ya registrado en productos con tracking por lote y bloquear con mensaje claro los productos con tracking por serie hasta que se registren sus seriales reales.

    """,
    "author": "Hanoi Calvo Fernandez for Doorandoor",
    "website": "https://gestion.doorandoor.com",
    "depends": [
        "stock",
        "product",
        "doorandoor_product_config",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/stock_serial_wizard_views.xml",
        "wizard/stock_label_wizard_views.xml",
        "wizard/stock_receipt_scan_wizard_views.xml",
        "views/product_views.xml",
        "views/stock_picking_views.xml",
        "report/stock_label_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
