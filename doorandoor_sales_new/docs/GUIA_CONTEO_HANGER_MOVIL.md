# Conteo de Inventario con Hanger y Móvil

El conteo físico crea una sesión auditable. Las lecturas no modifican el stock
inmediatamente; un responsable revisa las diferencias antes de aplicar el ajuste.

## Preparación

1. Confirmar barcode único en cada variante física.
2. Seleccionar una ubicación interna concreta.
3. Detener temporalmente entradas, salidas y traslados sobre esa ubicación.
4. Asignar Almacenero DoorAndDoor al operador.
5. Asignar Inventory Count Manager a quien validará diferencias.

## Crear la sesión

1. Abrir Operaciones, Almacén, Conteo de inventario.
2. Crear una sesión y seleccionar la ubicación.
3. Pulsar Start and Load Stock.
4. Odoo carga la fotografía de existencias teóricas.
5. Definir Cantidad por lectura, normalmente `1`.

## Conteo con hanger

1. Colocar el cursor en el campo de barcode.
2. Disparar el lector sobre cada etiqueta.
3. El hanger escribe y envía el código como teclado.
4. Cada lectura válida incrementa la variante configurada.
5. Confirmar visualmente producto, variante y cantidad antes de continuar.

## Conteo con móvil

1. Abrir DoorAndDoor desde la aplicación móvil.
2. Entrar en la sesión activa.
3. Pulsar Tomar foto y leer.
4. Mantener solamente un barcode dentro del recorte.
5. Acercar, enfocar y evitar reflejos.
6. Confirmar que el código reconocido coincide con la etiqueta.
7. Cada lectura válida queda registrada automáticamente.

## Registro manual alternativo

1. Escribir el barcode completo.
2. Pulsar Registrar barcode escrito.
3. Confirmar que el producto aparece entre los contados.

## Información para el operador

La lista debe mostrar producto, variante, referencia, barcode, cantidad
esperada, cantidad contada, diferencia y unidad de medida. Los productos ya
contados permanecen visibles para evitar lecturas repetidas por confusión.

## Revisión y ajuste

1. Pulsar Review al finalizar el conteo.
2. Investigar cada diferencia.
3. Registrar cero expresamente cuando un producto realmente no aparezca.
4. Repetir el conteo físico si existe duda.
5. El responsable pulsa Validate Adjustment.

Solo la validación final modifica `stock.quant` y deja la trazabilidad del
usuario, fecha, ubicación y diferencias. Una sesión validada no regresa a conteo.

## Errores que deben evitarse

- Compartir barcode entre variantes.
- Escanear una variante ajena a la sesión.
- Contar mientras existen movimientos sobre la ubicación.
- Validar diferencias sin investigación.
- Cambiar directamente las existencias teóricas.
- Escanear repetidamente porque no se revisó la lista de contados.

