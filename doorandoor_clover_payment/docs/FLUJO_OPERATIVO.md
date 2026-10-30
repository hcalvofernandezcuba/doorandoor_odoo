# Flujo Operativo

1. El vendedor publica la factura y pulsa **Pagar**.
2. Selecciona Clover y Odoo calcula el importe exigible: total o pago parcial según
   la política vigente de la factura.
3. Odoo crea una operación Clover con referencia interna e identificador de
   idempotencia único.
4. Se muestra el formulario iframe alojado por Clover dentro de la experiencia web
   de DoorAndDoor.
5. Clover tokeniza los datos de tarjeta en el navegador y devuelve un token `clv_`
   de un solo uso.
6. Odoo envía el token y el importe final al endpoint `POST /v1/charges` de Clover.
7. Si Clover aprueba, Odoo crea el pago contable usando el diario CLVR, actualiza la
   factura y conserva la referencia del cargo.
8. Si Clover rechaza, la factura no cambia y la operación queda `Rechazada`.
9. Ante timeout o respuesta no concluyente, la operación queda `En revisión`; no se
   debe reintentar hasta verificar la transacción en Clover.

## Pagos parciales

El primer pago usa el importe definido en las Opciones de pago de la factura. Tras
confirmarse, el saldo residual queda disponible para un segundo pago por Clover,
Zelle u otra vía permitida. Cada operación de tarjeta debe tener su propio importe,
referencia e identificador de idempotencia.

## Cargos por tarjeta

La política de cargos es contable y comercial de DoorAndDoor. No se debe copiar
automáticamente el porcentaje de Stripe: Clover puede aplicar sus propios cargos o
surcharges según el contrato y jurisdicción. El importe que Odoo muestra como total
es el mismo que se envía a Clover.
