# Crédito autorizado con código de seis dígitos

## Objetivo

Permitir que gerencia conceda un límite de crédito a un cliente y que Ventas
lo aplique a una factura solamente después de recibir la autorización expresa
del cliente mediante un código temporal de seis dígitos.

## Configuración

1. Un administrador de Ajustes abre el contacto comercial del cliente.
2. Define **Crédito autorizado por gerencia**.
3. En Contabilidad crea o utiliza un diario de tipo Banco y selecciona el
   flujo **Crédito con autorización del cliente**. En el diario selecciona la
   cuenta madre de cartera de créditos autorizados.
   En la configuración local se usa `122000 Créditos Autorizados Clientes`;
   sus subcuentas se generan como `122001`, `122002`, etc.
4. En local se configuran los parámetros secretos
   `doorandoor_credit.telegram_bot_token` y
   `doorandoor_credit.telegram_chat_id`. No se guardan credenciales en código.

## Uso desde una factura

1. La factura debe estar confirmada y conservar saldo pendiente.
2. En **Pagar**, se selecciona el diario de crédito autorizado.
3. Se indica el importe y se pulsa **Enviar código de 6 dígitos**.
4. Odoo reserva ese importe durante diez minutos y envía el código al bot.
5. Se introduce el código y se confirma el pago.
6. Odoo comprueba cliente, factura, diario, moneda, importe, vigencia y saldo.
7. Si todo coincide, liquida total o parcialmente la factura y deja el mismo
   importe como partida abierta financiada del cliente.

El campo del código debe permanecer vacío antes de pulsar **Enviar código**.
Solo se vuelve obligatorio después de que Telegram acepte la solicitud.

El mensaje del bot incluye también cliente, factura, fecha, vendedor, productos
y cantidades, total facturado, crédito solicitado, saldo restante de factura y
crédito disponible antes y después. El mismo contenido se reutilizará en el
futuro canal de correo electrónico.

La URL no está fija en el código. El mensaje toma `web.base.url` de la base de
datos e incluye tanto la instancia origen como un enlace directo a la factura.
Por ello cambia automáticamente entre local, pruebas y producción.

## Operaciones bloqueadas

El diario no puede utilizarse desde Pagos para **Enviar dinero** o **Recibir
dinero**. El bloqueo se aplica al crear, modificar y validar, incluyendo
importaciones y llamadas externas. Asignar crédito se hace únicamente en la
ficha del cliente; consumirlo se hace únicamente desde una factura confirmada.

## Contabilidad y recuperación del saldo

La autorización gerencial no se contabiliza como dinero bancario. Al primer
uso Odoo crea automáticamente una subcuenta conciliable exclusiva del cliente,
siguiendo la numeración de la cuenta madre configurada en el diario. Cuando se
usa el crédito, Odoo acredita la deuda original de la factura y debita esa
subcuenta. Los cobros reales posteriores se concilian contra ella. Su residual
determina el crédito utilizado; al cobrarlo, vuelve a aumentar automáticamente
el crédito disponible.

## Seguridad

- Código aleatorio de seis dígitos, almacenado solamente como hash.
- Vigencia de diez minutos y un solo uso.
- Vinculado de forma inmutable a cliente, factura, diario, moneda e importe.
- Un reenvío cancela la autorización anterior.
- Bloqueo de base de datos durante la validación para impedir doble consumo.
- Solo Ajustes puede modificar el límite concedido.
# Cobro posterior del crédito utilizado

La factura liquidada con crédito autorizado no vuelve a recibir pagos. La deuda
queda abierta en la subcuenta conciliable 122xxx correspondiente al cliente.

Para registrar una devolución del cliente:

1. Abra **Control de Cobros > Pagos** y cree un pago de entrada.
2. Seleccione el cliente y el diario real por el que entró el dinero (Zelle,
   Cheques, banco o caja). No utilice el diario Crédito Autorizado.
3. Deje vacía **Factura asociada** y seleccione en **Crédito autorizado a
   liquidar** la operación pendiente. El formulario muestra su factura origen y
   el saldo financiado actual.
4. Indique un importe igual o menor que el saldo. Se permiten pagos parciales;
   nunca se permite exceder la deuda seleccionada.
5. Confirme el pago. Se crea un control con origen **Cobro de crédito
   autorizado** y queda pendiente de validación.
6. Control de Cobros verifica la entrada real y valida el control. El asiento
   debita el banco/caja y acredita la subcuenta 122xxx del cliente; ambas
   partidas se concilian contra la deuda financiada.

Después de validar, el control conserva el saldo anterior, el importe aplicado
y el saldo restante. La autorización cambia automáticamente a pago parcial o
liquidado, y los valores de crédito usado y disponible del contacto se
actualizan desde la contabilidad. Este cobro no requiere OTP porque no concede
crédito nuevo y no altera el estado de la factura original.
