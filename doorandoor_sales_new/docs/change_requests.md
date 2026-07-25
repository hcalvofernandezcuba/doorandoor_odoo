# DoorAndDoor Sales New - Solicitudes de Cambio

## Formato sugerido

### CR-0001

- Fecha:
- Solicitado por:
- Descripcion:
- Impacto funcional:
- Impacto tecnico:
- Estado:

## CR-0001

- Fecha:
  2026-06-09

- Solicitado por:
  Cliente DoorAndDoor

- Descripcion:
  Mejorar y ampliar el flujo comercial y operativo despues de la fase base implementada.

- Impacto funcional:
  Abarca cotizacion, descuentos, impresion, stock, despacho y produccion.

- Impacto tecnico:
  Requiere nuevas extensiones sobre ventas, clientes, reportes y planeacion productiva.

- Estado:
  En analisis

## CR-0002

- Fecha:
  2026-06-09

- Solicitado por:
  Equipo del proyecto DoorAndDoor

- Descripcion:
  Iniciar la Fase A con stock visible en cotizacion para uso inmediato del equipo comercial.

- Impacto funcional:
  Mejora la toma de decision comercial antes de facturar.

- Impacto tecnico:
  Requiere extender vistas y logica de `sale.order.line` con informacion de disponibilidad.

- Estado:
  Implementado

## CR-0003

- Fecha:
  2026-06-10

- Solicitado por:
  Equipo del proyecto DoorAndDoor

- Descripcion:
  Iniciar la base de bonificaciones automaticas por cliente en cotizacion.

- Impacto funcional:
  Permite precargar descuentos comerciales simples desde la ficha del cliente.

- Impacto tecnico:
  Requiere extender `res.partner`, `sale.order.line` y la vista del cliente.

- Estado:
  Implementado

## CR-0004

- Fecha:
  2026-06-11

- Solicitado por:
  Equipo del proyecto DoorAndDoor

- Descripcion:
  Extender la bonificacion comercial para soportar grupos de cliente y definir prioridad frente al descuento manual.

- Impacto funcional:
  La cotizacion puede aplicar descuentos comerciales mas consistentes sin perder control manual del vendedor.

- Impacto tecnico:
  Requiere extender `res.partner.category`, `sale.order.line` y vistas de clientes/cotizacion.

- Estado:
  Implementado y validado en entorno

## CR-0005

- Fecha:
  2026-06-12

- Solicitado por:
  Cliente DoorAndDoor

- Descripcion:
  Crear un documento y flujo de orden de recogida en almacen, imprimible desde facturacion y trazable despues desde ventas e inventario.

- Impacto funcional:
  Permite entregar al cliente un documento de recogida y controlar el estado posterior de la entrega en almacen.

- Impacto tecnico:
  Requiere un modelo nuevo con lineas, estados, vistas de lista, accion desde factura, reporte imprimible y visibilidad segmentada entre ventas e inventario.

- Estado:
  Implementado y validado en entorno

## CR-0006

- Fecha:
  2026-06-19

- Solicitado por:
  Cliente DoorAndDoor

- Descripcion:
  Evitar que una misma salida fisica de mercancia quede duplicada en historial cuando el flujo puede dispararse tanto desde la venta como desde la factura.

- Impacto funcional:
  La entrega ya existente de la venta debe reutilizarse desde facturacion en lugar de crear otra operacion paralela para la misma mercancia.

- Impacto tecnico:
  Requiere reutilizar `stock.picking` abiertos de la `sale.order` asociada y evitar crear `stock.move` duplicados para la misma `sale_line_id` dentro del mismo picking.

- Estado:
  Implementado y pendiente de validacion final en entorno Docker Odoo

## CR-0007

- Fecha:
  2026-06-19

- Solicitado por:
  Cliente DoorAndDoor

- Descripcion:
  Evitar inconsistencias entre facturas pagadas o parcialmente pagadas y ajustes manuales de inventario que reduzcan el stock fisico sin respetar las unidades ya comprometidas por cobro.

- Impacto funcional:
  El usuario no debe poder dejar el stock por debajo de las cantidades ya liberadas por pago mientras esas unidades sigan pendientes de entrega.

- Impacto tecnico:
  Requiere interceptar los ajustes manuales de `stock.quant`, calcular cantidades bloqueadas por `doorandoor.fulfillment.line` y rechazar cualquier ajuste que deje el inventario por debajo de las unidades liberadas no entregadas.

- Estado:
  Implementado y validado en entorno Docker Odoo

- Nota de contexto:
  Durante la validacion aparecieron productos migrados desde Zoho con tipo consumible o servicio. Ese comportamiento se reconoce como condicion heredada de datos migrados y ya fue considerado en la preparacion de la base de produccion.

## CR-0008

- Fecha:
  2026-06-21

- Solicitado por:
  Cliente DoorAndDoor

- Descripcion:
  Incorporar codigos de barra escaneables en reportes impresos clave y retirar montos de los documentos operativos de entrega para uso de almacen.

- Impacto funcional:
  Facturas, pickings y ordenes de recogida pueden identificarse por escaneo y los documentos de entrega quedan enfocados en items y cantidades.

- Impacto tecnico:
  Requiere agregar una logica comun de barcode y QR para modelos documentales, extender templates QWeb de reportes y simplificar el reporte de orden de recogida quitando importes y total.

- Estado:
  Implementado y validado en carga de modulo Docker Odoo

## CR-0009

- Fecha:
  2026-06-24

- Solicitado por:
  Cliente DoorAndDoor

- Descripcion:
  Reservar inventario temporalmente al crear una prefactura, manteniendo la reserva durante 24 horas y liberandola automaticamente si no se convierte en factura publicada.

- Impacto funcional:
  El equipo comercial puede emitir una prefactura imprimible que sostenga una reserva temporal visible para no vender dos veces la misma existencia mientras la prefactura sigue vigente.

- Impacto tecnico:
  Requiere extender `account.move` en estado borrador, etiquetar el PDF como `Prefactura`, agregar vencimiento de reserva, tarea automatica de liberacion y descuento de esa reserva temporal en las columnas de stock visibles.

- Estado:
  Implementado y validado en entorno Docker Odoo
