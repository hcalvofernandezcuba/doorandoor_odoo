# DoorAndDoor Sales New - Explicacion del flujo de orden de recogida

## Objetivo

Este documento explica como la orden de recogida encaja en el flujo actual del proyecto.

No es un proceso aislado. Es una salida operativa que ocurre despues del recorrido comercial y contable principal.

## Lugar de la orden de recogida en el flujo

La secuencia general es:

- `Ventas`
- `Cotizacion`
- `Prefactura`
- `Factura confirmada`
- `Pago total`
- `Despacho listo`
- `Orden de recogida`
- `Entrega en almacen`

## Regla de entrada

La orden de recogida no debe generarse solo porque exista una venta o una factura.

Debe existir base operativa real:

- factura vinculada
- linea con seguimiento en `fulfillment`
- picking relacionado
- cantidad autorizada y pendiente de entregar

## Relacion con las reglas de pago

Como la entrega requiere pago total:

- la recogida tambien debe respetar ese criterio
- no debe usarse como atajo para sacar mercancia sin pago completo

## Funcion operativa

La orden de recogida sirve para:

- emitir documento de retiro al cliente
- saber si la mercancia esta pendiente o lista
- dejar trazabilidad desde factura y picking
- permitir confirmacion de entrega desde almacen

## Estados operativos

La orden puede verse como:

- `new`
- `pending`
- `ready`
- `delivered`
- `cancelled`

Lectura funcional:

- `pending` si existe autorizacion pero la operacion no esta lista
- `ready` cuando la salida esta lista para retirar
- `delivered` cuando almacen confirma entrega

## Navegacion esperada

El usuario normalmente llega a la orden de recogida desde:

- la factura
- los smart buttons de operacion
- las listas operativas de ventas o inventario

## Resumen

La orden de recogida es el documento operativo final para casos donde el cliente retira en almacen. Debe respetar exactamente las mismas reglas de pago y autorizacion que el resto de la entrega.
