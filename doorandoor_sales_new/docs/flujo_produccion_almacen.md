# DoorAndDoor Sales New - Flujo de Produccion con Almacen Origen y Destino

Fecha de corte documental: 2026-07-25

## Objetivo

Definir el flujo operativo cuando una venta incluye un producto con ruta de fabricacion y el cliente puede cambiar el almacen final de entrega aun despues de creada la orden de manufactura.

## Flujo funcional

### 1. Venta

- El equipo de `Ventas` registra una venta desde un almacen comercial determinado.
- Si el producto vendido tiene ruta de `fabricacion`, el sistema debe crear automaticamente la `MO`.

### 2. Creacion de la orden de manufactura

Al crear la `MO`, deben quedar visibles estos dos datos:

- `Almacen origen`
  - corresponde al almacen comercial desde el cual nacio la necesidad de venta
  - se carga automaticamente desde la venta o factura relacionada
  - queda visible para contexto operativo

- `Almacen destino de entrega`
  - corresponde al almacen al que debe llegar el producto terminado antes del despacho al cliente
  - puede inicializarse con el mismo almacen de origen
  - debe quedar editable porque el cliente puede cambiar el almacen final de entrega

### 3. Produccion terminada

- Cuando la `MO` termina, el sistema no debe despachar directamente al cliente desde manufactura.
- Primero debe respetar el `almacen destino de entrega` configurado en la orden.

### 4. Movimiento interno al almacen destino

Al cerrar la produccion:

- el sistema debe crear una `transferencia interna`
- esa transferencia mueve el producto terminado desde la ubicacion de salida de manufactura hacia la ubicacion de stock del `almacen destino de entrega`
- esa operacion deja trazabilidad del movimiento fisico en inventario

### 5. Despacho al cliente

Despues de generar el movimiento interno:

- el sistema debe crear la `orden de despacho`
- esa orden debe salir desde el `almacen destino de entrega`
- el despacho queda entonces alineado con el ultimo almacen definido para entrega al cliente

## Reglas funcionales clave

- la `MO` siempre muestra el `almacen origen`
- la `MO` permite editar el `almacen destino de entrega`
- si el cliente cambia el almacen de entrega, el usuario puede actualizar ese destino antes del cierre logistico
- el inventario debe reflejar primero el traslado interno y despues el despacho
- el picking de salida al cliente no debe salir desde manufactura si se definio otro almacen destino

## Resultado esperado

Al completar el flujo:

- la venta dispara la fabricacion
- la fabricacion conserva el contexto del almacen origen
- el usuario define o corrige el almacen final de entrega
- el producto terminado se mueve internamente al almacen correcto
- el despacho al cliente sale desde ese almacen seleccionado
