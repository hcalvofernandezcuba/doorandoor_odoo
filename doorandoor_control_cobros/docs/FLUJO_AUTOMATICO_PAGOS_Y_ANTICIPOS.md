# Flujo automático de pagos y anticipos

## Identificación de la factura

Los pagos entrantes buscan una referencia con formato `INV/año/número` en el
memo o referencia del pago. Si existe exactamente una factura publicada con
ese número y compañía, se asocia automáticamente.

El pagador puede ser diferente del cliente facturado. En ese caso se conserva
en **Pagador informado** y el asiento del pago se prepara contablemente para el
cliente de la factura.

Si no se encuentra una única factura, el pago continúa por el procedimiento
manual de Control de Cobros.

## Regla del porcentaje

El porcentaje se calcula siempre sobre el total completo de la factura:

`pagos acumulados / total de la factura × 100`

- Factura con fabricación y acumulado menor de 50 %: queda **En revisión**.
- Factura con fabricación y acumulado desde 50 %: valida los controles
  asociados y libera las órdenes de fabricación.
- Factura sin fabricación: se automatiza al completar el 100 %.
- El despacho requiere el pago total aunque la producción se haya liberado.

## Excedentes y anticipos

Cuando el pago supera el saldo de la factura, la factura se liquida por su
residual y el excedente se traslada a la subcuenta conciliable del cliente.

La ficha del contacto mantiene el campo **Cuenta de pagos anticipados**.

1. Si el cliente ya tiene una cuenta, se reutiliza.
2. Si no tiene, se localiza `120000 - Pagos Anticipados` de la compañía.
3. En compañías con país fiscal Estados Unidos, si `120000` no existe se crea
   como pasivo corriente conciliable.
4. Se crea el siguiente código disponible: `120001`, `120002`, etc.
5. La cuenta se guarda en el cliente y se utiliza en posteriores créditos.

La creación del código usa un bloqueo transaccional para evitar que dos pagos
simultáneos creen la misma subcuenta.

## Pruebas recomendadas

1. Pago menor de 50 % para factura con fabricación.
2. Segundo pago que lleve el acumulado exactamente a 50 %.
3. Confirmar que se crea la MO y no el despacho.
4. Pago total para factura sin fabricación.
5. Pago superior al residual con pagador diferente.
6. Confirmar factura pagada, subcuenta del cliente, asiento y saldo disponible.
7. Usar el crédito en otra factura y comprobar el saldo restante.
