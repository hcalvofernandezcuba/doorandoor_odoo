# DoorAndDoor - Estado de Entrega en Picking

## Objetivo

Este modulo agrega informacion de seguimiento de entrega en movimientos de inventario relacionados con ventas.

La idea es que, al revisar una entrega o un movimiento de stock, el usuario pueda ver rapidamente:

- cuanto se pidio en la venta original
- cuanto se esta entregando en ese movimiento
- cuanto queda pendiente respecto a ese movimiento

## Que hace el modulo

El modulo extiende `stock.move` y `stock.move.line` para mostrar tres columnas informativas:

- `qty_ordered`: cantidad pedida en la linea de venta original
- `qty_delivered_this`: cantidad entregada en ese movimiento
- `qty_pending`: diferencia entre pedido y entregado

Tambien agrega el campo tecnico:

- `has_sale_order`: indica si el movimiento pertenece a un picking ligado a una venta

## Como funciona

### 1. Cantidad pedida

`qty_ordered` se calcula desde `sale_line_id.product_uom_qty`.

Si el movimiento no viene de una venta, el valor es `0.0`.

### 2. Cantidad entregada

`qty_delivered_this` se calcula sumando las lineas de operacion (`move_line_ids`) del movimiento.

Para compatibilidad con distintas instalaciones de Odoo 18, el calculo intenta leer la cantidad en este orden:

1. `qty_done`
2. `quantity`
3. `product_uom_qty`

Si ninguno de esos campos existe en la linea, usa `0.0`.

### 3. Cantidad pendiente

`qty_pending` se calcula como:

`qty_ordered - qty_delivered_this`

Si no existe linea de venta asociada, el valor es `0.0`.

## Donde se ve en Odoo

Actualmente el modulo muestra esas columnas en estas vistas:

- Vista lista de movimientos de stock: `stock.view_move_tree`
- Vista formulario de movimiento de stock: `stock.view_move_form`
- Vista de operaciones detalladas: `stock.view_stock_move_line_detailed_operation_tree`

En operaciones detalladas, los campos existen en `stock.move.line` como campos `related` hacia `move_id`.

## Flujo de uso

### Caso normal

1. Se confirma una venta.
2. Odoo genera el picking y sus movimientos.
3. Al abrir los movimientos, el usuario puede comparar:
   - cantidad pedida
   - cantidad entregada
   - cantidad pendiente

### Para que sirve operativamente

- validar entregas parciales
- detectar diferencias entre pedido y entrega
- revisar rapidamente si un movimiento ya completo la cantidad esperada
- apoyar revisiones de logistica y despacho sin entrar a varios documentos

## Lo que no hace

Este modulo no:

- modifica la logica de reserva o validacion de stock
- cambia cantidades del picking
- recalcula entregas historicas fuera del movimiento mostrado
- agrega botones o automatizaciones de negocio

Es un modulo de soporte visual e informativo.

## Modelos extendidos

### `stock.move`

Campos agregados:

- `qty_ordered` - `Float`, compute, readonly
- `qty_delivered_this` - `Float`, compute, readonly
- `qty_pending` - `Float`, compute, readonly
- `has_sale_order` - `Boolean`, compute, readonly

### `stock.move.line`

Campos agregados:

- `qty_ordered` - `Float`, related a `move_id.qty_ordered`
- `qty_delivered_this` - `Float`, related a `move_id.qty_delivered_this`
- `qty_pending` - `Float`, related a `move_id.qty_pending`

## Archivos principales

- `models/stock_move.py`
  Contiene la logica compute principal.

- `models/stock_move_line.py`
  Expone los campos en operaciones detalladas por medio de `related`.

- `views/stock_move_views.xml`
  Agrega columnas en vistas de `stock.move`.

- `views/stock_picking_views.xml`
  Agrega columnas en la vista de operaciones detalladas de `stock.move.line`.

## Dependencias

- `doorandoor_sale_delivery_button`
- `stock`
- `sale`
- `sale_stock`

## Compatibilidad tecnica

Este modulo fue ajustado para una base Odoo 18 donde algunos XML IDs estandar no estan presentes.

Por esa razon se eliminaron herencias sobre vistas no disponibles en esta instalacion, entre ellas:

- `stock.view_move_picking_tree`
- `stock.view_move_tree_picking`

El modulo hoy se apoya solo en vistas que si existen en esta base.

## Historial tecnico de versiones

- `18.0.1.0.0`
  Version inicial del modulo.

- `18.0.1.0.1`
  Primer ajuste de compatibilidad sobre cantidades entregadas.

- `18.0.1.0.4`
  Enfoque robusto para leer cantidades desde `move_line_ids` con fallbacks.

- `18.0.1.0.5`
  Se agrego soporte en `stock.move.line` para que las operaciones detalladas puedan mostrar los mismos campos.

- `18.0.1.0.6`
  Se elimino la herencia a `stock.view_move_picking_tree` porque el XML ID no existe en esta base.

- `18.0.1.0.7`
  Se elimino la herencia a `stock.view_move_tree_picking` por el mismo motivo.

- `18.0.1.0.8`
  Se actualiza la documentacion funcional y tecnica del modulo para reflejar el comportamiento real instalado.

## Instalacion

1. Copiar el modulo en la carpeta `addons`.
2. Actualizar la lista de aplicaciones.
3. Instalar o actualizar `doorandoor_delivery_status`.

## Recomendaciones de prueba

- Crear una venta con una linea de producto.
- Confirmar la venta y abrir el picking generado.
- Revisar en movimientos y operaciones detalladas que aparezcan:
  - cantidad pedida
  - entregado
  - pendiente
- Validar un caso de entrega parcial y comprobar que el pendiente cambie en consecuencia.

## Autor

DoorAndDoor Team
