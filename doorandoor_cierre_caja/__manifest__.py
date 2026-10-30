{
    "name": "DoorAndDoor Cierre Diario de Caja",
    "version": "18.0.4.3.2",
    "category": "Accounting",
    "summary": "18.0.4.3.2 - Separa el cobro efectivo de la liberación logística posterior",
    "description": """
DoorAndDoor Cierre Diario de Caja
=================================

18.0.4.3.2
------------
Finaliza primero el pago, el movimiento de denominaciones y el recibo del
cobro en efectivo. Evita que los hooks de conciliación intenten crear o liberar
una entrega dentro de la misma transacción y reviertan el cobro por una regla
logística; la entrega continúa como una operación posterior e independiente.

18.0.4.3.1
------------
Permite que un vendedor envíe una solicitud de efectivo a la caja de su
ciudad sin necesitar acceso directo a la configuración de la caja. La lectura
técnica se limita a localizar y notificar a cajeros y responsables asignados.

18.0.4.3.0
------------
Unifica el cobro en efectivo con la cola de caja: el pago directo deja de
ofrecer diarios de efectivo, los operadores asignados pueden abrir Cobros
pendientes y las facturas con plan parcial cobran automáticamente el importe
faltante para alcanzar el 50% del subtotal más todos los impuestos.

18.0.4.2.3
------------
Permite que el operador complete un cobro en efectivo comprobando internamente
si existe un arqueo bloqueante, sin concederle lectura directa ni permisos de
responsable sobre las auditorías sorpresa de caja.

18.0.4.2.2
------------
En cobros efectivos resuelve la caja desde la solicitud enviada a caja. Evita
que un diario de efectivo compartido entre oficinas seleccione una caja ajena
y permite enlazar correctamente la sesión abierta de la oficina solicitada.

Controla la apertura de caja con fondo para cambio, el arqueo por
denominación, las ventas cobradas en efectivo y el cierre diario. El cierre
solo se confirma si el efectivo contado coincide con el esperado; conserva el
detalle de billetes y genera el reporte diario y la planilla de depósito.

No crea depósitos bancarios ni modifica asientos automáticamente: Contabilidad
recibe evidencia verificable y decide la contabilización y conciliación.

18.0.4.2.1
------------
Permite que los vendedores abran el asistente de pago para Zelle, Clover,
transferencia, cheque y demás métodos comerciales mediante lecturas técnicas
de configuración. No les concede acceso a cajas, sesiones, arqueos ni cierres;
el efectivo continúa por el flujo separado Enviar a caja.

18.0.4.2.0
------------
Añade al reporte diario el número e importe de cobros por Efectivo, Clover,
Zelle, transferencia, cheque u otros, limitados a facturas conciliadas de la
oficina y fecha de la sesión.

18.0.4.1.5
------------
Presenta Oficina / Caja como una lista fija durante la apertura, mostrando solo
cajas activas asociadas a una oficina y respetando las reglas por usuario.

18.0.4.1.4
------------
Permite seleccionar la caja u oficina durante el borrador de apertura y la
bloquea después de abrirla. Conserva además la corrección QWeb de ambos PDF.

18.0.4.1.3
------------
Corrige las celdas QWeb de los reportes diario y de depósito para que Odoo 18
genere ambos PDF sin aplicar widgets directamente sobre elementos de tabla.

18.0.4.1.2
------------
Calcula las ventas y el efectivo esperado con los movimientos propios de cada
sesión, evitando duplicar entre oficinas el total de un diario compartido.
Permite además abrir el formulario de una caja nueva antes de seleccionar la
oficina, sin intentar redondear con una moneda todavía vacía.

18.0.4.1.1
------------
Separa el cobro financiero del efectivo. El botón Pagar abre el selector normal
para Clover, Zelle, transferencia y cheque; el nuevo botón Enviar a caja crea
exclusivamente la solicitud auditable de efectivo para la sucursal.

18.0.4.1.0
------------
Relaciona cada caja comercial con una oficina, separa operadores de
responsables, valida que todos pertenezcan a la misma oficina y sincroniza los
grupos mínimos para cobrar o supervisar. Solo permite una caja comercial activa
por oficina y limita la cola de cobros a las cajas asignadas al usuario.

18.0.2.0.0
------------
Cada cobro en efectivo exige el desglose de los billetes recibidos. Cuando el
cliente entrega más que el importe de la factura, exige también el desglose
exacto del vuelto y verifica que la caja dispone de esos billetes. Conserva un
movimiento auditable por cobro y, al cierre, valida la cantidad esperada de
cada denominación, no solo el total monetario.

18.0.2.0.1
------------
El asistente de pago crea líneas de billetes solo cuando se selecciona la caja
de efectivo. Los cobros Clover y demás métodos financieros no leen ni requieren
permisos sobre el control de efectivo.

18.0.2.0.2
------------
Carga las líneas de billetes solo para Operadores de caja, con permisos
limitados a ese rol. Los usuarios de Clover no reciben campos de efectivo en
el asistente y el control de billetes continúa limitado a Caja de ventas.

18.0.2.1.0
------------
Al seleccionar Efectivo - Caja de ventas, precarga las denominaciones activas
para que el cajero escriba exclusivamente las cantidades. Excluye de ventas
los diarios nativos de efectivo que no estén configurados como Caja de ventas.

18.0.2.1.1
------------
Corrige el filtro de diarios del asistente de pago para reconocer Caja de ventas
cuando Odoo usa registros temporales, manteniendo oculto el efectivo nativo.

18.0.2.1.2
------------
Bloquea la adición y eliminación de filas de billetes en el cobro y descarta
de forma segura cualquier línea transitoria vacía enviada por el navegador.

18.0.2.1.3
------------
Fuerza el envío de la denominación precargada aunque el campo sea de solo
lectura, evitando líneas de cobro sin billete al guardar el asistente.

18.0.2.2.0
------------
Organiza en dos columnas el efectivo recibido y el vuelto a entregar, con
denominaciones precargadas y cantidades editables para ambos controles.

18.0.2.2.1
------------
Añade las monedas USD de 50, 25, 10, 5 y 1 centavos para registrar y devolver
importes exactos sin romper el control de arqueo por denominación.

18.0.2.2.2
------------
Amplía el bloque de efectivo al ancho completo del asistente y mantiene sus
dos columnas equilibradas para recibido y vuelto.

18.0.2.2.3
------------
Registra el movimiento auditable de efectivo mediante la lógica controlada del
sistema, preservando el usuario cobrador sin otorgar creación manual al cajero.

18.0.2.2.4
------------
Incluye Operador de caja dentro de Administración general para que gerencia
pueda operar el flujo de efectivo sin asignaciones manuales adicionales.

18.0.3.0.0
------------
Añade la auditoría sorpresa de caja: muestra las existencias esperadas por
denominación, registra el conteo físico y conserva las diferencias sin alterar
pagos, caja ni contabilidad.

18.0.3.0.1
------------
Declara USD 2 en el catálogo estándar para que las existencias y auditorías
usen las mismas denominaciones en Local, Pruebas y Gestión.

18.0.3.1.0
------------
Convierte la auditoría sorpresa en Arqueo de caja. Al iniciarlo, congela el
efectivo esperado y el detalle de cada cobro, efectivo recibido y vuelto;
genera una hoja PDF para conteo manual y permite registrar posteriormente el
resultado físico sin alterar pagos, caja ni contabilidad.

18.0.3.1.1
------------
Corrige la generación de la fotografía y del PDF de arqueo. Evita iniciar dos
arqueos pendientes para una misma caja y sesión.

18.0.3.1.2
------------
Bloquea solamente los cobros en efectivo mientras el arqueo está pendiente,
notifica internamente a los responsables de caja al inicio y al finalizar, y
mantiene disponibles los métodos de pago no efectivos.

18.0.4.0.0
------------
Añade solicitudes de efectivo enviadas por el vendedor a la cola del cajero de
su sucursal. El arqueo solo bloquea efectivo tras pulsar el botón presencial;
las solicitudes quedan en espera y se reactivan al registrar el conteo.

18.0.4.0.1
------------
Permite que vendedores creen y consulten solo sus propias solicitudes de
efectivo, mientras los cajeros autorizados ven y procesan la cola completa.

18.0.4.0.2
------------
Restringe una caja sin ciudad a Administración general; las cajas asignadas a
una ciudad solo pueden ser cobradas por sus responsables configurados.

18.0.4.0.3
------------
El botón Pagar de las facturas crea una solicitud de efectivo y notifica a
caja sin abrir un formulario de pago. Administración general puede iniciar y
controlar solicitudes aunque la caja esté definida para otra ciudad.

18.0.4.0.4
------------
El botón Pagar respeta el método elegido en la factura: abre el asistente de
tarjeta para que Clover procese las facturas preparadas como Pago con tarjeta,
y crea una solicitud de caja solamente para los cobros en efectivo.

18.0.1.0.1
------------
Excluye el diario BNK1 de los cobros directos de facturas para reservarlo a
depósitos y operaciones bancarias. El efectivo de ventas se registra en una
caja real independiente y queda disponible para apertura y cierre diario.

18.0.1.0.2
------------
Aplica de forma consistente el filtro de diarios disponibles en el asistente
de pago de facturas, manteniendo BNK1 fuera de la operación comercial.

18.0.1.0.3
------------
Filtra BNK1 desde el lote contable que genera las opciones del asistente de
pago, evitando que una recálculo estándar vuelva a mostrarlo en ventas.

18.0.1.0.4
------------
Permite a administradores acceder directamente al menú, apertura, cierre y
configuración de Caja sin requerir asignación manual de un nuevo rol.

18.0.1.0.5
------------
Renombra el acceso principal como Control de caja y lo ubica de forma visible
en la barra de Facturación para iniciar y controlar la venta diaria.
    """,
    "depends": ["account", "account_payment", "doorandoor_control_cobros", "doorandoor_tax_state", "doorandoor_commercial_office_tax"],
    "data": [
        "security/cash_security.xml",
        "security/ir.model.access.csv",
        "data/cash_data.xml",
        "views/cash_register_views.xml",
        "views/cash_collection_request_views.xml",
        "views/cash_audit_views.xml",
        "views/account_payment_register_views.xml",
        "wizard/cash_open_wizard_views.xml",
        "wizard/cash_close_wizard_views.xml",
        "wizard/cash_audit_wizard_views.xml",
        "views/cash_session_views.xml",
        "report/cash_reports.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
