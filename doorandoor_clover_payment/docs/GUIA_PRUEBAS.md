# Guía de Pruebas

## Precondiciones

- Proveedor Clover en `Modo de prueba` y entorno `Sandbox`.
- Merchant ID y ambos tokens configurados en Odoo.
- Diario `CLVR` asociado al proveedor.
- Factura de prueba publicada, no pagada y con cliente de prueba.

## Matriz mínima

| Caso | Resultado esperado |
| --- | --- |
| Pago total Clover | Cargo aprobado, pago Odoo en CLVR y factura pagada. |
| Pago parcial Clover + Zelle | Primer pago reduce saldo; Zelle puede cerrar el residual. |
| Pago parcial Zelle + Clover | Clover cobra exactamente el saldo pendiente. |
| Pago parcial Clover + Clover | Cada cargo tiene referencia/idempotencia distinta y saldo final cero. |
| Tarjeta rechazada | No se crea pago ni asiento; factura queda pendiente. |
| Error de red/respuesta incierta | Operación queda `En revisión`; no hay reintento automático. |
| Reenvío del mismo formulario | Clover recibe la misma clave de idempotencia; no se duplica el cargo. |

## Evidencia

Para cada caso conservar:

1. Número de factura Odoo.
2. Referencia de operación Clover y estado.
3. Referencia de cargo de Clover.
4. Pago y asiento en CLVR.
5. Saldo residual de la factura.

## Consulta en Clover Sandbox

En el Merchant Dashboard del merchant sandbox, usar `Settings > Transactions > Payments`.
Un cobro Ecommerce aprobado también crea una orden asociada. La consulta técnica de
los cargos se realiza desde el backend mediante `GET https://scl-sandbox.dev.clover.com/v1/charges`;
no se deben abrir URLs con tokens en el navegador.
