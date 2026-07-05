# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Product Config",
    "version": "18.0.1.0.1",
    "category": "Sales",
    "summary": "Precio adicional por variante aplicado automaticamente en factura",
    "description": """
DoorAndDoor Product Config
==========================

Objetivo
--------

Este modulo extiende la logica comercial de DoorAndDoor para manejar un
precio adicional por variante de producto y aplicarlo automaticamente en
las lineas de factura de cliente.

La idea funcional de esta primera version es simple.
El producto plantilla mantiene su precio base de venta.
Cada variante puede tener un valor adicional propio.
Al seleccionar la variante en la factura el sistema suma precio base mas
adicional de variante.
Ese resultado se guarda en `price_unit`.
Desde ahi Odoo continua con sus calculos normales de subtotal,
impuestos, descuentos y procesos posteriores.

Alcance funcional
-----------------

- Se agrega un campo `ddpc_variant_extra_price` en `product.product`.
- El usuario puede editarlo desde la vista heredada del producto.
- El valor representa un adicional sobre el precio base del producto.
- Al seleccionar una variante en `account.move.line`, el sistema toma
  `product_tmpl_id.list_price`, suma el adicional y actualiza
  automaticamente `price_unit`.
- La factura muestra precio base, adicional de variante y precio
  configurado final.
- Al trabajar sobre `price_unit`, el modulo respeta el comportamiento
  estandar de Odoo para importes e impuestos y favorece la compatibilidad
  con modulos internos que ya consumen ese precio unitario.

Decision de diseno en esta version
----------------------------------

Esta primera entrega implementa una sola seleccion de variante por linea
de factura. No resuelve todavia el escenario mas complejo donde una misma
linea de producto acumula varias selecciones configurables simultaneas.

Se adopta este enfoque porque reduce complejidad tecnica inicial,
permite validar rapidamente el comportamiento con el cliente y deja una
base limpia para decidir si despues hace falta evolucionar hacia
multiples adicionales por linea.

Uso esperado
------------

- Crear o editar un producto con atributos y variantes.
- Definir el precio base del producto en la plantilla.
- Abrir cada variante y colocar su `Variant Extra Price`.
- Crear una factura de cliente.
- Seleccionar la variante en la linea.
- Verificar que `price_unit` se calcule como precio base mas adicional
  de variante.

Notas operativas
----------------

- El modulo aplica su logica sobre facturas de cliente y notas de credito
  de cliente.
- Si la variante no tiene adicional definido, la linea usa solo el precio
  base del producto.
- Esta version prioriza validacion funcional. Si el negocio confirma luego
  un esquema mas complejo, el siguiente paso natural seria agregar
  multiples configuraciones por linea con suma acumulada.

Estructura tecnica
------------------

- `models/product_product.py`: campo adicional por variante.
- `models/account_move_line.py`: logica de calculo automatico y campos
  informativos.
- `views/product_views.xml`: vista heredada para editar el adicional de
  variante.
- `views/account_move_views.xml`: vista heredada de factura para mostrar
  el calculo aplicado.
- `tests/test_variant_price_invoice.py`: pruebas del calculo base y del
  fallback sin adicional.

Control de versiones
--------------------

- `18.0.1.0.0`: version inicial del modulo. Se agrega precio adicional
  por variante y aplicacion automatica en `account.move.line` usando el
  precio base del producto plantilla.

- `18.0.1.0.1`: se agrega selector de variantes con icono en las lineas
  de factura y un acceso rapido en el producto para gestionar precios de
  variantes. Esta version permite abrir un formulario emergente desde la
  linea de factura, escoger la variante final y aplicar automaticamente
  el precio configurado.
    """,
    "author": "Hanoi Calvo Fernandez (doorandoor)",
    "website": "https://doorandoor.com",
    "depends": [
        "account",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "views/account_move_views.xml",
        "views/ddpc_variant_selector_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
