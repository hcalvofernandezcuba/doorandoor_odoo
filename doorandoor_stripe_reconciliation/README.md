# DoorAndDoor Stripe Bank Reconciliation

Primera capa de conciliación para Odoo 18 Community. Mantiene separado el
cobro del cliente y la llegada del dinero al banco.

## Alcance inicial

- instala y reutiliza `payment_stripe` estándar;
- descarga payouts y balance transactions de Stripe;
- calcula bruto, comisión, neto y diferencia;
- propone un único movimiento bancario por importe y ventana de ±3 días;
- no publica ni reconcilia asientos automáticamente;
- no modifica `doorandoor_control_cobros`.
- para una transacción Stripe asociada a un solo PO, reutiliza el pago contable
  estándar y crea automáticamente un Control de Cobro validado;

## Puesta en marcha segura

1. Configure Stripe con claves `pk_test_...` y `sk_test_...`.
2. Mantenga el proveedor en modo de prueba.
3. Seleccione el diario bancario de pruebas en el bloque de conciliación.
4. Genere pagos y payouts simulados en Stripe Sandbox.
5. Importe un extracto OFX/CSV simulado en el diario.
6. Sincronice las liquidaciones y revise la propuesta.

La automatización horaria está desactivada de fábrica. Solo debe activarse
después de validar manualmente la correspondencia entre payouts y depósitos.

El botón **Preparar diario Stripe** crea una cuenta transitoria conciliable y
el diario bancario `STRP`, y lo clasifica como vía inmediata. Es idempotente y
no habilita el proveedor ni contiene credenciales. El método Tarjeta se activa
con el comportamiento estándar de Odoo cuando Stripe pasa a modo de prueba.
