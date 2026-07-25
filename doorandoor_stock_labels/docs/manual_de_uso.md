# Manual de Uso - DoorAndDoor Stock Labels

## Objetivo

Este documento explica como usar el modulo `doorandoor_stock_labels`
siguiendo el proceso operativo esperado en Doorandoor:

- un usuario inicia el proceso y prepara la impresion
- el especialista de recepcion recibe y cuenta fisicamente
- la serializacion se registra en el momento de la recepcion
- el especialista pega las etiquetas segun cada unidad recibida
- al finalizar, la recepcion se cierra con un reporte visible para quien
  inicio el proceso

## Alcance de esta primera version

- Configuracion basica en producto para imprimir etiquetas al recibir.
- Impresion de etiquetas desde recepciones de inventario.
- Soporte para QR navegable desde movil.
- Soporte para `Code128` para lectores tipo hanger o scanner industrial.
- Uso de serial/lote cuando el producto esta configurado con trazabilidad.

## Flujo general del proceso

### Rol 1 - Usuario que inicia el proceso

Este usuario prepara la operacion antes de que el almacen reciba
fisicamente la mercancia.

Sus tareas son:

1. Crear o revisar el producto.
2. Confirmar que el producto use el tipo de seguimiento correcto.
3. Preparar la recepcion en Odoo.
4. Dejar listo el documento para que el especialista de recepcion pueda
   registrar lo recibido e imprimir o usar las etiquetas.

### Rol 2 - Especialista de recepcion / almacenero

Este usuario ejecuta la recepcion real en almacen.

Sus tareas son:

1. Recibir fisicamente la mercancia.
2. Contar las unidades.
3. Registrar seriales en el momento de la recepcion.
4. Pegar las etiquetas a medida que las unidades se reciben y verifican.
5. Cerrar la recepcion y dejar trazabilidad del resultado final.

## Creacion del producto

Antes de recibir un producto nuevo, debe existir correctamente creado en
Odoo.

### Datos minimos recomendados

- Nombre del producto
- Referencia interna `default_code`
- `Barcode` si el negocio ya lo maneja
- Tipo de producto correcto
- Categoria del producto
- Unidad de medida

### Regla importante sobre seriales

El serial **no debe confundirse con el codigo del producto**.

- El codigo del producto identifica el modelo o articulo.
- El serial identifica una unidad fisica especifica de ese producto.

Ejemplo:

- Producto: Silla Ejecutiva Negra
- Codigo del producto: `SILLA-EJ-NEG`
- Seriales posibles:
  - `SN-000001`
  - `SN-000002`
  - `SN-000003`

Cada serial es independiente del codigo del producto aunque pertenezca al
mismo articulo.

## Configuracion del producto

Abrir el producto y revisar los siguientes campos:

- `Tracking`
  - `None`: no usa lote ni serie.
  - `By Lots`: varias unidades pueden compartir un mismo lote.
  - `By Unique Serial Number`: cada unidad lleva su serial propio.
- `Print Label On Receipt`
  - Si esta activado, el producto se incluye por defecto al imprimir
    etiquetas desde una recepcion.
- `Use Product Barcode On Label`
  - Si esta activado, el `Code128` usa el `barcode` del producto cuando
    exista.
  - Si esta desactivado, usa la referencia interna `default_code`.

## Flujo recomendado para productos controlados

Para productos que necesitan control individual:

1. Configurar `Tracking = By Unique Serial Number`.
2. Activar `Print Label On Receipt`.
3. Registrar el producto en la recepcion del almacen.
4. Esperar la llegada fisica del producto.
5. Cargar el serial de cada unidad **durante la recepcion**.
6. Pegar la etiqueta a cada unidad conforme se recibe y se cuenta.
7. Pulsar `Print Labels` en la recepcion cuando corresponda al flujo
   operativo definido.
8. Imprimir una etiqueta por serial recibido.

## Momento correcto de la serializacion

La serializacion debe hacerse **a la hora de la recepcion**, no en una
etapa previa desconectada de la realidad fisica del almacen.

Esto permite que:

- el serial registrado coincida con la unidad realmente recibida
- el especialista valide cantidad contra mercancia fisica
- la etiqueta se pegue a la unidad correcta en el mismo momento
- se reduzcan errores entre lo preparado y lo efectivamente recibido

## Escenario operativo ideal

El flujo ideal propuesto es:

1. Un usuario administrativo o de compras crea el producto y prepara la
   recepcion.
2. Ese usuario deja listo el proceso para impresion o control.
3. El especialista de recepcion recibe fisicamente la mercancia.
4. Mientras recibe, cuenta y registra los seriales reales.
5. A medida que identifica cada unidad, pega la etiqueta correspondiente.
6. Al terminar, valida la recepcion.
7. El sistema genera o permite consultar un reporte final de recepcion.
8. El usuario que inicio el proceso puede revisar que fue lo realmente
   recibido por el almacenero.

## Flujo para productos sin serial

Para productos sin trazabilidad individual:

1. Configurar `Tracking = None` o `By Lots`.
2. Activar `Print Label On Receipt` si se desea incluirlo por defecto.
3. Registrar la cantidad recibida en la recepcion.
4. Pulsar `Print Labels`.
5. Si el wizard tiene activado `Include Untracked Quantities`, el sistema
   genera una etiqueta por unidad recibida.

## Uso desde la recepcion

En una operacion de tipo recepcion:

1. Abrir la recepcion.
2. Verificar productos, cantidades y seriales/lotes.
3. Si el producto usa serial unico, pulsar `Register Serials`.
4. Cargar alli los seriales reales, una unidad por cada linea.
5. Guardar los seriales.
6. Para lotes o revisiones avanzadas, usar tambien operaciones detalladas
   si el flujo lo requiere.
6. Pulsar el boton `Print Labels`.
4. En el wizard:
   - `Only Products Marked For Labels`: incluye solo productos marcados
     para etiquetado.
   - `Include Untracked Quantities`: permite imprimir por cantidad cuando
     no existe serial o lote.
7. Pulsar `Print`.
8. Pegar las etiquetas segun se reciben y cuentan las unidades.
9. Cerrar la recepcion solo despues de terminar la verificacion fisica.

## Como cargar seriales o lotes en la recepcion

Este punto es clave para el cliente.

Si el producto tiene `Tracking = By Unique Serial Number` o `By Lots`, no
basta con poner la cantidad en la linea principal de la recepcion.

Tambien hay que registrar el detalle real de lo recibido.

### Paso a paso con el wizard nuevo

1. Abrir la recepcion.
2. Pulsar `Register Serials`.
3. Revisar la lista de unidades preparadas por el sistema.
4. Escribir un serial por cada unidad.
5. Si desea continuar la numeracion del mismo dia para ese producto,
   pulsar `Auto Generate Serials`.
6. El sistema buscara la ultima serie de entrada del mismo producto con la
   misma fecha y continuara desde el siguiente numero disponible.
5. Pulsar `Save Serials`.
6. Regresar a la recepcion.
7. Pulsar `Print Labels`.

### Paso a paso manual en operaciones detalladas

1. Abrir la recepcion.
2. Localizar la linea del producto.
3. Abrir **operaciones detalladas**.
4. Crear una linea por cada unidad si el producto usa serial.
5. En cada linea colocar:
   - producto
   - cantidad
   - serial o lote real
6. Guardar las operaciones detalladas.
7. Regresar a la recepcion.
8. Ejecutar `Print Labels`.

### Regla practica

- Si el producto usa **serial**, normalmente cada unidad lleva su propia
  linea y su propio serial.
- Si el producto usa **lote**, varias unidades pueden compartir el mismo
  lote segun la operacion real.

## Mensaje de error frecuente

Puede aparecer un mensaje como:

- `Debe proporcionar un numero de serie o lote para el producto`

Esto significa que:

- el producto esta configurado con seguimiento
- pero la recepcion todavia no tiene cargado el serial o lote requerido

### Como resolverlo

1. No imprimir aun.
2. Abrir las operaciones detalladas.
3. Registrar el serial o lote real.
4. Guardar.
5. Intentar imprimir nuevamente.

## Diferencia entre cantidad y serial

Es importante explicarlo al cliente:

- La **cantidad** dice cuantas unidades se reciben.
- El **serial** dice exactamente cuales unidades son.

Por eso, en productos serializados, la cantidad sola no alcanza.
Hace falta identificar cada unidad.

## Cierre del proceso

Al finalizar la recepcion debe existir un cierre claro del proceso.

### Objetivo del cierre

Permitir que el usuario que inicio el proceso pueda ver:

- que productos se esperaban
- que cantidades se recibieron realmente
- que seriales fueron registrados
- quien hizo la recepcion
- cuando se termino la recepcion

### Resultado esperado

La recepcion debe cerrar con un **reporte de recepcion** o una vista final
equivalente que sirva como evidencia operativa.

Ese reporte sera la base para:

- control interno
- auditoria operativa
- confirmacion del almacenero
- seguimiento del usuario que preparo la recepcion

## Que contiene la etiqueta

La etiqueta actual imprime:

- Nombre del producto.
- Referencia interna si existe.
- Serial o lote cuando existe.
- `Code128` para lectura con equipos de escaneo.
- `QR` con URL del sistema Odoo.

## Comportamiento del QR

- Si la etiqueta pertenece a una unidad con serial/lote, el `QR` abre el
  registro del lote/serial en Odoo.
- Si la etiqueta no tiene serial/lote, el `QR` abre el formulario del
  producto.

## Recomendaciones operativas

- Usar `By Unique Serial Number` para equipos, muebles identificables,
  electronica y productos que necesiten trazabilidad por unidad.
- Usar `By Lots` para grupos de unidades que comparten origen o fecha.
- Evitar serializar productos consumibles o de rotacion masiva si el
  negocio no necesita ese nivel de control.
- No registrar seriales teoricos antes de la recepcion fisica si el
  especialista aun no ha confirmado las unidades reales.
