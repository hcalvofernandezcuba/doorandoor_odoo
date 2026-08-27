# Capacitación de Cobros y Pagos DoorAndDoor

Guía operativa para registrar, identificar, validar y aplicar los ingresos
reales sin duplicar pagos ni alterar incorrectamente las facturas.

## Regla principal

- Ventas puede reportar que el cliente manifestó haber pagado.
- El reporte comercial no crea dinero, asiento ni conciliación.
- Solo el responsable autorizado registra el pago oficial recibido.
- Únicamente el pago oficial validado reduce el saldo de la factura.
- Un control reportado no puede validarse sin un pago real enlazado.

## Pago oficial identificado

1. Abrir Cobros y Pagos y crear un ingreso.
2. Registrar importe real, fecha, diario, pagador y referencia.
3. Asociar una sola factura.
4. Confirmar el pago.
5. Revisar el Control de Cobro creado o enlazado.
6. Validar monto, diario, referencia, cliente y factura.
7. Conciliar y comprobar el nuevo saldo de la factura.

El pagador puede ser distinto del cliente. Una referencia válida de factura
permite conservar al pagador real y aplicar el ingreso al documento correcto.

## Pago por identificar

1. Registrar el dinero cuando se detecta en banco, Zelle, cheque o caja.
2. Dejar el control Por identificar si no existe evidencia suficiente.
3. No asociar una factura por suposición.
4. Investigar cliente y documento.
5. Asociar y conciliar cuando la identificación sea segura.

Registrar el pago y conciliarlo son dos momentos distintos.

## Pagos parciales y regla del 50 por ciento

El porcentaje se calcula sobre el total completo de la factura.

- Menos del 50 por ciento: acepta el parcial, reduce el saldo y no libera fabricación.
- Acumulado igual o superior al 50 por ciento: libera una sola vez la fabricación de las líneas fabricables.
- Menor al total: no libera despacho ni entrega.
- Pago total: residual cero, factura pagada y entrega liberada cuando exista disponibilidad física.

## Pago superior al saldo

1. Aplicar a la factura solamente su saldo pendiente.
2. Liquidar la factura.
3. Registrar el excedente como crédito del mismo cliente.
4. Usar su subcuenta individual bajo `120000 Pagos Anticipados`.
5. Mostrar importe recibido, aplicado y crédito restante.
6. Aplicar posteriormente ese crédito a otra factura del mismo cliente.

Nunca debe utilizarse la cuenta de otro cliente.

## Crédito autorizado por gerencia

1. Ajustes define el límite autorizado en la ficha del cliente.
2. Desde una factura confirmada se selecciona el diario de crédito autorizado.
3. Se informa el importe y se solicita el código de seis dígitos.
4. El código permanece vigente diez minutos y es de un solo uso.
5. Debe coincidir cliente, factura, diario, moneda e importe.
6. Al confirmar, la factura se liquida total o parcialmente y queda una partida financiada del cliente.
7. El cobro real posterior se concilia contra su subcuenta y recupera el crédito disponible.

## Diario Cheques

El diario Cheques sigue la misma operatoria controlada de Zelle:

- Ventas solo reporta el posible cobro.
- El reporte no afecta contabilidad ni la factura.
- Cobros y Pagos registra el cheque real recibido.
- El control se valida después de revisar cheque, importe, pagador y factura.
- Un cheque no identificado queda Por identificar.
- La factura solo cambia cuando existe pago oficial validado.

## Comprobación final

Revisar en la factura estado funcional, total validado, pendiente, rechazado,
saldo residual y crédito disponible. Revisar en Contabilidad el pago oficial,
asiento, conciliación y cuenta individual correcta.

