# Especificacion Tecnica - Pagos Parciales, Multiples Vias y Pagos por Identificar

Fecha: 2026-08-02
Modulo: `doorandoor_control_cobros`
Documento relacionado:
- `docs/flujo_pagos_parciales_y_por_identificar.md`

## Objetivo tecnico

Extender `doorandoor_control_cobros` para soportar:

- multiples pagos parciales sobre una misma factura
- pagos por distintas vias para una misma factura
- controles de cobro sin factura identificada al momento de crear el registro
- asociacion posterior de factura y pago contable
- acumulacion del monto validado para cerrar total o parcialmente la factura

## Principio de diseno

La unidad de control sera el tramo de pago.

Eso significa:

- un control no representa la factura completa
- un control representa una evidencia individual de pago
- una factura puede tener N controles
- el estado de la factura se calcula por agregacion de esos controles

## Modelos involucrados

### 1. `doorandoor.cobro.control`

Sigue siendo el modelo principal.

#### Campos actuales que se conservan

- `name`
- `move_id`
- `partner_id`
- `currency_id`
- `company_id`
- `journal_id`
- `payment_id`
- `payment_state`
- `invoice_payment_state`
- `sale_user_id`
- `accountant_user_id`
- `payment_date`
- `amount_reported`
- `payment_reference`
- `state`
- `review_date`
- `rejection_reason`
- `notes`

#### Nuevos campos propuestos

- `invoice_id`
  No hace falta si seguimos usando `move_id`.
  Recomendacion: mantener `move_id` como campo principal.

- `matching_status = fields.Selection(...)`
  Valores sugeridos:
  - `unidentified`
  - `invoice_linked`
  - `payment_linked`
  - `ready_to_validate`
  - `validated`

  Proposito:
  Dar lectura rapida del nivel de completitud del control.

- `is_unidentified = fields.Boolean(...)`
  Computado desde:
  - `move_id`
  - `state`

  Regla:
  - `True` cuando no hay factura asociada
  - `False` cuando ya hay factura

- `is_partial = fields.Boolean(...)`
  Computado.

  Regla:
  - `True` si el monto reportado es menor que el residual vigente de la factura al momento de comparar

- `invoice_residual_snapshot = fields.Monetary(...)`
  Opcional.

  Proposito:
  Guardar referencia del residual observado cuando se creo o actualizo el control.

- `validated_amount = fields.Monetary(...)`
  Recomendado.

  Regla:
  - por defecto igual a `amount_reported`
  - en el futuro permitira validar monto distinto si hace falta ajustar diferencias

- `source_type = fields.Selection(...)`
  Valores sugeridos:
  - `sales_report`
  - `accounting_detected`
  - `manual`

  Proposito:
  Saber si el control lo inicio ventas, contabilidad o una carga manual.

- `identification_notes = fields.Text(...)`
  Proposito:
  Notas operativas mientras se identifica la factura correcta.

### 2. `account.move`

La factura pasa a ser agregador de controles.

#### Nuevos campos propuestos

- `ddc_total_reported = fields.Monetary(...)`
  Suma de controles no rechazados.

- `ddc_total_validated = fields.Monetary(...)`
  Suma de controles validados.

- `ddc_total_rejected = fields.Monetary(...)`
  Suma de controles rechazados.

- `ddc_total_pending = fields.Monetary(...)`
  Suma de controles pendientes, reportados o en revision.

- `ddc_balance_pending = fields.Monetary(...)`
  Formula:
  - `amount_total - ddc_total_validated`
  Ajustado por moneda y residual real.

- `ddc_has_unidentified_controls = fields.Boolean(...)`
  Opcional.
  Puede ayudar a reportes si algun control se enlazo luego.

#### Campos actuales a mantener

- `ddc_control_ids`
- `ddc_control_count`
- `ddc_collection_state`
- `ddc_payment_review_state`

## Reglas de negocio

### Regla 1. Multiples controles por factura

Debe permitirse crear varios controles con el mismo `move_id`.

No debemos imponer unicidad por factura.

Restriccion a mantener:

- evitar duplicar el mismo `payment_id` para la misma factura si representa exactamente la misma aplicacion

Posible SQL o validacion Python:

- impedir duplicado cuando coincidan:
  - `payment_id`
  - `move_id`
  - `amount_reported`
  - `state != rejected`

### Regla 2. Control sin factura

Debe permitirse crear un control sin `move_id`.

Comportamiento:

- queda en bandeja `Pagos por identificar`
- no puede afectar residual de ninguna factura
- no puede cerrar factura
- no debe intentar conciliacion

### Regla 3. Control sin pago contable

Debe permitirse guardar control sin `payment_id` si aun no se ha localizado.

Pero:

- no debe validarse contablemente mientras no exista un pago real enlazado
- si se quiere un estado previo, puede quedar en `pending` o `review`

### Regla 4. Validacion contable

Un control solo debe pasar a `validated` si:

- tiene `move_id`
- tiene `payment_id`
- el `payment_id` esta posteado o puede postearse
- existe conciliacion posible entre pago y factura

### Regla 5. Cierre de factura

La factura debe cerrarse cuando la conciliacion acumulada deje el residual en cero.

No por simple suma operativa del `amount_reported`.

### Regla 6. Parcialidad

Si el monto validado acumulado es menor que el total de la factura:

- la factura queda parcial
- el ribbon/cartel y estado funcional deben reflejarlo

## Logica de calculo de factura

### `ddc_collection_state`

Recomendacion de ajuste:

- `pending` si existe al menos un control en:
  - `draft`
  - `reported`
  - `pending`
  - `review`

- `rejected` si todos los controles activos estan rechazados y no hay validaciones

- `validated` si hay validaciones y no quedan pendientes

### `ddc_payment_review_state`

Recomendacion:

- `no_control`
  Si no hay controles

- `reviewing`
  Si hay pendientes

- `validated`
  Si el monto validado acumulado cubre totalmente la factura o si el flujo de revision ya cerro sin incidencias

- nuevo estado recomendado:
  `partial`

- `rejected`
  Si no hay validaciones y el escenario vigente es rechazo

Si no queremos agregar `partial` al campo actual, entonces:

- mantener el estado visual parcial usando ribbon/cartel y totales en pantalla

Mi recomendacion:

- agregar `partial` al `ddc_payment_review_state`

Valores sugeridos finales:

- `no_control`
- `reviewing`
- `partial`
- `validated`
- `rejected`

## Reglas de conciliacion

### Flujo de validacion de un control

En `action_validate()`:

1. Verificar `move_id`
2. Verificar `payment_id`
3. Si el pago esta en draft o in_process:
   - asegurar `outstanding_account_id`
   - `payment.action_post()`
   - postear `payment.move_id` si aun esta draft
4. Buscar lineas conciliables del pago:
   - partner correcto
   - cuenta conciliable
   - receivable/payable
   - no reconciliadas
5. Buscar lineas conciliables de la factura:
   - mismas condiciones
6. Conciliar por cuenta comun
7. Recalcular factura:
   - `_compute_amount()`
   - `_compute_payment_state()`
   - `_ddc_refresh_control_status()`

### Importante

La conciliacion debe ser acumulativa.

Si hay varios pagos parciales:

- el primer control baja una parte del residual
- el segundo baja otra parte
- el tercero cierra lo restante

## Cambios tecnicos por archivo

### `models/cobro_control.py`

Cambios:

- permitir `move_id` opcional
- agregar campos:
  - `matching_status`
  - `is_unidentified`
  - `is_partial`
  - `validated_amount`
  - `source_type`
  - `identification_notes`
- endurecer `action_validate()`
- impedir validacion si falta `move_id` o `payment_id`
- agregar accion para asociar factura
- agregar accion para asociar pago contable

### `models/account_move.py`

Cambios:

- agregar totales agregados:
  - `ddc_total_reported`
  - `ddc_total_validated`
  - `ddc_total_rejected`
  - `ddc_total_pending`
  - `ddc_balance_pending`
- recalcular estado de revision segun controles multiples
- ajustar `payment_state` visual si la factura esta parcial

### `models/account_payment_register.py`

Cambios:

- mantener creacion automatica de control desde ventas
- si la factura ya tiene otros controles, permitir agregar otro mas
- publicar mensaje mas claro en chatter indicando pago parcial o nuevo tramo si aplica

### `views/control_cobros_views.xml`

Cambios:

- agregar filtros:
  - `Pagos por identificar`
  - `Con factura`
  - `Sin pago contable`
  - `Parciales`
- mostrar columnas nuevas:
  - `matching_status`
  - `validated_amount`
  - `source_type`
  - `is_partial`

### `views/account_move_views.xml`

Cambios:

- agregar bloque resumen de control:
  - total reportado
  - total validado
  - total rechazado
  - saldo pendiente de validar
- mostrar si la factura esta parcial
- mantener carteles y ribbons ya existentes

### Wizard recomendado nuevo

Nuevo wizard sugerido:

- `doorandoor.cobro.control.match.wizard`

Uso:

- asociar factura a control sin factura
- asociar `account.payment` a control sin pago enlazado

Campos sugeridos:

- `control_id`
- `partner_id`
- `move_id`
- `payment_id`
- `suggested_move_ids`
- `suggested_payment_ids`
- `notes`

## Acciones nuevas sugeridas

### 1. `action_mark_unidentified`

Pasa el control a una bandeja de identificacion.

### 2. `action_link_invoice`

Permite vincular factura manualmente.

### 3. `action_link_payment`

Permite vincular `account.payment` manualmente.

### 4. `action_prepare_validation`

Opcional.
Verifica que el control ya tiene toda la informacion para pasar a validacion.

## Validaciones Python sugeridas

### En create/write de `doorandoor.cobro.control`

Validar:

- `amount_reported > 0`
- si `state == validated`, exigir:
  - `move_id`
  - `payment_id`

- si hay `payment_id` y `move_id`, impedir duplicado funcional activo

### En `action_validate`

Lanzar `UserError` si:

- no hay factura asociada
- no hay pago asociado
- el pago no tiene movimiento contable
- no se encontraron lineas conciliables comunes

## Casos de prueba funcionales

### Caso 1. Factura con dos pagos parciales

Datos:

- factura de 1,000
- pago A por 400
- pago B por 600

Esperado:

- dos controles
- validado A => residual 600
- validado B => residual 0
- factura pagada

### Caso 2. Factura con un pago parcial unico

Datos:

- factura de 1,000
- pago por 300

Esperado:

- un control validado
- residual 700
- factura parcial

### Caso 3. Pago por identificar

Datos:

- control creado sin `move_id`

Esperado:

- aparece en filtro `Pagos por identificar`
- no afecta ninguna factura
- no permite validacion final

### Caso 4. Asociacion posterior

Datos:

- control sin factura
- luego se vincula `move_id`
- luego se vincula `payment_id`

Esperado:

- puede validarse
- concilia correctamente

### Caso 5. Rechazo de un pago parcial

Datos:

- factura 1,000
- control A validado por 400
- control B rechazado por 600

Esperado:

- residual 600
- total validado 400
- total rechazado 600
- factura no cerrada

### Caso 6. Evitar doble validacion del mismo pago

Datos:

- mismo `payment_id`
- misma factura
- intento de dos controles activos equivalentes

Esperado:

- bloqueo por validacion o advertencia

## Orden de implementacion recomendado

### Fase 1. Base de datos y logica

1. extender `doorandoor.cobro.control`
2. extender `account.move` con totales agregados
3. reforzar conciliacion acumulativa
4. asegurar controles sin factura o sin pago

### Fase 2. Vistas operativas

1. filtros nuevos en controles
2. resumen agregado en factura
3. smart buttons y listas

### Fase 3. Asistentes

1. wizard para asociar factura
2. wizard para asociar pago contable
3. sugerencias por cliente, monto, referencia y fecha

### Fase 4. Pulido

1. chatter y notificaciones
2. mensajes de error mas claros
3. reportes operativos y PDF

## Recomendacion tecnica final

No modelar "varios pagos dentro de un mismo control".

Modelar:

- muchos controles por factura
- un control por evidencia de pago
- asociacion flexible posterior
- cierre por conciliacion contable acumulada

Ese enfoque es mas estable, mas auditable y mas facil de mantener.
