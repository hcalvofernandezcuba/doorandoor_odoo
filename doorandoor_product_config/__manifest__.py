# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Product Config",
    "version": "18.0.1.8.2",
    "category": "Sales",
    "summary": "18.0.1.8.2 - Restringe la configuración de precios de variantes a Ajustes",
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

- `18.0.1.8.0`: cotizaciones, prefacturas y facturas muestran una sola entrada
  por plantilla de producto. La variante tecnica permanece oculta y se asigna
  solamente al confirmar el configurador guiado.

- `18.0.1.7.4`: elimina el bloqueo visual absoluto `no_create` del selector de
  productos. Los administradores pueden crear productos nuevos y Odoo conserva
  el control para los demás usuarios mediante sus permisos de acceso reales.

- `18.0.1.7.3`: carga como dato tecnico las opciones informativas del
  configurador en las vistas de factura, evitando el error Owl al confirmar la
  variante antes de ejecutar el control de stock.

- `18.0.1.7.2`: evita asignar una variante provisional al seleccionar la
  plantilla; el control de stock se ejecuta solamente despues de confirmar la
  variante definitiva en el configurador.

- `18.0.1.7.1`: abre el configurador mediante observacion reactiva del producto
  seleccionado y elimina el guardado previo que demoraba el flujo.

- `18.0.1.7.0`: reemplaza el asistente visual propio de facturas por el
  componente estandar de configuracion usado en Cotizaciones.

- `18.0.1.6.0`: migra todos los productos al modo configurador, lo establece
  para productos nuevos y evita que Ventas vuelva a abrir la matriz de variantes.

- `18.0.1.5.0`: oculta secciones sin opciones, muestra solo el valor en cada
  desplegable y detalla los atributos obligatorios pendientes de seleccionar.

- `18.0.1.4.4`: restaura `layout_mode` como campo tecnico de compatibilidad
  para evitar errores de lectura en sesiones con vistas anteriores cacheadas.

- `18.0.1.4.3`: sustituye la funcion Sass `min()` con unidades incompatibles
  por reglas responsivas equivalentes, corrigiendo los estilos web e impresion.

- `18.0.1.4.2`: declara explicitamente el modelo relacionado del campo
  calculado de valores disponibles para asegurar la inicializacion del registro.

- `18.0.1.0.0`: version inicial del modulo. Se agrega precio adicional
  por variante y aplicacion automatica en `account.move.line` usando el
  precio base del producto plantilla.

- `18.0.1.0.1`: se agrega selector de variantes con icono en las lineas
  de factura y un acceso rapido en el producto para gestionar precios de
  variantes. Esta version permite abrir un formulario emergente desde la
  linea de factura, escoger la variante final y aplicar automaticamente
  el precio configurado.

- `18.0.1.1.0`: el selector permite crear un valor permanente para un
  atributo del producto y genera solamente la combinacion solicitada. Las
  variantes personalizadas conservan factura de origen, precio y referencia;
  se reutilizan aunque esten archivadas y pueden archivarse 30 dias despues
  de su entrega cuando no tienen stock ni documentos abiertos.

- `18.0.1.1.1`: se incorpora en `Docs` la guia operativa y tecnica para
  configurar, vender, corregir, archivar y reactivar productos con variantes.

- `18.0.1.2.0`: se sustituye el desplegable de variantes por el wizard
  `Armar producto`, con seleccion por atributos, opciones acumulables, vista
  previa de precio y creacion o reactivacion de la combinacion resultante.

- `18.0.1.2.1`: la linea de factura muestra un selector de plantillas con una
  entrada por producto y mantiene la variante tecnica oculta hasta resolverla
  mediante `Armar producto`.

- `18.0.1.2.2`: evita exponer variantes archivadas en el campo de vista previa
  del wizard y las reactiva de forma controlada al pulsar `Aplicar`, corrigiendo
  el `KeyError` del cliente web.

- `18.0.1.2.3`: la variante resultante se presenta como texto y no como
  registro Many2one, evitando que `web_read` intente resolver IDs archivados o
  restringidos antes de ejecutar `Aplicar`.

- `18.0.1.2.4`: el wizard ignora la variante provisional de la linea y abre
  todas las opciones sin marcar para que el vendedor arme explícitamente el
  producto.

- `18.0.1.3.0`: el selector de plantilla guarda automáticamente la prefactura
  y su linea, localiza la linea persistida mediante un token y abre `Armar
  producto` sin exigir un guardado manual.

- `18.0.1.3.1`: `Armar producto` permite alternar entre tarjetas visuales y
  tabla compacta sin perder las opciones seleccionadas.

- `18.0.1.4.0`: se reemplazan las vistas experimentales por la presentacion
  definitiva inspirada en `Configure su producto` de Ventas, con imagen,
  opciones múltiples, desplegables por atributo, cantidad, precio y total.

- `18.0.1.4.1`: `available_template_value_ids` pasa de related incompatible a
  Many2many calculado, corrigiendo el error de arranque del registro de Odoo.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": [
        "account",
        "product",
        "sale_product_matrix",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/custom_variant_cron.xml",
        "views/product_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/ddpc_variant_selector_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_product_config/static/src/js/product_template_autosave_field.js",
            "doorandoor_product_config/static/src/scss/variant_configurator.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
