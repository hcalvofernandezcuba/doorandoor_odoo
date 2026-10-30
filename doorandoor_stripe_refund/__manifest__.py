{
    "name": "DoorAndDoor Stripe Refund",
    "version": "18.0.1.4.0",
    "category": "Accounting/Accounting",
    "summary": "18.0.1.4.0 - Sincroniza devoluciones con cantidades netas y bloquea entregas",
    "description": """
DoorAndDoor Stripe Refund
=========================

18.0.1.4.0
------------
Conserva factura y venta publicadas como documentos históricos, muestra las
cantidades devueltas y netas en la factura, recalcula fulfillment y documentos
abiertos, y bloquea entregas mientras la devolución o su sincronización estén
pendientes.

18.0.1.3.0
------------
Crea o reutiliza el canal Administrators durante la instalación, incorpora sus
responsables y publica mensajes separados para solicitud, aprobación y resultado.

18.0.1.2.2
------------
Elimina Otra causa para que Ventas solo utilice causas mandatorias aprobadas y
adapta la unicidad del código a la API ORM disponible en Odoo 18 Community.

18.0.1.2.1
------------
Ubica Causas de devoluciones bajo Control de Cobros / Configuración y limita
su creación, edición y archivo a usuarios con permisos de Ajustes del sistema.

18.0.1.2.0
------------
Sustituye el motivo principal libre por un selector de causas configurable,
carga causas corporativas iniciales y exige detalle en las que lo requieren.

18.0.1.1.1
------------
Aplica colores consistentes a los estados en la lista y a las cintas del
formulario: gris, amarillo, azul, verde y rojo según el avance o resultado.

18.0.1.1.0
------------
Notifica solicitudes y resultados en el canal Administrators y crea actividades
de autorización para administradores del sistema y Control de Cobros.

18.0.1.0.3
------------
Impide que Ventas cambie por API el estado, los documentos o las cantidades de
una solicitud enviada y limita la lectura de líneas a solicitudes propias.

18.0.1.0.2
------------
Envía cada reembolso Stripe con una clave idempotente asociada a la solicitud
para impedir duplicados ante reintentos y corrige el mensaje de auditoría que
se publica en la factura después de la autorización.

18.0.1.0.1
------------
Corrige el formato de los mensajes de validación al bloquear cantidades que
superan lo facturado o importes distintos a la nota de crédito.

18.0.1.0.0
------------
Incorpora un flujo basado exclusivamente en facturas para que Ventas solicite
la devolución de cantidades no entregables y Control de Cobros la rechace o
autorice. Al autorizar genera la nota de crédito parcial, solicita el reembolso
contra el PaymentIntent original y enlaza la transacción y el pago de salida.
No depende ni modifica el flujo PO.
    """,
    "depends": [
        "account",
        "mail",
        "payment_stripe",
        "doorandoor_control_cobros",
        "doorandoor_stripe_reconciliation",
        "doorandoor_sales_new",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/refund_security.xml",
        "data/ir_sequence.xml",
        "data/refund_reason_data.xml",
        "views/refund_reason_views.xml",
        "views/stripe_refund_request_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
    ],
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
