# DoorAndDoor Sales New - Explicacion del flujo pago -> fabricacion o despacho -> entrega

## Objetivo

Este documento explica la parte operativa que ocurre despues de creada la factura.

El punto importante es distinguir entre dos reglas vigentes del proyecto:

- la `Fabricacion` puede avanzar con pago parcial
- el `Despacho` y la `Entrega` solo avanzan con pago total

## Punto de partida

Este bloque no inicia en una factura aislada. Inicia despues de haber recorrido:

- `Ventas`
- `Cotizacion`
- `Prefactura`
- `Factura confirmada`

Solo despues entra la logica de pago y operacion.

## Regla de pago

Cuando se registra pago o conciliacion:

- el sistema recalcula la liberacion operativa
- actualiza cantidades y estado en `fulfillment`
- decide si una linea puede pasar a fabricacion o despacho

## Fabricacion con pago parcial

Si la politica y la ruta del producto lo permiten:

- un pago parcial puede liberar fabricacion
- el sistema puede crear `mrp.production`
- la linea queda trazada para seguimiento operativo

Esto permite adelantar produccion antes del pago total cuando el negocio lo necesita.

## Despacho con pago total

Para despacho y entrega la regla es mas estricta.

Solo con factura totalmente pagada debe permitirse:

- activar botones de entrega
- crear o usar la salida operativa correspondiente
- ejecutar entrega final al cliente

## Comportamiento visual esperado

En ventas:

- el boton `Entregar` o `Entregas` sigue visible
- permanece inactivo mientras no haya pago total

En servidor:

- si alguien intenta forzar la accion sin pago total, debe bloquearse

## Resultado funcional

Con esta separacion se logra:

- permitir avance de fabricacion cuando el negocio lo admite
- evitar salida indebida de mercancia antes del pago total
- mantener una regla simple y defendible para almacen

## Relacion con fulfillment

`Fulfillment` mantiene la trazabilidad entre:

- factura
- lineas comprometidas
- fabricacion
- despacho
- entrega

Es la base para saber cuanto esta:

- pendiente de pago
- liberado
- enviado a fabricacion
- enviado a stock
- entregado

## Resumen ejecutivo

La politica operativa actual es deliberadamente asimetrica:

- se puede producir con pago parcial
- no se puede despachar ni entregar sin pago total

Ese es el criterio que hoy debe explicarse y validarse con cualquier usuario operativo del sistema.
