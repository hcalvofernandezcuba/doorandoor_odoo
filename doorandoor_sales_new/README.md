# DoorAndDoor Sales New

## Objetivo

Este modulo centraliza el flujo comercial y operativo actual de DoorAndDoor.

El proceso vigente inicia en `Ventas` con una `Cotizacion`, continua con una `Prefactura` reservando inventario por 24 horas y termina en una `Factura` confirmada que despues sigue las reglas de pago, fabricacion, despacho y entrega.

## Flujo funcional actual

1. `Ventas -> Cotizacion`
   - el usuario crea la cotizacion desde ventas
   - la cotizacion nace sin numero visible final
   - la cotizacion no debe aparecer como documento comercial definitivo hasta validarla

2. `Validar cotizacion`
   - se asigna el numero `SO`
   - la cotizacion queda registrada comercialmente
   - se crea la `Prefactura`
   - la `Prefactura` toma la referencia de la `SO`

3. `Prefactura`
   - vive sobre `account.move` en `draft`
   - reserva stock por 24 horas
   - permite `Imprimir` y `Enviar`
   - si vence la reserva, la prefactura se marca vencida y el flujo vuelve a cotizacion
   - se permite renovacion manual solo para el mismo cliente

4. `Confirmar prefactura`
   - publica la factura automaticamente
   - confirma la venta relacionada
   - convierte la reserva temporal en compromiso firme del stock

5. `Factura confirmada`
   - mantiene trazabilidad con cotizacion, prefactura y venta
   - muestra stock comercialmente comprometido
   - mantiene visibles smart buttons de operacion

6. `Pago y operacion`
   - fabricacion permitida con pago parcial
   - despacho permitido solo con pago total
   - los botones de entrega permanecen visibles pero inactivos hasta pago total

7. `Entrega y recogida`
   - el flujo puede terminar en despacho tradicional o en orden de recogida
   - las ordenes de recogida siguen trazadas desde factura

## Punto de entrada para usuario

El recorrido funcional esperado se navega asi:

- entrar en `Ventas`
- crear `Cotizacion`
- validar cotizacion para crear `Prefactura`
- abrir `Prefactura`
- imprimir o enviar prefactura
- confirmar prefactura para crear `Factura`
- desde la factura navegar a:
  - `Sale Order`
  - `Fulfillment`
  - `Dispatches`
  - `Manufacturing`
  - `Releases`
  - `Pickup Orders`

## Reglas operativas vigentes

- la cotizacion solo toma numero al validarla
- la prefactura toma el numero de la `SO`
- la reserva temporal dura 24 horas
- al vencer la reserva, el flujo vuelve a cotizacion
- la renovacion manual de reserva aplica solo al mismo cliente
- la factura comprometida descuenta stock visible sin esperar al pago
- la fabricacion puede arrancar con pago parcial
- el despacho y la entrega solo avanzan con pago total

## Relacion con otros modulos

- `doorandoor_delivery_status`
  aporta apoyo visual sobre estados de movimientos y operaciones

- `doorandoor_sale_delivery_button`
  controla que los botones de entrega solo queden activos con factura totalmente pagada

- `doorandoor_tax_state`
  apoya el manejo fiscal por estado y la consistencia del bloque de impuestos en documentos

## Estructura principal

- `models/sale_order.py`
  controla registro de cotizacion, numeracion, prefactura y flujo comercial

- `models/account_move.py`
  controla prefactura, factura, reserva temporal, publicacion y trazabilidad operativa

- `models/account_move_line.py`
  enlaza lineas de factura con lineas de venta y cumplimiento

- `models/fulfillment_line.py`
  controla seguimiento operativo por linea

- `models/pickup_order.py`
  controla ordenes de recogida y su estado

- `views/sale_order_views.xml`
  adapta ventas al flujo `Cotizacion -> Prefactura -> Factura`

- `views/account_move_views.xml`
  adapta factura/prefactura, botones, smart buttons y resumen de totales

## Estado funcional actual

El modulo ya cubre:

- cotizacion sin numero hasta validarla
- validacion de cotizacion creando prefactura
- prefactura con reserva de 24 horas
- renovacion manual de reserva
- publicacion automatica de factura al confirmar prefactura
- trazabilidad entre cotizacion, prefactura, factura y venta
- stock visible ajustado por reservas y compromisos reales
- fabricacion con pago parcial
- despacho con pago total
- botones de entrega visibles pero bloqueados hasta pago total
- ordenes de recogida trazadas desde factura
- etiquetas de impuestos unificadas como `Total de Impuestos`

## Historial de desarrollo reciente

### 18.0.1.0.49

- Se implementa la base tecnica del flujo `Cotizacion -> Prefactura -> Factura`.
- Validar cotizacion crea prefactura reservada por 24 horas.
- Confirmar prefactura publica factura y confirma la venta.

### 18.0.1.0.50

- Se corrige `action_post()` para esta base de Odoo 18 usando el recordset original en lugar del valor devuelto por `super()`.

### 18.0.1.0.51

- Se ajusta el control del boton de entregas para que solo se habilite con pago total de la factura vinculada.

### 18.0.1.0.52

- Se unifica la etiqueta visual de impuestos en ventas y facturacion usando `Total de Impuestos`.

### 18.0.1.0.53

- Se actualiza la documentacion funcional y del website para reflejar que el flujo vigente inicia en `Ventas` y navega por `Cotizacion -> Prefactura -> Factura -> Pago -> Operacion`.

## Base de validacion funcional

Base usada recientemente para las pruebas operativas:

- `pruebas`
