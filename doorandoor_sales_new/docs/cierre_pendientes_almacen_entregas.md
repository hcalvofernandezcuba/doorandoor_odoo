# Cierre de pendientes - Almacen y entregas

Fecha base: 27 de julio de 2026

## Objetivo

Dejar una guia corta y operativa para cerrar los pendientes funcionales del flujo de almacen, pickup order, picking y entrega final.

## Tabla corta: estado actual vs estado esperado

| Punto | Como esta hoy | Como debe quedar | Funcion o area a revisar |
| --- | --- | --- | --- |
| Recepcion | Usa flujo estandar de `stock.picking` sin capa adicional propia | Confirmar si solo se trabajara con recepcion estandar o si se necesita vista operativa propia para almacen | `stock.picking` / operacion real |
| Reserva por prefactura | Reserva stock por 24h y limpia prefacturas obsoletas a las 48h | Mantener esta regla y verificar que almacen entienda que una prefactura no es salida autorizada | `account.move._ddsn_release_expired_preinvoice_reservations()` |
| Pago parcial con fabricacion | Puede liberar fabricacion parcial si la linea va a `ready_mrp` | Mantenerlo y validar que el equipo de almacen no genere entrega por este evento | `account.move._ddsn_sync_mrp_fulfillment_documents()` |
| Pago parcial con stock | No deberia liberar salida de stock | Confirmar que ninguna accion manual permita crear entrega o pickup order antes del pago total | `account.move._ddsn_sync_stock_fulfillment_documents()` |
| Picking de salida | Se crea cuando la factura ya puede liberar stock | Confirmar criterio exacto de nacimiento y si siempre debe nacer antes del pickup order | flujo de `account.move` hacia `stock.picking` |
| Pickup Order | Nace cuando hay `picking_id` y cantidad lista para pickup | Reforzar en codigo que solo pueda crearse con factura totalmente pagada | `account.move._ddsn_ensure_pickup_orders()` |
| Estado del Pickup Order | Usa `new`, `pending`, `ready`, `delivered`, `cancelled` segun picking | Validar si esos estados operativos son suficientes para el cliente | `doorandoor.pickup.order` |
| Entrega final | Puede marcarse entregada desde pickup order | Confirmar quien hace el cierre y si `delivered` es cierre interno o cierre al cliente | `doorandoor.pickup.order.action_mark_delivered()` |
| Operaciones para almacen | Ya existen `Process Flows` y `Process Tasks` | Automatizar la creacion de tareas desde ventas/factura/picking para que no dependan de carga manual | `doorandoor_process_control` + disparadores |
| En ruta | Existe en control de procesos, no en pickup order | Definir si la salida de almacen pasa primero por `En ruta` antes de `Cerrado` en todos los casos | `doorandoor_process_control` |

## Pendientes concretos para cierre

1. Reforzar por codigo que el `Pickup Order` solo se cree con factura totalmente pagada.
2. Confirmar si el `Pickup Order` nace automaticamente al pago total o por accion manual del usuario despues del pago total.
3. Confirmar si el `picking` siempre debe existir antes del `Pickup Order`.
4. Confirmar que almacen no use prefactura como documento valido de salida.
5. Definir el criterio exacto de cierre:
   - `Entregado`
   - `En ruta`
   - `Cerrado`
6. Automatizar la tarea de almacen en `Operaciones` para que el flujo no dependa de crear procesos manualmente.
7. Validar impresion final de:
   - picking
   - pickup order
   - labels asociados

## Orden recomendado de revision

1. Factura con producto de stock y pago parcial.
   Resultado esperado: no crear pickup order ni salida.
2. Factura con producto de stock y pago total.
   Resultado esperado: liberar salida y permitir pickup order.
3. Factura con producto fabricable y pago parcial.
   Resultado esperado: crear MO, pero no pickup order final de entrega.
4. Producto fabricado ya terminado y factura totalmente pagada.
   Resultado esperado: permitir salida de almacen y pickup order.
5. Cierre de entrega.
   Resultado esperado: trazabilidad clara entre almacen, en ruta y cierre.

## Criterio de cierre funcional

Se considerara cerrado este bloque cuando:

- el equipo de almacen tenga claro que documento usa en cada etapa
- el pickup order solo nazca con pago total
- la fabricacion con pago parcial no permita entrega prematura
- operaciones reciba tareas automaticamente
- el flujo `stock -> pago -> picking -> pickup order -> entrega` se pueda probar de punta a punta sin ambiguedad
