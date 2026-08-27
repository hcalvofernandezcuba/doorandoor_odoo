# Productos transformados DoorAndDoor

## Creacion desde facturacion

1. Crear o abrir una prefactura de cliente en borrador.
2. Agregar el producto normal que servira como base.
3. Pulsar `Armar producto` en la linea.
4. Marcar `Declarar como producto transformado`.
5. Completar Ancho, Alto, especificaciones e instrucciones. Estas medidas
   libres no se agregan al catalogo de atributos o variantes normales.
6. Pulsar `Confirmar` y completar componentes u operaciones de la LDM.
7. Pulsar `Crear producto y LDM`.

El acceso a productos transformados no ocupa una columna adicional en la factura.
Solo aparece dentro del configurador cuando la factura esta en borrador y el
producto base no es ya un producto transformado.

El producto nuevo sustituye al producto base en la linea. La LDM nace en
estado `LDM pendiente`.

Cuando el cambio incluye medidas deben completarse Ancho y Alto. El
nombre se forma automaticamente con la nomenclatura:

`Producto base Transformado AnchoxAlto`

Ejemplo: `Miami Transformado 36x30`. El mismo texto se guarda en el producto
transformado y en la descripcion de la linea de factura y venta.

## Guia de receta y fabricacion

La informacion de transformacion no queda solamente en la factura. Se muestra en:

- la ficha del producto transformado;
- la LDM, junto a sus componentes y operaciones;
- cada orden de fabricacion creada para ese producto.

La guia incluye producto base, factura de origen, medidas finales,
especificaciones e instrucciones de fabricacion (cortes, armado, acabado,
tolerancias y controles). Si se selecciona una LDM base, el asistente copia
tambien sus operaciones y centros de trabajo; Produccion debe revisarlos y
adaptarlos antes de validar la nueva LDM.

La lista de componentes se puede ajustar en el asistente. Las operaciones,
tiempos, centros de trabajo y hojas de trabajo se terminan de revisar en la
LDM transformada con las herramientas normales de Fabricacion.

## Validacion de Produccion

1. Abrir la ficha del producto transformado.
2. Revisar medidas, componentes, operaciones, centros de trabajo,
   instrucciones y controles de la receta.
3. Pulsar `Validar LDM transformada`.

Si la LDM se modifica posteriormente, vuelve automaticamente a pendiente.
La factura no puede publicarse mientras una LDM transformada este pendiente.

## Pagos y operaciones

- Un pago parcial validado libera la cantidad proporcional y crea produccion.
- El producto transformado siempre usa la ruta de fabricacion.
- El despacho y la orden de recogida permanecen bloqueados hasta pago total.
- Pagos posteriores liberan solamente la cantidad adicional cubierta.

## Archivo automatico

La fecha de archivo se mueve 30 dias desde cada actividad comercial,
productiva o de inventario. El proceso diario solo archiva cuando no existen:

- facturas en borrador con el producto;
- movimientos de stock abiertos;
- ordenes de fabricacion abiertas;
- existencias disponibles.

La LDM transformada se archiva junto con el producto. Ningun documento historico
se elimina.
