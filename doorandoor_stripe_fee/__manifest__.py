{
    "name": "DoorAndDoor Pagos con Tarjeta",
    "version": "18.0.3.0.42",
    "category": "Accounting/Accounting",
    "summary": "18.0.3.0.42 - Cotizaciones parciales muestran el saldo pendiente del cliente",
    "description": """
DoorAndDoor Pagos con Tarjeta
=============================

Permite cobrar facturas total o parcialmente mediante tarjeta. El cargo de
procesamiento se refleja únicamente en los totales de la misma factura y se
contabiliza sin añadir un producto o artículo a las líneas comerciales. El
cliente ve exclusivamente "Pago con tarjeta"; Stripe se conserva como detalle
técnico de la integración.

Historial de versiones
----------------------

Version 18.0.3.0.40
---------------------

Recalcula en servidor el importe de Pago total con tarjeta usando el total
final de productos e impuestos al crear y publicar la factura. Evita conservar
un importe anterior al cálculo fiscal y recalcula el cargo de procesamiento
antes de publicar.

Version 18.0.3.0.35
---------------------

Al devolver una factura con cargo técnico de tarjeta a borrador, retira el
importe correspondiente de la cuenta por cobrar antes de validar el asiento.
Evita el descuadre causado por la limpieza estándar de líneas técnicas de Odoo.

Version 18.0.3.0.36
---------------------

Valida el saldo del asiento directamente al finalizar el retorno a borrador,
compatible con el verificador interno de Odoo 18.

Version 18.0.3.0.37
---------------------

Actualiza el importe de tarjeta dentro de la misma operación atómica que el
impuesto y el cargo, evitando validaciones intermedias de un asiento temporal.

Version 18.0.3.0.38
---------------------

Tras recalcular impuestos, deriva la cuenta por cobrar desde el balance real
de las demás líneas, incluso cuando Odoo haya reconstruido temporalmente el
vencimiento sin el cargo técnico de tarjeta.

Version 18.0.3.0.39
---------------------

Actualiza el importe visible del cargo cuando cambia la línea técnica después
de recalcular ciudad, impuesto y total de la factura.

Version 18.0.3.0.34
---------------------

Recalcula el cargo técnico de tarjeta cuando cambia la ciudad fiscal en una
factura borrador, manteniendo alineados impuesto, cargo y total por cobrar.

Version 18.0.3.0.32
---------------------

Reconoce también como primer cobro con tarjeta el pago total cuyo saldo es
exactamente igual al total con fee. Esto permite que Clover lo fuerce y evita
que el asistente caiga en un diario manual.

Version 18.0.3.0.33
---------------------

Declara en ``sale.order`` el porcentaje calculado de cargo por tarjeta usado
por la vista de cotizaciones, permitiendo instalar el módulo desde cero.

Version 18.0.3.0.31
---------------------

Muestra el porcentaje del cargo por tarjeta sin ceros finales en totales de
factura y PDF; por ejemplo, `3 %`, `5 %` o `3,5 %`. El cálculo no cambia.

Version 18.0.3.0.30
---------------------

Muestra el porcentaje configurado junto al cargo por pago con tarjeta en
cotizaciones, facturas, asistente de pago y documento impreso, sin modificar
el cálculo ni los asientos de la operación.

Version 18.0.3.0.29
---------------------

Usa Clover como proveedor preferente de tarjeta cuando está activo, aplicando
el porcentaje y producto de fee configurables. Stripe queda compatible para
flujos históricos o una reactivación futura.

Version 18.0.3.0.28
---------------------

Define ``Pago total`` como valor inicial de las Opciones de pago en cotizaciones,
prefacturas y facturas nuevas. Las selecciones existentes no se modifican.

Version 18.0.3.0.27
---------------------

Imprime el porcentaje e importe de impuestos y el cargo por tarjeta en el
documento de factura.
""",
    "depends": ["doorandoor_stripe_reconciliation", "sale", "doorandoor_sales_new", "doorandoor_tax_state"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_provider_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/report_card_fee.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
