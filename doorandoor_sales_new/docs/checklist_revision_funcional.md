# DoorAndDoor Sales New - Checklist de Revision Funcional

Usar esta lista durante la validacion funcional para confirmar si los flujos actuales siguen estables o si hace falta una nueva modificacion.

## 1. Cotizacion y Prefactura

- [ ] Crear una `cotizacion` con productos inventariables.
- [ ] Confirmar que el `stock visible` en cada linea sea correcto.
- [ ] Registrar la cotizacion.
- [ ] Verificar que se genere la `prefactura` en borrador.
- [ ] Confirmar que la prefactura quede con `reserva activa`.
- [ ] Abrir otra cotizacion o factura y validar que ese stock reservado ya no aparezca como libre.
- [ ] Imprimir la prefactura y revisar que salga identificada como `Prefactura`.

## 2. Reserva de 24 horas

- [ ] Revisar en la prefactura el `vencimiento de reserva`.
- [ ] Confirmar que mientras la reserva este vigente siga descontando stock visible.
- [ ] Simular vencimiento o ejecutar el proceso programado.
- [ ] Verificar que la reserva vencida se libere correctamente.
- [ ] Confirmar que el stock vuelva a mostrarse disponible despues de liberar la reserva.

## 3. Publicacion de la Prefactura

- [ ] Publicar la prefactura.
- [ ] Verificar que al publicar se elimine la `reserva temporal`.
- [ ] Confirmar que la `venta relacionada` quede enlazada.
- [ ] Confirmar que la venta quede `confirmada`.
- [ ] Verificar que se creen las `lineas de cumplimiento`.
- [ ] Confirmar que no se dupliquen lineas de cumplimiento al resincronizar o reprocesar.

## 4. Pago y Liberacion

- [ ] Registrar un `pago parcial`.
- [ ] Verificar que el sistema permita `fabricacion parcial` si aplica al producto.
- [ ] Confirmar que el `despacho` no quede totalmente liberado si la regla exige pago total.
- [ ] Registrar el `pago total`.
- [ ] Verificar que con pago total si se libere el despacho.

## 5. Despacho y Picking

- [ ] Revisar una factura relacionada con una venta que ya tenga `picking` abierto.
- [ ] Confirmar que el sistema reutilice el `stock.picking` existente.
- [ ] Verificar que no cree `stock.move` duplicados para la misma linea de venta.
- [ ] Confirmar que los estados del picking evolucionen correctamente.

## 6. Orden de Recogida

- [ ] Crear una `orden de recogida` desde la factura liberada.
- [ ] Verificar que traiga producto, cantidad y notas operativas.
- [ ] Confirmar que el estado quede `pending` o `ready` segun el picking.
- [ ] Imprimir la orden de recogida.
- [ ] Verificar que la orden de recogida no muestre montos ni total.
- [ ] Marcar la orden como `delivered`.
- [ ] Confirmar que quede registrada la trazabilidad de entrega.

## 7. Ajuste Manual de Inventario

- [ ] Intentar un `ajuste manual de inventario` que deje stock por debajo de lo comprometido.
- [ ] Confirmar que el sistema bloquee la operacion con error funcional.
- [ ] Intentar un ajuste permitido por encima de lo comprometido.
- [ ] Confirmar que ese ajuste si se pueda aplicar.

## 8. Revision Visual de Reportes

- [ ] Imprimir `factura`.
- [ ] Verificar que el bloque fiscal se vea correcto y sin solapamientos.
- [ ] Imprimir `picking`.
- [ ] Confirmar que barcode y QR salgan visibles.
- [ ] Imprimir `orden de recogida`.
- [ ] Confirmar que barcode y QR salgan visibles tambien ahi.
- [ ] Verificar que todos los reportes abran e impriman sin error.

## 9. Registro de Incidencias

- [ ] Anotar documento probado: cotizacion, factura, picking o pickup order.
- [ ] Anotar resultado esperado.
- [ ] Anotar resultado real.
- [ ] Clasificar la falla si aparece: funcional, visual o dato migrado.
- [ ] Guardar evidencia minima: numero de documento y captura si aplica.
