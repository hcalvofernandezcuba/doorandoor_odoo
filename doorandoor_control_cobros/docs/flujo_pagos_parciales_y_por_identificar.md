# Flujo de Pagos Parciales y Pagos por Identificar

Fecha: 2026-08-02
Modulo: `doorandoor_control_cobros`

## Objetivo

Definir la logica funcional para soportar:

- una misma factura pagada por varias vias o en varios momentos
- pagos parciales sobre una misma factura
- pagos recibidos por contabilidad antes de identificar la factura exacta
- asociacion posterior del pago a la factura y al pago contable real

La meta es que ventas, control de cobros y contabilidad trabajen sobre un flujo trazable sin perder consistencia contable.

## Problema del modelo actual

Hoy el flujo esta mas cerca de pensar:

- `1 factura -> 1 control -> 1 pago`

Ese enfoque no escala bien cuando:

- el cliente paga una parte por Zelle y otra por transferencia
- el cliente hace varios pagos parciales en dias distintos
- contabilidad ve un ingreso en banco pero aun no sabe a que factura corresponde
- un mismo cliente tiene varias facturas abiertas y hay que identificar despues a cual aplicar el pago

## Cambio conceptual recomendado

La unidad operativa no debe ser "la factura completa", sino "cada evidencia de pago".

El modelo correcto debe pasar a:

- `1 factura -> N controles de cobro -> N pagos reales o potenciales`

Eso significa:

- cada pago parcial genera su propio control
- cada via de pago genera su propio control
- cada control puede validarse o rechazarse por separado
- el estado final de la factura depende de la suma de controles validados

## Regla central

Un control de cobro representa un tramo de pago, no necesariamente el pago total de la factura.

## Modelo funcional propuesto

### 1. Control de cobro como registro individual

Cada registro de `doorandoor.cobro.control` debe representar una sola evidencia de pago.

Ejemplos:

- pago parcial 1 por Zelle
- pago parcial 2 por transferencia
- pago parcial 3 en efectivo

Cada uno debe tener su propio estado y su propia trazabilidad.

### 2. La factura como agregador

La factura debe calcular su estado a partir del conjunto de controles asociados.

No debe depender de un solo control.

## Casos de negocio que debe soportar

### Caso A. Factura con dos pagos parciales por diferentes vias

Ejemplo:

- factura por 1,000
- cliente paga 400 por Zelle
- cliente paga 600 por transferencia

Flujo:

- se crean dos controles
- cada control se revisa por separado
- cuando se valida el primero, la factura queda parcialmente pagada
- cuando se valida el segundo, la factura queda totalmente pagada

### Caso B. Factura con varios pagos parciales en el tiempo

Ejemplo:

- factura por 1,000
- cliente paga 300 hoy
- paga 300 manana
- paga 400 la semana proxima

Flujo:

- tres controles separados
- el residual de la factura debe bajar con cada validacion real
- la factura pasa de pendiente a parcial y luego a pagada

### Caso C. Contabilidad recibe el pago antes de saber la factura

Ejemplo:

- entra transferencia de 250
- el concepto no identifica claramente la factura
- control de pagos crea o registra el ingreso como pendiente de identificar

Flujo:

- se crea un control sin factura asociada inicialmente
- el control queda en una bandeja de pagos por identificar
- cuando se determine la factura correcta, se vincula manualmente
- despues se valida normalmente

### Caso D. Un mismo pago debe asociarse despues al pago contable real

Ejemplo:

- primero se captura la evidencia del cliente
- luego contabilidad encuentra o crea el `account.payment`

Flujo:

- el control puede existir sin `payment_id`
- mas adelante se enlaza con el pago contable real
- la conciliacion solo debe ejecutarse cuando la informacion critica este completa

## Campos y estructura recomendada

### En `doorandoor.cobro.control`

Campos actuales que deben mantenerse:

- `partner_id`
- `move_id`
- `payment_id`
- `journal_id`
- `payment_reference`
- `amount_reported`
- `state`
- `sale_user_id`
- `accountant_user_id`
- `review_date`
- `rejection_reason`
- `notes`

Campos o comportamientos a reforzar:

- `move_id`
  Debe poder quedar vacio temporalmente para pagos por identificar.

- `payment_id`
  Debe poder quedar vacio temporalmente hasta enlazar el pago contable real.

- `journal_id`
  Debe seguir representando la via o diario reportado.

Campos nuevos recomendados:

- `is_unidentified`
  Booleano o computado para distinguir pagos aun no vinculados a factura.

- `identification_notes`
  Observaciones operativas mientras se identifica la factura correcta.

- `matching_status`
  Opcional, para distinguir:
  - sin factura
  - factura vinculada
  - pago contable vinculado
  - listo para validar

- `amount_validated`
  Opcional si en el futuro se permite validar un monto distinto al reportado.

## Estados propuestos del control individual

Estados base:

- `draft`
- `reported`
- `pending`
- `review`
- `validated`
- `rejected`

Estado adicional recomendado:

- `unidentified`

Uso:

- `unidentified`
  El pago existe como evidencia o hallazgo contable, pero todavia no tiene factura identificada.

Si prefieres no agregar un estado nuevo, se puede modelar con:

- `move_id = False`
- un filtro especial `Pagos por identificar`

Mi recomendacion operativa:

- usar un estado o bandera visible
- evitar que el equipo tenga que inferirlo solo por un campo vacio

## Estados propuestos de la factura

La factura debe calcularse por agregacion de controles validados y pendientes.

Estados funcionales sugeridos:

- `Sin control`
- `Revisando`
- `Pagada parcialmente`
- `Pagada`
- `Rechazada`
- opcional: `Con incidencias`

### Regla de calculo

- si no hay controles:
  `Sin control`

- si hay controles pendientes o en revision:
  `Revisando`

- si hay monto validado mayor que cero pero menor que el total:
  `Pagada parcialmente`

- si el monto validado cubre el total:
  `Pagada`

- si todos los controles relacionados estan rechazados y no hay monto validado:
  `Rechazada`

## Regla contable

La contabilidad real no debe depender del control visual solamente.

Cuando un control sea validado:

1. debe existir o enlazarse el `account.payment`
2. el pago debe quedar posteado correctamente
3. debe reconciliarse contra la factura por el monto correspondiente
4. el residual de la factura debe bajar
5. los totales y estados deben recalcularse
6. el movimiento debe quedar reflejado correctamente para libros mayores

## Regla de suma

Para una factura:

- `total_reportado = suma de todos los controles no rechazados`
- `total_validado = suma de controles validados`
- `total_rechazado = suma de controles rechazados`
- `saldo_pendiente = total_factura - total_validado`

La factura no debe cerrarse por `total_reportado`.

Debe cerrarse por `total_validado` realmente conciliado.

## Reglas de validacion sugeridas

### No permitir validar si:

- no hay cliente
- no hay monto
- el monto es cero o negativo
- no existe factura enlazada, salvo que definamos una validacion operativa separada
- no existe `payment_id`, si el modelo exige impacto contable inmediato

### No permitir doble conteo

Debemos evitar que:

- un mismo `payment_id` se valide dos veces para la misma factura
- un mismo control impacte mas de una vez el residual

### Permitir reasociacion controlada

La controladora debe poder:

- asignar factura despues
- cambiar factura si se detecto error antes de validar
- enlazar `payment_id` despues

Pero una vez validado, idealmente esos cambios deben quedar restringidos o auditados.

## Cambios recomendados en UI

### 1. Vista de Control de Cobros

Agregar filtros o secciones:

- `Pendientes de revision`
- `Pagos por identificar`
- `Parciales`
- `Validados`
- `Rechazados`

### 2. En la factura

Agregar visibilidad del agregado:

- total reportado
- total validado
- total rechazado
- saldo pendiente
- lista de controles asociados

### 3. Smart button

El boton de `Controles de cobro` debe abrir todos los controles de la factura, no uno solo.

### 4. Vista del control

Debe permitir:

- enlazar factura manualmente
- enlazar pago contable manualmente
- ver si es pago parcial
- ver el monto pendiente restante de la factura

## Flujo recomendado

### Flujo 1. Pago reportado por ventas

1. ventas registra pago
2. se crea un control individual
3. factura pasa a `Revisando`
4. control de cobros valida o rechaza
5. si valida, se concilia el monto correspondiente
6. la factura recalcula su saldo

### Flujo 2. Pago detectado por contabilidad sin factura

1. contabilidad registra control sin factura
2. control queda en `Pagos por identificar`
3. luego se vincula factura y pago
4. pasa a revision o validacion
5. impacta saldo solo cuando este correctamente asociado

### Flujo 3. Factura con pagos mixtos

1. la factura recibe varios controles
2. algunos se validan, otros quedan pendientes
3. la factura muestra:
   - total validado
   - saldo pendiente
   - estado parcial o en revision
4. se cierra solo al completar monto validado conciliado

## Decision tecnica importante

No recomiendo "asociar dos pagos a un mismo control" como idea principal.

Lo mas estable es:

- muchos controles por factura
- un control por evidencia de pago
- asociacion flexible posterior de factura y pago contable

Eso simplifica:

- trazabilidad
- auditoria
- rechazo parcial
- conciliacion parcial
- soporte de varias vias de pago

## Propuesta de implementacion por fases

### Fase 1

- permitir controles sin factura
- agregar filtro `Pagos por identificar`
- reforzar multiples controles por factura
- mostrar totales agregados en la factura

### Fase 2

- asistente o accion para asociar manualmente factura y pago contable
- validaciones para evitar doble aplicacion
- mejoras en residual y conciliacion parcial

### Fase 3

- tablero operativo para controladoras
- conciliacion asistida por monto, cliente, referencia y fecha
- reglas automaticas de sugerencia

## Recomendacion final

La modificacion debe construirse sobre esta logica:

- una factura puede tener muchos controles
- cada control representa una evidencia individual de pago
- un control puede nacer sin factura o sin pago contable
- la validacion real suma montos validados y conciliados
- la factura cierra por conciliacion contable acumulada, no por simple reporte operativo

## Siguiente paso sugerido

Traducir esta definicion funcional en una especificacion tecnica con:

- campos nuevos
- reglas de negocio exactas
- cambios en vistas
- orden de implementacion
- casos de prueba
