# DoorAndDoor Sales New - Explicacion del flujo actual ventas -> cotizacion -> prefactura -> factura

## Objetivo

Este documento explica el flujo comercial actual tal como debe entenderse hoy en el proyecto.

Ya no se debe presentar como un proceso que nace en factura. El punto de arranque del usuario es `Ventas`.

## Secuencia general

El flujo vigente es este:

1. `Cotizacion`
2. `Validar cotizacion`
3. `Prefactura`
4. `Confirmar prefactura`
5. `Factura confirmada`
6. `Pago`
7. `Fabricacion, despacho, entrega o recogida`

## Paso 1 - Cotizacion

La cotizacion vive en `sale.order`.

En esta etapa:

- el vendedor selecciona cliente y productos
- revisa stock visible
- revisa precios y condiciones
- el documento aun no debe comportarse como registro comercial definitivo

Regla acordada:

- la cotizacion solo toma numero al validarla

## Paso 2 - Validar cotizacion

La accion `Validar cotizacion` hace tres cosas clave:

- asigna el numero `SO`
- registra la cotizacion
- crea la `Prefactura`

Con esto el proceso comercial deja de quedarse en una simple propuesta y pasa a un documento que aparta inventario temporalmente.

## Paso 3 - Prefactura

La prefactura se implementa sobre `account.move` en estado `draft`.

Su funcion es:

- reservar stock por 24 horas
- permitir impresion y envio al cliente
- mantener una vista de documento previa a la factura final

Comportamiento esperado:

- la prefactura toma la referencia de la `SO`
- puede abrirse desde la venta
- muestra las acciones necesarias para trabajo comercial

## Paso 4 - Reserva temporal de 24 horas

Mientras la prefactura este vigente:

- el stock visible debe descontar esa reserva
- se reduce el riesgo de doble venta

Si la reserva vence:

- la prefactura se considera vencida
- el flujo vuelve a cotizacion
- el inventario reservado se libera

Renovacion:

- existe renovacion manual
- solo procede para el mismo cliente

## Paso 5 - Confirmar prefactura

Al confirmar la prefactura:

- se publica la factura automaticamente
- la venta relacionada queda confirmada
- la reserva temporal pasa a compromiso firme

Aqui se cierra la parte comercial previa y se abre la parte formal contable y operativa.

## Paso 6 - Factura confirmada

La factura confirmada es el documento formal del proceso.

Desde ella se puede navegar a:

- `Sale Order`
- `Fulfillment`
- `Dispatches`
- `Manufacturing`
- `Releases`
- `Pickup Orders`

La factura tambien refleja mejor el stock comprometido real y mantiene el resumen fiscal con la etiqueta fija `Total de Impuestos`.

## Paso 7 - Pago y operacion

La politica vigente del proyecto es:

- `Fabricacion` con pago parcial
- `Despacho` con pago total
- `Entrega` con pago total

Por eso, aunque la orden o la factura ya existan:

- los botones de entrega pueden seguir visibles
- no deben quedar activos sin pago total

## Relacion con fulfillment

`Fulfillment` sigue siendo la capa de seguimiento operativo por linea.

Su papel en el flujo actual es:

- mantener trazabilidad entre venta, prefactura y factura
- controlar cantidades comprometidas
- sostener liberacion, despacho, fabricacion y entrega
- servir de base para ordenes de recogida

## Lectura funcional rapida

La forma simple de explicarlo es esta:

- ventas inicia el proceso
- cotizacion prepara la propuesta
- validacion crea prefactura
- prefactura reserva por 24 horas
- confirmacion publica factura
- pago define que operacion puede ejecutarse

## Conclusion

El cambio clave del proyecto es que el proceso comercial ya no depende de comenzar en facturacion. Ahora nace en `Ventas`, y desde ahi enlaza todos los documentos y vistas necesarias hasta la operacion final.
