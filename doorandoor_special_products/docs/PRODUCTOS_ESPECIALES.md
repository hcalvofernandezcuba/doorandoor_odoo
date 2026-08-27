# Productos especiales desde plantilla maestra

## Diferencia funcional

- **Transformado:** consume un producto terminado existente y lo modifica.
- **Especial:** se fabrica desde cero con materias primas y operaciones de una
  plantilla maestra WINDOWS o DOORS.

## Preparar la plantilla

1. Crear un producto técnico sin venta habilitada.
2. Marcar `Plantilla maestra de fabricación`.
3. Seleccionar la familia WINDOWS o DOORS.
4. Escribir el nombre comercial que tendrán los productos resultantes.
5. Opcionalmente crear su LDM con componentes y operaciones. Sin ella, el
   sistema genera una receta mínima de tres bisagras por unidad.
6. Configurar las reglas dimensionales necesarias.

## Crear el especial desde una venta

1. Abrir una cotización, prefactura o factura en borrador.
2. Pulsar `Agregar producto especial`.
3. Seleccionar la plantilla; la LDM maestra es opcional.
4. Revisar los atributos precargados y agregar o quitar filas libremente.
5. En cada fila seleccionar un atributo existente o escribir el nombre de un
   atributo completamente nuevo.
6. Escribir un valor nuevo para cada atributo.
7. Indicar cantidad, precio, especificaciones e instrucciones.
8. Pulsar `Crear especial y agregar`.

El sistema crea el producto almacenable, su variante, la LDM calculada y la
línea comercial. La MO se libera con las reglas de pago existentes. Después de
la fabricación, el producto entra en stock y el despacho consume esa existencia.

En el mismo proceso se generan la referencia interna `ESP-...` y un barcode
EAN-13 numérico único para lectura e impresión de etiquetas.

El producto Especial es independiente: la plantilla aporta la receta y las
operaciones, pero no limita los atributos ni sus valores. Los atributos nuevos
se crean con generación dinámica de variantes para evitar combinaciones
innecesarias en el catálogo.

El producto no aparece en selectores de ventas posteriores. Se archiva cuando
han transcurrido 30 días desde su último movimiento y no quedan ventas, facturas,
stock, movimientos u órdenes de fabricación abiertas.
