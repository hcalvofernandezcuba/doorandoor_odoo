# DoorAndDoor Sales New - Sprint Actual

## Objetivo del sprint

Cerrar la Fase E del backlog con foco en recogida operativa en almacen:

- crear ordenes de recogida desde facturacion
- registrar su seguimiento en lista con estados
- dar visibilidad a ventas e inventario

## Alcance inmediato

### Tarea 1

- Nombre:
  Modelo y flujo de orden de recogida

- Objetivo:
  Crear una entidad operativa propia para controlar recogidas posteriores a la factura.

- Resultado esperado:
  Ventas puede emitir una orden de recogida y localizarla despues.

- Estado:
  Implementada

### Tarea 2

- Nombre:
  Lista operativa y estados

- Objetivo:
  Permitir seguimiento de la orden desde vistas de lista.

- Propuesta inicial:
  Estados propuestos: nueva, pendiente, lista, entregada, cancelada.

- Estado:
  Implementada

### Tarea 3

- Nombre:
  Visibilidad y reportes por area

- Objetivo:
  Exponer las ordenes desde facturacion e inventario con enfoque distinto por estado.

- Estado:
  Implementada

## Fuera de alcance de este sprint

- proyeccion de produccion
- reglas avanzadas de bonificacion por categoria de producto
- refinamientos adicionales de impresion que no afecten recogida

## Criterio de cierre

Este sprint se considera listo cuando:

- exista una orden de recogida propia ligada a factura
- la orden pueda imprimirse para el cliente
- la orden quede guardada en una lista con estados
- almacen pueda marcarla como entregada
- la lista sea visible desde ventas e inventario
- el cambio quede documentado y validado en el entorno Odoo

## Resultado actual

- Las fases A y B quedan cerradas y validadas.
- La Fase C ya tiene el ajuste inicial de impuestos en factura impresa.
- La Fase E queda implementada y validada.
- La regla de despacho queda ajustada para exigir factura totalmente pagada.
- La regla de fabricacion queda validada con pago parcial.
- La lectura de stock por almacen queda extendida tambien a lineas de factura.
- La regla base de `listo para recoger` queda cerrada:
  - linea con cantidad liberada no entregada
  - con picking asociado no cancelado
  - orden `ready` si el picking esta `assigned` o `done`
- Las ordenes de recogida ya se generan desde factura, se listan por estado y pueden marcarse como entregadas.
- La lista queda visible desde ventas e inventario.
- La ficha del cliente ya muestra foto editable en `res.partner`.
- El flujo de despacho ahora reutiliza el picking abierto de la venta cuando la factura relacionada intenta liberar esa misma salida.
- Se evita crear `stock.move` duplicados en el mismo picking para la misma `sale_line_id`.

## Problemas detectados al cierre

- Se detecto riesgo de que un ajuste manual de inventario redujera el stock fisico aun cuando una factura ya tenia cantidades pagadas o parcialmente pagadas comprometidas para entrega.
- Esto podia romper la consistencia entre lo cobrado, lo liberado por pago y la existencia real en almacen.

## Soluciones aplicadas

- Se bloqueo el ajuste manual de inventario cuando intenta dejar el stock por debajo de las unidades ya liberadas por facturas pagadas o parcialmente pagadas.
- La validacion se apoya en las lineas de cumplimiento del modulo para calcular cantidad liberada pendiente de entrega.
- El comportamiento fue validado con pruebas automatizadas ejecutadas en el entorno Docker Odoo.
- La columna de stock visible en lineas de factura ahora muestra stock neto vendible, descontando cantidades ya comprometidas por pagos anteriores pendientes de entrega.
- Los reportes de factura, picking y orden de recogida ahora muestran codigo de barras y QR para identificacion y apertura del documento.
- La orden de recogida impresa queda enfocada solo en producto, cantidad y notas operativas, sin montos ni total.
- Las prefacturas en borrador ahora sostienen una reserva temporal de inventario por 24 horas.
- Esa reserva temporal se descuenta del stock visible en cotizacion y factura mientras siga activa.
- Si la prefactura no se publica como factura dentro del plazo, la reserva se libera automaticamente.

## Contexto de migracion conocido

- Durante las pruebas aparecieron productos heredados desde Zoho con tipificacion de consumible o servicio, lo que impide tratarlos como inventario fisico real dentro de Odoo.
- Ese punto se considera una condicion conocida de datos migrados y no una falla del bloqueo funcional implementado.
- Para la base de produccion, este criterio ya quedo contemplado en la preparacion de la migracion desde Zoho para asegurar productos inventariables con tipificacion correcta.

## Cierre documental al corte actual

Hasta este punto se considera cerrado y documentado:

- la separacion entre despacho con pago total y fabricacion con pago parcial
- la extension de stock por almacen hacia facturacion
- la base de recogida operativa en almacen
- la proteccion contra duplicacion de salida entre venta y factura
- el bloqueo de ajustes manuales que dejen stock por debajo de cantidades ya comprometidas por pago
- la identificacion escaneable de documentos operativos y comerciales desde reportes impresos
- la reserva temporal de inventario por 24 horas para prefacturas en borrador

Queda expresamente fuera de avance adicional hasta nueva definicion del cliente:

- reglas avanzadas por almacen
- criterio final de semaforos y visibilidad entre venta y factura
- refinamientos adicionales de impresion
- decisiones de produccion avanzada aun no definidas
