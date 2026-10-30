{
    "name": "DoorAndDoor Stripe Bank Reconciliation",
    "version": "18.0.1.6.4",
    "category": "Accounting/Accounting",
    "summary": "18.0.1.6.4 - Oculta liquidaciones mientras Stripe permanece inactivo",
    "description": """
DoorAndDoor Stripe Bank Reconciliation
=======================================

Separa el cobro en línea de su liquidación bancaria. Reutiliza el proveedor
Stripe estándar de Odoo Community, descarga payouts y movimientos de saldo,
calcula bruto, comisiones y neto, y propone el movimiento del diario bancario
correspondiente. No modifica el flujo existente de Control de Cobros ni
concilia asientos automáticamente sin revisión.

18.0.1.6.4
------------
Oculta de Facturación el menú Liquidaciones Stripe mientras este método de
pago no se encuentra habilitado, sin eliminar configuración ni historial.

18.0.1.6.2
------------
Elimina la mención a Odoo del aviso mostrado antes de abrir Stripe Checkout y
explica la espera mediante la confirmación de Stripe.

18.0.1.6.1
------------
Añade cintas diagonales y avisos destacados en la factura para los estados
Esperando Stripe, Tarjeta aceptada y Pago rechazado.

18.0.1.6.0
------------
Sustituye en la lista de pagos el estado técnico de los cobros trasladados a
anticipos por Crédito disponible, parcialmente usado o consumido, sin alterar
el ciclo contable interno del pago.

18.0.1.5.0
------------
Traslada el cobro Stripe duplicado a la subcuenta 1200xx del cliente y crea su
Control validado para mostrarlo y consumirlo como Crédito disponible.

18.0.1.4.2
------------
Usa el PaymentIntent como concepto del crédito duplicado para impedir que el
reconocimiento automático de referencias lo reasocie a la factura ya pagada.

18.0.1.4.1
------------
Contabiliza como crédito abierto del cliente un cobro Stripe confirmado cuando
la factura vinculada ya fue pagada, sin conciliarla ni duplicar la venta.

18.0.1.4.0
------------
Muestra en la factura si Stripe espera al cliente/webhook o si ya confirmó el
cobro y falta contabilizarlo. La sesión Checkout queda pendiente desde su alta.

18.0.1.3.1
------------
Evita buscar el diario en el dominio de proveedores porque journal_id no se
almacena en Odoo 18; filtra el proveedor Stripe compatible en memoria.

18.0.1.3.0
------------
Intercepta Crear pago únicamente al seleccionar el diario Stripe y abre una
sesión segura de Stripe Checkout. La factura solo se liquida tras el webhook.

18.0.1.2.4
------------
Conserva el procesamiento estándar de facturas en instancias que todavía no
incluyen el desarrollo PO, sin exigir campos exclusivos de ese flujo.

18.0.1.2.3
------------
Impide reutilizar o modificar un diario bancario genérico ya asignado por
Odoo al proveedor; Stripe siempre crea o reutiliza exclusivamente STRP.

18.0.1.2.2
------------
Añade cobertura automática para impedir que el método Stripe deje de usar
la cuenta transitoria dedicada durante futuras actualizaciones.

18.0.1.2.1
------------
Configura el método de entrada Stripe para contabilizar los cobros en la
cuenta conciliable Stripe - Fondos por liquidar.

18.0.1.2.0
------------
Convierte cada transacción Stripe confirmada de un único PO en pago contable
y Control de Cobro validado, sin intervención humana ni afectar otras vías.

18.0.1.1.1
------------
Respeta la validación estándar de Odoo: prepara el diario y la cuenta sin
activar Tarjeta hasta que el proveedor Stripe pase a modo de prueba.

18.0.1.1.0
------------
Crea de forma controlada el diario Stripe, una cuenta transitoria conciliable,
habilita tarjetas y vincula todo al proveedor como vía de validación inmediata.

18.0.1.0.2
------------
Vincula el proveedor al flujo inmediato del Control de Cobros e impide usar
Stripe con un diario que requiera revisión humana.

18.0.1.0.1
------------
Adapta las restricciones de unicidad a la API ORM disponible en la revisión
local de Odoo 18 Community.

18.0.1.0.0
------------
Versión inicial del sincronizador y de las propuestas de depósito.
    """,
    "depends": ["account", "payment_stripe", "doorandoor_control_cobros"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/payment_provider_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_payment_views.xml",
        "views/account_move_views.xml",
        "views/stripe_settlement_views.xml",
        "views/menu_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
