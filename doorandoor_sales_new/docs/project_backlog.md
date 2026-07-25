# DoorAndDoor Sales New - Backlog del Proyecto

## Objetivo

Este archivo concentra el estado funcional del modulo `doorandoor_sales_new`, el alcance ya implementado, las tareas pendientes y el orden recomendado para continuar las mejoras solicitadas por el cliente.

## Estado actual del modulo

Actualmente el modulo cubre este flujo base:

1. Factura publicada
   - crea `sale.order` en borrador
   - crea lineas de venta
   - crea lineas internas de cumplimiento

2. Pago aplicado
   - calcula liberacion segun politica
   - actualiza importes y estados en cumplimiento
   - crea bitacora de liberacion

3. Ruta stock
   - crea `stock.picking`
   - crea `stock.move`
   - enlaza el despacho a la factura

4. Ruta fabricacion
   - crea `mrp.production`
   - confirma la orden de fabricacion
   - al terminar produccion prepara el despacho de salida

5. Entrega final
   - al validar picking actualiza cantidades entregadas
   - recalcula estado de cumplimiento
   - mantiene trazabilidad entre factura, venta, produccion y entrega

6. Reportes
   - firmas en factura
   - firmas en pedido de venta
   - firmas en orden de entrega
   - numero de orden de despacho visible en factura impresa

## Cambios ya implementados

- Generacion de `sale.order` desde factura.
- Sincronizacion manual `Sync Fulfillment`.
- Politicas de liberacion por pago.
- Pestañas de cumplimiento y configuracion en factura.
- Automatizacion de despacho por stock.
- Automatizacion de orden de fabricacion.
- Enlace produccion terminada -> picking de salida.
- Actualizacion de entrega al validar picking.
- Mejoras visuales de la factura.
- Traducciones base al español latino.
- Stock visible en cotizacion.
- Bonificaciones por cliente y por grupo con prioridad base.
- Ajuste de impresion de impuestos en factura.
- Visibilidad de stock por almacen en lineas de factura.
- Ordenes de recogida en almacen con lista, estados y reporte.
- Foto visible y editable en ficha del cliente.
- Historial de desarrollo versionado en `README.md`.

## Pendientes provenientes de reunion con cliente

### 1. Cotizacion con informacion de stock

Objetivo:
Mostrar existencias al momento de cotizar, no esperar a la facturacion.

Posibles tareas:
- mostrar disponibilidad por producto en `sale.order.line`
- mostrar disponibilidad por almacen
- decidir si se muestra:
  - stock total
  - stock por almacen principal
  - stock por almacen del pedido
  - proxima disponibilidad
- definir si la cotizacion solo informa o tambien bloquea

Prioridad:
Alta

Estado actual:
Implementado y extendido al flujo de facturacion.
Ya existe:
- disponibilidad por producto en `sale.order.line`
- lectura por almacen en cotizacion
- visibilidad equivalente en lineas de factura

Pendiente futuro:
- definir si la visualizacion debe bloquear o solo informar
- definir criterio final de proxima disponibilidad
- endurecer la decision operativa por almacen

Estado de avance al corte:
Congelado en estos pendientes hasta nueva definicion funcional del cliente.

### 2. Bonificaciones y descuentos por cliente

Objetivo:
Aplicar reglas comerciales diferenciadas segun cliente o grupo.

Posibles tareas:
- agregar bonificacion global en `res.partner`
- agregar grupo de bonificacion
- crear reglas por categoria o grupo comercial
- aplicar bonificacion automaticamente en cotizacion
- permitir prioridad entre:
  - bonificacion del cliente
  - bonificacion por grupo
  - ajuste manual

Prioridad:
Alta

Estado actual:
Implementado en su version base.
Ya existe:
- bonificacion por cliente
- bonificacion por grupo de cliente
- aplicacion automatica en cotizacion
- prioridad base:
  - descuento manual
  - bonificacion del cliente
  - bonificacion del grupo

Pendiente futuro:
- reglas por categoria de producto
- grupos comerciales mas especializados
- prioridades configurables

### 3. Ajustes de impresion de documentos

Objetivo:
Completar y refinar la salida impresa para clientes y operaciones.

Posibles tareas:
- revisar texto del total de impuestos
- mostrar impuesto agrupado y total de impuesto en el cuadro de totales
- definir si algunas partidas se ocultan solo al imprimir
- extender el mismo criterio visual a otros reportes si hace falta

Prioridad:
Media

Estado actual:
Implementado parcialmente.
Ya existe:
- factura impresa sin impuestos por item
- total fiscal agrupado como `Total de impuestos`

Pendiente futuro:
- ocultar otras partidas solo al imprimir si el cliente lo solicita
- extender el mismo criterio a otros reportes si hace falta

### 4. Reglas mas estrictas para despacho

Objetivo:
Controlar mejor cuando se puede liberar y despachar.

Posibles tareas:
- reforzar la regla de no despachar sin pago
- revisar comportamiento con pago parcial
- decidir politica si hay varios almacenes
- decidir si reserva primero del almacen principal o del que tenga stock

Prioridad:
Alta

Estado actual:
Implementado parcialmente segun ultima validacion.
Ya existe:
- despacho por stock solo con factura totalmente pagada
- fabricacion permitida con pago parcial
- produccion terminada no genera picking de salida si la factura aun no esta totalmente pagada

Pendiente futuro:
- definir comportamiento exacto con varios almacenes
- definir reserva por almacen principal o por almacen con stock
- revisar si debe existir alguna excepcion operativa controlada

Estado de avance al corte:
Congelado hasta que el cliente confirme la politica exacta por almacen.

### 5. Foto en ficha de cliente

Objetivo:
Agregar soporte visual en el formulario del cliente.

Posibles tareas:
- usar `image_1920` si el cliente no necesita un campo extra
- crear un bloque visual en la ficha
- decidir si se usara tambien en reportes o solo en pantalla

Prioridad:
Media

Estado actual:
Implementado.
Ya existe:
- uso de `image_1920` en la ficha del cliente
- foto visible y editable en `res.partner`

### 6. Produccion avanzada

Objetivo:
Ampliar la parte industrial mas alla de la orden basica.

Posibles tareas:
- vincular producto con linea o sistema de produccion
- mostrar proyeccion de produccion
- generar vista o resumen de demanda proyectada
- definir si la proyeccion sale desde factura, venta o tablero propio

Prioridad:
Media

### 7. Orden de recogida en almacen

Objetivo:
Emitir y controlar un documento operativo de recogida desde facturacion, con seguimiento posterior en ventas e inventario.

Posibles tareas:
- crear modelo propio de orden de recogida ligado a la factura
- generar ordenes desde facturacion para productos pagados y listos para recoger
- mostrar almacen designado para la entrega
- imprimir el documento para el cliente desde la lista de reportes de factura
- guardar las ordenes en una vista de lista con estados
- permitir seguimiento posterior desde ventas
- hacer visible la misma lista desde inventarios
- permitir que almacen marque la orden como entregada al cliente
- separar la vista operativa:
  - ventas:
    - nuevas
    - pendientes
    - listas
  - inventario:
    - entregadas
- agregar reporte reimprimible desde la orden

Prioridad:
Alta

Estado actual:
Implementado en su version base.
Ya existe:
- modelo propio de orden de recogida
- creacion desde factura
- lista con estados
- visibilidad desde ventas e inventario
- reporte imprimible y reimprimible
- cambio manual a entregada por almacen

## Pendientes de definicion

Estos puntos necesitan decision funcional antes de implementarse:

- que significa exactamente "ocultar una partida" en factura
- como se define el grupo de bonificacion
- que regla exacta debe usarse para stock por almacen
- que significa "ver solo lo que tenga fecha mas proxima" en entregas
- a que se refiere exactamente "linea de produccion" en producto:
  - BoM
  - centro de trabajo
  - ruta
  - linea interna del negocio

## Regla base ya definida para recogida

Para esta fase se toma como regla operativa inicial:

- una linea puede entrar en orden de recogida si:
  - tiene producto
  - tiene picking asociado
  - el picking no esta cancelado
  - existe cantidad liberada no entregada

- una orden queda `ready` para recoger si:
  - el picking esta en estado `assigned` o `done`

- una orden queda `pending` si:
  - existe la linea autorizable
  - pero el picking aun no esta en condicion operativa de entrega

## Orden recomendado de trabajo

### Fase A

- cotizacion con stock visible
- comprobacion de stock en tiempo de cotizar

### Fase B

- bonificaciones por cliente y por grupo
- aplicacion automatica en cotizacion

### Fase C

- ajustes de impresion de impuestos y partidas
- afinacion de documentos impresos

### Fase D

- proyeccion de produccion
- vinculo producto -> linea o sistema de produccion

### Fase E

- orden de recogida en almacen
- listado y estados operativos
- visibilidad en ventas e inventario
- reporte imprimible y reimprimible

## Riesgos y consideraciones

- algunas mejoras tocan vistas estandar de venta, factura y stock al mismo tiempo
- las reglas de descuentos y stock deben quedar bien definidas para no generar conflictos con el flujo ya automatizado
- si el cliente cambia politicas por almacen o por tipo de producto, convendra mover ciertas reglas a configuraciones seleccionables

## Siguiente paso recomendado

No avanzar sobre nuevas reglas de negocio hasta que el cliente confirme los puntos abiertos.

Al reanudar, retomar primero:

- comportamiento por almacen
- criterio de stock visible en facturacion y cotizacion
- siguientes decisiones de produccion avanzada

## Ejecucion actual

La fase activa del proyecto queda en:

- validacion operativa con cliente
  - flujo de facturacion
  - recogida en almacen
  - ajustes finos sobre reportes y operacion
