{
    "name": "DoorAndDoor Clover Ecommerce",
    "version": "18.0.1.7.2",
    "category": "Accounting/Payment Providers",
    "summary": "18.0.1.7.2 - Concilia la factura antes de validar el control Clover",
    "author": "Hanoi Calvo Fernández -- DoorAndDoor",
    "website": "https://www.doorandoor.com",
    "description": """
DoorAndDoor Clover Ecommerce
=============================

Integra los cobros con tarjeta de Clover Ecommerce en el mismo ciclo operativo
de facturas, pagos parciales y Control de Cobros usado para tarjeta. Mientras
no existan credenciales, ofrece un simulador exclusivamente local que nunca
captura ni transmite datos de tarjeta. La integración real utiliza el iframe
alojado por Clover y recibe únicamente referencias tokenizadas.

Historial de versiones
----------------------

Version 18.0.1.7.2
------------------

Evita que Control de Cobros consuma anticipadamente la contrapartida por
cobrar contra el asiento interno Clover. La transacción aplica primero el
saldo comercial a la factura y conserva separado el ingreso por el cargo.

Version 18.0.1.7.1
------------------

En una liquidación Clover posterior a pagos por Zelle, efectivo o cheque,
separa el saldo pendiente, el cargo de procesamiento configurado y el total
cobrado. Liquida únicamente el saldo de la factura y registra el cargo en su
cuenta de ingresos, sin modificar ni recargar los pagos anteriores.

Version 18.0.1.7.0
------------------

Completa el simulador exclusivamente local con validación de titular, envío de
OTP por Telegram, comprobación del código y aprobación simulada antes de crear
el pago Odoo. Nunca transmite datos de tarjeta ni usa credenciales productivas.

Version 18.0.1.6.14
-------------------

Permite que cada comercial cree y actualice exclusivamente sus propias
operaciones Clover durante la validación del titular y del OTP. Administración
mantiene visibilidad global y nadie recibe acceso a la configuración sensible
del proveedor de pago.

Version 18.0.1.6.13
-------------------

Evita exponer el registro administrativo de `payment.provider` en el asistente
de pago. El comercial conserva acceso al flujo operativo de Clover mediante un
identificador técnico y las lecturas sensibles se ejecutan de forma controlada,
sin concederle permisos de Administración/Ajustes.

Version 18.0.1.6.11
-------------------

Conserva cada correo OTP en la cola de Odoo, enlazado a su operación Clover y
con estado de envío o fallo verificable. Ya no se elimina automáticamente tras
la entrega SMTP.

Version 18.0.1.6.10
-------------------

Corrige el contexto real del botón Pagar de Odoo, que abre el asistente desde
las líneas por cobrar. La factura de tarjeta ahora se identifica correctamente
y el diálogo inicia de forma obligatoria con Clover, no con Zelle.

Version 18.0.1.6.9
------------------

Cuando una factura está preparada para tarjeta, el asistente de pago inicia
visiblemente con el diario y la línea online de Clover, en vez del primer
diario manual disponible.

Version 18.0.1.6.8
------------------

Corrige el orden de alta del primer proveedor Clover: asocia primero el
método Tarjeta y después lo activa, respetando la validación estándar de Odoo.

Version 18.0.1.6.7
------------------

Mantiene en solo lectura el diario y la línea de pago mientras el primer
cobro de una factura está comprometido con Clover. La protección de servidor
de la versión anterior continúa siendo la autoridad ante cualquier alteración
de la interfaz.

Version 18.0.1.6.6
------------------

Cuando una factura tiene Clover seleccionado para su primer cobro, fuerza en
servidor el diario, la línea online y el importe de Clover. Impide registrar
efectivo, transferencia u otro método manual con el cargo de tarjeta aplicado.
Tras completar un pago parcial, el saldo restante conserva la elección de un
método de pago diferente.

Version 18.0.1.6.5
------------------

Añade una vista final independiente para mantener el importe Clover en solo
lectura aunque existan personalizaciones previas del asistente de pago.

Version 18.0.1.6.4
------------------

Bloquea visual y funcionalmente el importe del asistente Clover: el cobro se
calcula exclusivamente desde el saldo de la factura, incluyendo el importe
planificado por el cargo de tarjeta cuando corresponda. También fuerza la
línea online del proveedor Clover al crear el pago aprobado, evitando que una
línea manual homónima deje la factura en proceso sin asiento ni conciliación.

Version 18.0.1.6.0
------------------

Garantiza que cada proveedor Clover tenga el método online estándar Tarjeta,
evitando listas vacías en la vista previa de facturas. Prepara el acceso de
portal para reutilizar el control antifraude de titular y OTP antes del
checkout seguro de Clover.

Version 18.0.1.6.1
------------------

Evita que archivar Stripe deje inactivo el método online compartido Tarjeta
mientras Clover esté habilitado; Stripe permanece desactivado y Clover sigue
disponible para el portal.

Version 18.0.1.6.2
------------------

Selecciona explícitamente la línea online Clover al iniciar un pago desde el
portal, evitando que Odoo elija la línea manual del mismo diario.

Version 18.0.1.6.3
------------------

Permite que el portal respete el canal OTP configurado para Clover. En
Pruebas puede usarse Telegram para validadores internos; Local y Gestión
conservan el canal que tengan configurado de forma independiente.

Version 18.0.1.5.5
------------------

Permite configurar una lista exclusiva de chats internos para que el mismo OTP
de Clover llegue a los validadores de Pruebas, sin alterar Crédito, secretos,
ni el canal de Gestión. Conserva la compatibilidad local con el chat único
previamente configurado.

Version 18.0.1.5.0
------------------

Permite seleccionar mediante parámetro local la entrega del OTP Clover por el
bot interno de Telegram ya usado por crédito autorizado. No replica secretos,
mantiene trazabilidad del canal y no altera la configuración de Pruebas ni de
Gestión.

Version 18.0.1.5.1
------------------

Muestra en el checkout el titular validado antes del OTP como dato de solo
lectura y elimina su edición posterior; Clover solo solicita número, fecha,
CVC y código postal.

Version 18.0.1.5.2
------------------

Conserva visible el titular autorizado por Odoo y habilita también el campo
``CARD_NAME`` del iframe Clover para que el vendedor ingrese ese mismo nombre
cuando el procesador no pueda autocompletarlo.

Version 18.0.1.5.3
------------------

Mantiene visible el titular auditado por Odoo y elimina el segundo ingreso en
el iframe Clover; tras OTP el vendedor solo captura los datos de tarjeta.

Version 18.0.1.5.4
------------------

Registra en el log técnico únicamente el diagnóstico seguro de Clover ante un
rechazo, sin incluir datos de tarjeta ni tokens, para diferenciar causas de
Sandbox y configuración.

Version 18.0.1.4.4
------------------

Evita páginas técnicas ante incidencias durante la validación del OTP y ofrece
al comercial mensajes claros: código incorrecto, vencido o usado; reenvío
seguro del código; o continuación directa cuando ya fue validado.

Version 18.0.1.4.5
------------------

Captura la indisponibilidad SMTP durante el envío OTP, conserva el control de
titular y muestra al comercial una acción segura: configurar correo y solicitar
un código nuevo, sin OTP activo ni página técnica.

Version 18.0.1.4.3
------------------

Cancela el OTP activo y muestra un error claro cuando el servidor SMTP no logra
entregar el código, evitando que el flujo indique una autorización inexistente.

Version 18.0.1.4.2
------------------

Monta el elemento oficial ``CARD_NAME`` de Clover dentro del iframe seguro,
para que el formulario del procesador solicite también el titular de tarjeta.

Version 18.0.1.4.1
------------------

Exige el titular declarado de la tarjeta antes del OTP y lo compara con el
cliente, su empresa comercial y sus contactos asociados. Una diferencia
bloquea el cobro antes de enviar el formulario Clover.

Version 18.0.1.4.0
------------------

Añade autorización antifraude por OTP enviado al correo del cliente antes de
mostrar el formulario Clover: código de un uso, diez minutos de vigencia y
tres intentos máximos, con trazabilidad en la operación.

Version 18.0.1.3.5
------------------

Presenta el rechazo de tarjeta en una alerta roja, con el texto claro
``Tarjeta rechazada. No se realizó ningún cargo.``, incluso si Clover devuelve
su código HTTP técnico al tokenizar o cobrar.

Version 18.0.1.3.4
------------------

Convierte el rechazo HTTP 402 de Clover en un mensaje operativo claro que
confirma que no se realizó ningún cargo, sin exponer el código técnico al
vendedor.

Version 18.0.1.3.3
------------------

Adapta el POST tokenizado de Clover al checkout privado: autentica la sesión y
valida que la operación pertenezca al usuario antes de cobrar, sin depender del
token CSRF de un layout público inexistente.

Version 18.0.1.3.2
------------------

Versiona los recursos CSS y JavaScript del checkout para impedir que el
navegador reutilice el script anterior sin token CSRF.

Version 18.0.1.3.1
------------------

Incluye el token CSRF de la sesión en el POST del formulario Clover autónomo,
evitando que Odoo rechace el cobro antes de llamar a la API.

Version 18.0.1.3.0
------------------

Establece la altura segura de los iframes de Clover y estilos propios del
checkout para mostrar todos los campos sin depender de los assets del website.

Version 18.0.1.2.9
------------------

Reemplaza la plantilla pública por una página autónoma para el checkout
privado de Clover, eliminando el error 500 por falta de contexto website.

Version 18.0.1.2.8
------------------

Protege toda creación de operación Clover frente a extensiones del asistente
de pago: genera la clave de idempotencia ausente y establece el estado
pendiente antes de persistirla.

Version 18.0.1.2.7
------------------

Usa el icono PNG RGBA oficial de los módulos DoorAndDoor en las tarjetas,
manteniendo su transparencia y sin añadir ningún fondo.

Version 18.0.1.2.6
------------------

Normaliza las tarjetas de capacitación a la proporción física estándar y
elimina el excedente horizontal, conservando el wordmark transparente.

Version 18.0.1.2.5
------------------

Reemplaza la placa blanca del logo por el wordmark corporativo transparente,
igual al recurso utilizado por los demás módulos DoorAndDoor.

Version 18.0.1.2.4
------------------

Corrige el área visual del logotipo corporativo en las tarjetas de
capacitación para asegurar contraste, escala y presentación consistente.

Version 18.0.1.2.3
------------------

Incorpora el logotipo corporativo de DoorAndDoor en las tarjetas internas de
capacitación Clover, conservando el diseño y los escenarios de prueba.

Version 18.0.1.2.2
------------------

Refina las tarjetas internas de capacitación Clover para el uso exclusivo del
equipo en desarrollo, sin alterar los datos de prueba ni el flujo de cobro.

Version 18.0.1.2.1
------------------

Incluye tarjetas visuales de capacitación con titular, vencimiento y CVC de
prueba explícitos para reproducir los escenarios aprobado y rechazado en
Clover Sandbox.

Version 18.0.1.2.0
------------------

Integra el checkout seguro de Clover mediante iframe, tokeniza la tarjeta en
el navegador y envía al servidor únicamente un token. El cargo se realiza con
API idempotente, queda registrado como operación auditable y se acompaña de la
guía de configuración y pruebas de sandbox.

Version 18.0.1.1.1
------------------

Corrige la persistencia del identificador del wizard temporal para evitar una
relación prohibida entre la operación persistente y un TransientModel de Odoo.

Version 18.0.1.1.0
------------------

Añade la primera operación Clover y sus vistas de configuración, simulación y
seguimiento del cobro.

Version 18.0.1.0.0
------------------

Versión inicial del proveedor Clover Ecommerce, diario y validaciones de
credenciales.
    """,
    "depends": ["account", "payment", "account_payment", "doorandoor_stripe_fee"],
    "data": [
        "security/clover_security.xml",
        "security/ir.model.access.csv",
        "data/payment_provider_data.xml",
        "views/payment_provider_views.xml",
        "views/account_payment_register_views.xml",
        "views/clover_amount_guard_views.xml",
        "views/clover_checkout_wizard_views.xml",
        "views/clover_operation_views.xml",
        "views/clover_checkout_templates.xml",
        "views/portal_clover_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "doorandoor_clover_payment/static/src/css/clover_checkout.css",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
