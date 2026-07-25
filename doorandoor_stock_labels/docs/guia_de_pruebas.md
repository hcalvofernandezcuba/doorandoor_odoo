# Guia de Pruebas - DoorAndDoor Stock Labels

## Objetivo

Validar que el modulo `doorandoor_stock_labels` funcione correctamente en
configuracion de producto, recepcion, serializacion, impresion y lectura
por QR / scanner.

## Preparacion

Antes de probar:

1. Actualizar el modulo en Odoo.
2. Confirmar que la URL base del sistema sea correcta.
3. Tener definidos dos perfiles de usuario:
   - usuario que inicia/prepara el proceso
   - especialista de recepcion / almacenero
4. Tener al menos dos productos de prueba:
   - un producto con serial
   - un producto sin serial

## Caso 0 - Creacion correcta del producto

### Pasos

1. Crear un producto nuevo con nombre y referencia interna.
2. Configurar `Tracking = By Unique Serial Number`.
3. Activar `Print Label On Receipt`.
4. Guardar el producto.

### Resultado esperado

- El producto queda listo para usarse en recepciones.
- El equipo entiende que el serial sera independiente del codigo del
  producto.

## Caso 1 - Producto con serial

### Configuracion

- Producto A
- `Tracking = By Unique Serial Number`
- `Print Label On Receipt = True`
- `Barcode` definido si se desea usar ese valor

### Pasos

1. Crear una recepcion con 2 unidades del Producto A.
2. Simular llegada fisica de la mercancia.
3. Abrir operaciones detalladas.
4. Asignar dos seriales distintos durante la recepcion.
4. Abrir el wizard `Print Labels`.
5. Imprimir etiquetas.

### Resultado esperado

- Se generan 2 etiquetas.
- Cada etiqueta muestra el nombre del producto.
- Cada etiqueta muestra su serial correcto.
- El `Code128` corresponde al serial.
- El `QR` abre el registro del serial/lote en Odoo.
- El serial no coincide necesariamente con el `default_code` del producto.

## Caso 1.1 - Error por falta de serial

### Pasos

1. Configurar un producto con `Tracking = By Unique Serial Number`.
2. Crear una recepcion con cantidad mayor que cero.
3. No cargar seriales en operaciones detalladas.
4. Intentar imprimir etiquetas.

### Resultado esperado

- El proceso debe rechazar la impresion.
- El usuario debe entender que primero debe registrar seriales reales.
- El equipo de pruebas debe confirmar que el manual de uso permite resolver
  el caso sin asistencia tecnica.

## Caso 2 - Producto sin serial

### Configuracion

- Producto B
- `Tracking = None`
- `Print Label On Receipt = True`

### Pasos

1. Crear una recepcion con cantidad 3 del Producto B.
2. Abrir el wizard `Print Labels`.
3. Mantener activado `Include Untracked Quantities`.
4. Imprimir etiquetas.

### Resultado esperado

- Se generan 3 etiquetas.
- Cada etiqueta muestra nombre y referencia del producto.
- El `Code128` usa `barcode` o `default_code`.
- El `QR` abre el formulario del producto.

## Caso 3 - Filtro por productos marcados

### Pasos

1. Crear una recepcion con un producto marcado y otro no marcado.
2. Abrir el wizard con `Only Products Marked For Labels = True`.
3. Imprimir etiquetas.

### Resultado esperado

- Solo se generan etiquetas del producto marcado.

## Caso 4 - Sin datos suficientes

### Pasos

1. Crear una recepcion sin cantidades recibidas o sin seriales cargados
   cuando el flujo lo requiera.
2. Abrir el wizard e intentar imprimir.

### Resultado esperado

- El sistema no debe generar etiquetas vacias.
- Debe mostrarse un mensaje indicando que no se generaron etiquetas.

## Caso 5 - Flujo por roles

### Pasos

1. Usuario A crea el producto y prepara la recepcion.
2. Usuario B abre la recepcion en almacen.
3. Usuario B cuenta, serializa y pega etiquetas.
4. Usuario B cierra la recepcion.
5. Usuario A revisa el resultado final.

### Resultado esperado

- El proceso refleja separacion entre preparacion y recepcion.
- El usuario que inicia puede revisar lo recibido por almacen.
- El cierre deja evidencia clara del resultado de recepcion.

## Caso 6 - Prueba desde movil

### Pasos

1. Imprimir una etiqueta real o generar PDF.
2. Escanear el `QR` con un movil conectado al sistema.

### Resultado esperado

- El navegador abre Odoo.
- Si el usuario tiene sesion iniciada, llega al registro esperado.
- Si no tiene sesion, Odoo solicita autenticacion y luego permite acceder.

## Caso 7 - Prueba con lector

### Pasos

1. Escanear el `Code128` con el hanger o scanner disponible.
2. Verificar el valor recibido por el equipo o software intermedio.

### Resultado esperado

- El lector interpreta correctamente el serial o la referencia.
- El codigo no presenta truncamientos ni caracteres inesperados.

## Caso 8 - Continuidad de seriales por fecha y producto

### Pasos

1. Crear una primera recepcion del mismo producto serializado en la fecha
   del `16 de julio de 2026`.
2. Autogenerar seriales y guardar la recepcion.
3. Crear una segunda recepcion del mismo producto en la misma fecha.
4. Abrir `Register Serials`.
5. Pulsar `Auto Generate Serials`.

### Resultado esperado

- El sistema no reinicia en `1607260001`.
- El sistema busca el ultimo serial de entrada del mismo producto en esa
  fecha.
- La nueva recepcion continua en el siguiente consecutivo disponible.

## Observaciones a registrar

Durante las pruebas documentar:

- modelo del hanger o scanner
- distancia de lectura
- tamano de etiqueta
- calidad de impresion
- si el movil abre correctamente la URL interna o publica
- si el flujo real de recepcion permite pegar las etiquetas a tiempo
- si el especialista puede serializar sin frenar la recepcion
- observaciones de usuarios de almacen
