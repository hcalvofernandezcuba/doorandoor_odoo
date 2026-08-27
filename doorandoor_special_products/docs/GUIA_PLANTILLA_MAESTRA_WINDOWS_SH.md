# Guía: plantilla maestra WINDOWS SH y producto especial desde Ventas

## 1. Objetivo

Esta guía explica cómo configurar `WINDOWS SH` como plantilla maestra de
fabricación y cómo utilizarla desde una cotización, prefactura o factura para
crear un producto especial.

El producto `WINDOWS SH` es una referencia técnica. No representa inventario
disponible ni debe seleccionarse como una línea comercial normal. Su función
es proporcionar al producto especial nuevo:

- la familia de fabricación `WINDOWS`;
- los atributos que el vendedor completará con valores nuevos;
- la LDM maestra con materias primas;
- las operaciones y centros de trabajo;
- las reglas que calculan las cantidades de componentes.

El producto especial resultante sí es almacenable, puede fabricarse, entrar en
stock, venderse y despacharse mediante los flujos normales de DoorAndDoor.

## 2. Requisitos previos

Antes de configurar la plantilla, el administrador debe comprobar lo
siguiente:

1. El módulo `doorandoor_product_config` está instalado y actualizado.
2. El módulo `doorandoor_special_products` está actualizado, como mínimo, a
   la versión `18.0.4.4.0`.
3. El usuario que configura la plantilla pertenece al grupo
   `Fabricación / Administrador`.
4. Los atributos que describen la ventana ya existen en
   `Ventas > Configuración > Atributos`.
5. Las materias primas, unidades de medida, centros de trabajo y operaciones
   que formarán la receta ya están creados.

> Si la pestaña **Plantilla de fabricación** no aparece o la base informa que
> el campo técnico `ddsp_is_manufacturing_template` no existe, el módulo no ha
> sido actualizado todavía. El administrador técnico debe actualizar el
> módulo antes de continuar.

## 3. Crear o preparar el producto WINDOWS SH

### 3.1 Abrir el producto

1. Ir a `Ventas > Productos > Productos` o
   `Inventario > Productos > Productos`.
2. Buscar y abrir `WINDOWS SH`.
3. Si no existe, crear un producto nuevo con ese nombre.

### 3.2 Configuración comercial y logística

Configurar el producto como referencia técnica:

1. Desactivar **Puede ser vendido**.
2. Desactivar **Puede ser comprado**, salvo que exista una razón operativa
   documentada para comprar esta referencia.
3. No registrar existencias para `WINDOWS SH`.
4. No usarlo directamente en cotizaciones, prefacturas, facturas ni
   transferencias.

Desactivar **Puede ser vendido** no impide que aparezca en el asistente. El
asistente utiliza el indicador **Plantilla maestra de fabricación**, no el
indicador comercial.

### 3.3 Declarar la plantilla maestra

1. Abrir la pestaña **Plantilla de fabricación**.
2. Activar **Plantilla maestra de fabricación**.
3. En **Familia de fabricación**, seleccionar `WINDOWS`.
4. En **Nombre del producto resultante**, escribir el nombre base que deberán
   recibir los productos nuevos; por ejemplo, `WINDOW SH` o `WINDOWS SH`.
5. Guardar el producto.

La casilla **Permitir transformaciones** pertenece al flujo Transformado y no
es la condición que hace visible esta plantilla en el asistente de Especiales.

## 4. Configurar los atributos

Los atributos de `WINDOWS SH` se precargan como filas que el vendedor debe
completar en el asistente. Todos sus valores aparecen inicialmente en blanco.

1. En la pestaña de atributos y variantes del producto, agregar los atributos
   requeridos para fabricar la ventana.
2. Usar nombres claros y estables, por ejemplo:
   - `Ancho`;
   - `Alto`;
   - `Tipo de vidrio`;
   - `Color`;
   - `Marco`;
   - cualquier otra característica necesaria para producción.
3. Guardar el producto después de configurar las líneas de atributos.

El vendedor también puede agregar o quitar filas en el asistente, seleccionar
otros atributos existentes o escribir nombres de atributos completamente
nuevos. Los valores también son nuevos: ni los atributos ni los valores tienen
que existir previamente en el catálogo de `WINDOWS SH`.

Para reglas dimensionales, el valor debe comenzar con una cantidad que pueda
interpretarse numéricamente. Ejemplos válidos: `36`, `36.5` o `36 1/2`. Los
textos puramente descriptivos deben utilizarse en atributos sin fórmula de
cantidad.

## 5. Crear la LDM maestra

### 5.1 Crear la receta

1. Desde `WINDOWS SH`, abrir el botón inteligente de **Lista de materiales**,
   o ir a `Fabricación > Productos > Listas de materiales`.
2. Crear una LDM cuyo producto sea exactamente `WINDOWS SH`.
3. Mantener la LDM activa.
4. Agregar todas las materias primas necesarias.
5. Configurar las cantidades base y sus unidades de medida.
6. Agregar las operaciones, centros de trabajo, tiempos y secuencia.
7. Guardar la LDM.

La LDM maestra es opcional. Si no existe o está vacía, el sistema crea para el
Especial una LDM mínima editable con tres unidades del componente automático
por cada unidad fabricada.

En la pestaña **Plantilla de fabricación** puede definirse el
**Componente automático** y su **Cantidad automática**. Si no se configura,
el sistema busca primero `bisagras`, después `bisagra` y, solo si ninguno
existe, crea un componente genérico.

La receta maestra no debe consumir el propio producto terminado `WINDOWS SH`.
Debe contener materias primas reales. Al crear el Especial, esta LDM se copia
al producto nuevo junto con sus operaciones.

### 5.2 Reglas de transformación o cálculo

En la pestaña **Reglas de transformación** de la LDM se puede ajustar la
cantidad de un componente según una medida escrita por el vendedor.

Para cada regla indicar:

- **Componente**: materia prima incluida en la LDM;
- **Atributo**: medida que controla la cantidad, por ejemplo `Alto`;
- **Condición**: valor opcional para limitar cuándo se aplica;
- **Cantidad base**;
- **Factor del valor**;
- **Porcentaje de merma**.

La fórmula es:

`Cantidad = Cantidad base + (valor numérico del atributo × factor) + merma`

Ejemplo: para dos perfiles verticales, con `Alto = 80`, cantidad base `0`,
factor `2` y sin merma, la cantidad resultante será `160`.

## 6. Comprobación antes de usar Ventas

Abrir nuevamente `WINDOWS SH` y confirmar:

- está activo;
- **Plantilla maestra de fabricación** está activado;
- la familia es `WINDOWS`;
- tiene un nombre de producto resultante;
- tiene atributos configurados;
- opcionalmente existe una LDM activa asociada directamente a `WINDOWS SH`;
- si no hay receta, está definido o disponible el componente automático;
- las operaciones y reglas están completas cuando correspondan.

No es necesario activar **Puede ser vendido**. La plantilla maestra se excluye
intencionalmente de la lista normal de productos de las líneas comerciales.

## 7. Crear el producto especial desde Ventas

### 7.1 Cotización

1. Ir a `Ventas > Órdenes > Cotizaciones`.
2. Crear o abrir una cotización en estado borrador.
3. Seleccionar el cliente y completar los datos generales.
4. Pulsar **Agregar producto especial** en la cabecera.
5. En **Plantilla**, seleccionar `WINDOWS SH`.
6. Si existe una receta completa, confirmar o seleccionar la **LDM maestra**.
   Puede dejarse vacía para generar automáticamente la LDM mínima.
7. Revisar los atributos precargados y agregar o quitar filas cuando sea
   necesario.
8. En cada fila seleccionar un **Atributo existente** o escribir un
   **Atributo nuevo**. No completar ambas columnas en la misma fila.
9. Escribir el **Nuevo valor**. Ninguna fila debe quedar incompleta y un mismo
   atributo no puede repetirse.
10. Indicar cantidad y precio unitario.
11. Completar las especificaciones y las instrucciones de fabricación.
12. Pulsar **Crear especial y agregar**.

El sistema crea un producto almacenable nuevo, sus valores de atributos, su
variante y una LDM propia, copiada de la maestra o generada automáticamente.
Después agrega el producto a la cotización.

### 7.2 Prefactura o factura

El mismo botón **Agregar producto especial** está disponible en una
prefactura o factura de cliente mientras el documento esté en borrador. El
procedimiento es el mismo que en la cotización.

No se debe buscar `WINDOWS SH` mediante **Agregar un producto**. Esa lista
excluye deliberadamente las plantillas maestras y los productos especiales.

## 8. Qué debe observarse después de crear el Especial

En la línea comercial debe aparecer un nombre parecido a:

`[ESP-...] WINDOWS SH Especial [Ancho: 36, Alto: 80, ...]`

En cotizaciones, prefacturas y facturas impresas se conserva el código y el
nombre del producto, pero los valores se presentan debajo por tipo:

```text
[ESP-...] WINDOWS SH Especial

Ancho: 36
Alto: 80
Cristal: Gray
```

El producto creado debe mostrar:

- tipo personalizado `Especial`;
- plantilla de origen `WINDOWS SH`;
- familia `WINDOWS`;
- LDM maestra de origen;
- valores solicitados;
- documento y línea comercial de origen;
- fecha prevista de archivado.

También recibe automáticamente dos identificadores diferentes:

- **Referencia interna**: código `ESP-...` usado visualmente en documentos;
- **Código de barras**: EAN-13 numérico único, generado en el mismo proceso y
  utilizable por lectores y etiquetas.

La LDM nueva debe contener las materias primas y operaciones copiadas de la
maestra, con las cantidades recalculadas por las reglas. No debe consumir una
unidad terminada de `WINDOWS SH`.

La orden de fabricación se libera según las reglas de pago configuradas en
DoorAndDoor. El despacho continúa sujeto al flujo comercial y de cobros ya
establecido.

## 9. Diagnóstico cuando WINDOWS SH no aparece

Revisar, en este orden:

1. **Módulo actualizado**: la base debe tener instalada la versión indicada en
   esta guía.
2. **Casilla maestra**: `WINDOWS SH` debe tener activado
   **Plantilla maestra de fabricación**.
3. **Producto activo**: un producto archivado no aparece.
4. **Permisos**: la configuración requiere Administrador de Fabricación; el
   uso comercial requiere permisos de vendedor.
5. **Documento editable**: la cotización debe estar en borrador o enviada; la
   prefactura/factura debe estar en borrador.
6. **Botón correcto**: utilizar **Agregar producto especial**, no la lista
   normal de productos.
7. **LDM activa**: debe existir una LDM activa cuyo producto sea exactamente
   `WINDOWS SH`.
8. **Caché web**: después de actualizar el módulo, recargar la vista con una
   recarga forzada del navegador o cerrar la sesión y entrar nuevamente.

Si la plantilla aparece pero no permite confirmar, revisar que cada atributo
tenga un valor, que la LDM tenga componentes y que cantidad y precio sean
válidos.

## 10. Prueba mínima de aceptación

1. Abrir una cotización nueva.
2. Pulsar **Agregar producto especial**.
3. Verificar que `WINDOWS SH` aparece en Plantilla.
4. Seleccionarla y comprobar que aparecen todos sus atributos vacíos.
5. Introducir valores nuevos y crear el Especial.
6. Confirmar que la línea se agrega a la cotización.
7. Abrir el producto generado y verificar su trazabilidad.
8. Abrir su LDM y comprobar materias primas, cantidades y operaciones.
9. Ejecutar el flujo de pago definido y verificar la liberación de la MO.
10. Completar producción, entrada en stock, despacho y entrega conforme al
    flujo normal.
