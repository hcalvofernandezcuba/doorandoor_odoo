# DoorAndDoor Sales New - Guia de presentacion y capacitacion del flujo actual

## Objetivo del documento

Este documento sirve para presentar y capacitar sobre el flujo comercial vigente de DoorAndDoor.

La version actual ya no debe explicarse como un proceso que arranca en facturacion. El punto de entrada del usuario es `Ventas`, y desde ahi se navega a las vistas necesarias hasta cerrar el ciclo operativo.

## Mensaje principal

El flujo operativo actual es:

- `Cotizacion`
- `Prefactura`
- `Factura confirmada`
- `Pago`
- `Fabricacion o despacho`
- `Entrega o recogida`

La regla general es que todo inicia en `Ventas`.

## Resumen ejecutivo para conversacion con cliente

Hoy el sistema permite:

- crear cotizaciones desde ventas
- mantener la cotizacion sin numero definitivo hasta validarla
- crear una prefactura al validar la cotizacion
- reservar stock por 24 horas en la prefactura
- imprimir o enviar la prefactura antes de confirmar
- publicar la factura automaticamente al confirmar la prefactura
- mantener fabricacion con pago parcial
- bloquear despacho y entrega hasta pago total
- seguir todo el proceso desde ventas y facturacion con smart buttons relacionados

## Flujo para explicar en demo

### 1. Entrar en `Ventas`

Este es el punto de inicio del usuario comercial.

Desde aqui se crea la `Cotizacion`.

### 2. Crear `Cotizacion`

Comportamiento esperado:

- la cotizacion se crea en estado inicial
- no toma numero definitivo hasta validarla
- el vendedor puede revisar cliente, productos, stock y precios

### 3. Validar cotizacion

Al pulsar `Validar cotizacion` ocurre esto:

- se asigna el numero `SO`
- la cotizacion queda registrada
- se crea la `Prefactura`
- la prefactura toma la referencia de la `SO`

### 4. Trabajar la `Prefactura`

La prefactura sirve para:

- reservar inventario por 24 horas
- imprimir documento comercial
- enviarlo al cliente
- revisar condiciones antes de convertirlo en factura final

Reglas:

- si vence la reserva, la prefactura se marca vencida
- el flujo vuelve funcionalmente a cotizacion
- la renovacion manual solo se permite para el mismo cliente

### 5. Confirmar prefactura

Al confirmar la prefactura:

- se publica la `Factura`
- se confirma la venta relacionada
- el stock queda comprometido de forma firme

### 6. Gestionar pago y operacion

Reglas acordadas:

- `Fabricacion` con pago parcial
- `Despacho` con pago total
- `Entrega` con pago total

Consecuencia en pantalla:

- los botones de entrega siguen visibles
- permanecen inactivos mientras la factura no este totalmente pagada

### 7. Navegar entre vistas relacionadas

Desde ventas y facturacion el usuario puede entrar a:

- `Sale Order`
- `Fulfillment`
- `Dispatches`
- `Manufacturing`
- `Releases`
- `Pickup Orders`

## Que debe mostrar la demo

- una cotizacion creada desde ventas
- el momento de `Validar cotizacion`
- la prefactura creada con sus botones `Imprimir` y `Enviar`
- la reserva temporal vigente
- la confirmacion de prefactura hacia factura
- la factura con `Total de Impuestos`
- el boton de entrega visible pero inactivo sin pago total
- el cambio de comportamiento despues del pago total

## Decisiones funcionales cerradas

- la cotizacion solo toma numero al validarla
- la prefactura toma el numero de la `SO`
- confirmar prefactura publica factura automaticamente
- si vence la reserva de 24 horas, la prefactura se considera vencida y el flujo vuelve a cotizacion
- la reserva puede renovarse manualmente solo para el mismo cliente
- la fabricacion puede permitirse con pago parcial
- el despacho y la entrega requieren pago total

## Mensaje de cierre recomendado

El proyecto ya tiene definido el recorrido operativo principal para ventas. La discusion con cliente debe concentrarse ahora en ajustes finos de interfaz, politicas de excepcion y detalles de operacion, no en la estructura base del flujo.
