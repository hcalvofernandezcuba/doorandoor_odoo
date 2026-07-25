# DoorAndDoor Sales New - Puntos Pendientes para Reunion con Cliente

Fecha de corte documental: 2026-07-25

Este documento resume los frentes que quedan pendientes de definicion o validacion con el cliente para continuar el proyecto sin perder contexto.

## 1. Produccion y Fabricacion

### Punto a revisar

Definir y validar el flujo completo de produccion a partir de la liberacion por pago.

### Aspectos a confirmar

- si la fabricacion parcial se mantiene como regla definitiva
- cuando debe crearse la orden de fabricacion
- si la fabricacion debe dispararse automaticamente o por accion manual
- como debe reflejarse el avance de produccion en factura, venta y entrega
- que estados o alertas necesita ver el cliente durante ese proceso

### Objetivo de la reunion

Cerrar el criterio funcional final del flujo de fabricacion para luego validar si hace falta ajuste tecnico adicional.

## 2. Entregas y Hanger

### Punto a revisar

Validar el flujo operativo de entregas en almacen con hanger.

### Aspectos a confirmar

- como se prepara la mercancia cuando el producto pasa a hanger
- quien marca el cambio de estado operativo
- si hanger debe verse como estado, ubicacion, etiqueta o parte del documento de entrega
- como se confirma la entrega final al cliente
- que trazabilidad debe quedar guardada

### Objetivo de la reunion

Definir con precision el flujo real de almacen para que la implementacion no quede basada en supuestos.

## 3. Metodos de Pago

### Punto a revisar

Definir como deben manejarse y mostrarse los metodos de pago dentro del flujo comercial y contable.

### Aspectos a confirmar

- cuales metodos de pago necesita usar el cliente
- si deben mostrarse solo internamente o tambien impresos en factura
- si una factura puede tener uno o varios metodos de pago visibles
- si el metodo debe capturarse antes del pago, al registrar el pago o en ambos momentos
- si algun metodo cambia reglas de liberacion, despacho o fabricacion

### Objetivo de la reunion

Fijar el comportamiento funcional antes de hacer cambios en vistas, reportes o logica de negocio.

## 4. Politicas Opcionales en Factura

### Punto a revisar

Definir que politicas comerciales o legales deben poder aparecer opcionalmente en la factura.

### Aspectos a confirmar

- cuales politicas exactas deben existir
- si son politicas globales o seleccionables por factura
- quien decide cuando se imprimen
- si deben aparecer en pantalla, en PDF o en ambos
- si el usuario debe poder activarlas o desactivarlas manualmente

### Objetivo de la reunion

Cerrar el criterio de impresion opcional para evitar retrabajo en reportes.

## Propuesta de orden para tratar en la reunion

1. Produccion y fabricacion
2. Entregas y hanger
3. Metodos de pago
4. Politicas opcionales en factura

## Resultado esperado de la reunion

Al cerrar esta reunion deberia quedar definido:

- que puntos requieren cambio funcional real
- que puntos son solo ajuste visual o documental
- que reglas deben implementarse primero
- que elementos quedan congelados hasta nueva decision del cliente
