# Guía de productos y variantes — DoorAndDoor

## 1. Objetivo

Esta guía explica cómo configurar productos con variantes para utilizarlos en
facturación, inventario, fabricación y etiquetas sin generar combinaciones
incorrectas. También describe cómo un administrador puede corregir precios,
valores, referencias y variantes personalizadas.

El módulo responsable es `doorandoor_product_config`.

## 2. Conceptos importantes

### Producto plantilla

Es el producto general, por ejemplo `Miami`. Contiene categoría, unidad de
medida, precio base, impuestos, rutas y atributos disponibles.

### Atributo

Es una característica configurable, por ejemplo:

- Color;
- Medida;
- Material;
- Acabado;
- Orientación.

### Valor de atributo

Es una opción perteneciente a un atributo. Por ejemplo, el atributo `Color`
puede contener `Blanco`, `Negro` y `Natural`.

### Variante

Es una combinación concreta de valores. Ejemplo:

`Miami / Blanco / 36x81`

Cada variante puede tener referencia interna, código de barras, precio
adicional, existencias y movimientos propios.

## 3. Modos de creación de variantes

Odoo permite tres modos:

### Al instante

Crea todas las combinaciones cuando se agregan valores. Debe utilizarse solo
cuando existen pocos atributos y pocas opciones.

Ejemplo: 2 colores por 2 materiales generan 4 variantes.

### De forma dinámica

Crea una combinación cuando se necesita. Es el modo recomendado para medidas
personalizadas y catálogos con muchas posibilidades.

### Nunca

El valor se guarda como información configurable, pero no diferencia el
inventario por variante.

El tipo visual `Varias casillas` obliga a utilizar `Nunca`. No debe intentarse
convertir directamente un atributo ya utilizado de `Nunca` a `Dinámico`, pues
puede alterar combinaciones e historial.

## 4. Configuración recomendada por tipo de atributo

| Uso | Visualización | Creación | Selección |
|---|---|---|---|
| Color | Opción o Seleccionar | Dinámica | Un valor |
| Medida estándar | Seleccionar | Dinámica | Un valor |
| Medida excepcional | Seleccionar | Dinámica | Un valor nuevo |
| Material principal | Opción o Seleccionar | Dinámica | Un valor |
| Accesorios acumulables | Varias casillas | Nunca | Varios valores |
| Información comercial | Varias casillas | Nunca | Varios valores |

Cuando el atributo actual `Medidas` utiliza `Varias casillas` y `Nunca`, debe
conservarse. Para medidas que deban crear inventario separado se recomienda un
atributo nuevo llamado `Medida personalizada`, configurado como `Seleccionar`
y `De forma dinámica`.

## 5. Crear correctamente un producto con variantes

1. Ir a **Inventario → Productos → Productos**.
2. Pulsar **Nuevo**.
3. Introducir el nombre de la plantilla.
4. Configurar:
   - tipo de producto;
   - categoría;
   - unidad de medida;
   - precio base;
   - impuestos;
   - rutas de inventario o fabricación.
5. Abrir la pestaña **Atributos y variantes**.
6. Agregar cada atributo necesario.
7. Seleccionar únicamente los valores válidos para ese producto.
8. Guardar la plantilla.
9. Abrir el botón inteligente **Variantes**.
10. Revisar cada variante generada y completar:
    - referencia interna única;
    - código de barras cuando corresponda;
    - precio adicional de variante;
    - peso u otros datos operativos necesarios.

Antes de vender, debe comprobarse que no existan combinaciones duplicadas y
que cada variante almacenable tenga una referencia interna o código de barras.

## 6. Precio de una variante

El precio utilizado por el módulo se calcula así:

`Precio final = Precio base de la plantilla + Precio adicional de variante`

El precio base se edita en la plantilla. El campo **Variant Extra Price** se
edita en la ficha de la variante.

Ejemplo:

- precio base: 500.00;
- adicional de variante: 75.00;
- precio configurado: 575.00.

El precio calculado se copia al precio unitario de la línea de factura.

## 7. Armar el producto desde una factura

1. Crear una factura de cliente en borrador.
2. En la columna **Producto**, seleccionar el modelo requerido. Esta lista
   muestra una sola entrada por plantilla y no todas sus variantes.
3. El sistema guarda automáticamente la prefactura en borrador y abre
   **Armar producto**. El botón manual permanece disponible como respaldo.
4. Confirmar la plantilla del producto.
5. En **Acción**, escoger **Armar producto**.
6. Marcar las opciones múltiples que correspondan.
7. Escoger un valor en cada desplegable de atributo que define variante.
8. Revisar cantidad, variante resultante, resumen, precio y total.
9. Si la medida es excepcional, marcar **Declarar como producto especial** y
   completar Ancho, Alto, especificaciones e instrucciones. Esas medidas no se
   agregan a los atributos ni a las listas normales.
10. Revisar la variante resultante, el resumen, el precio base, el adicional y
   el precio configurado.
11. Pulsar **Confirmar**.

El asistente no presenta una lista interminable de variantes. Resuelve la
combinación a partir de los atributos seleccionados, reutiliza una variante
existente, reactiva una archivada o crea dinámicamente la combinación cuando
la configuración del producto lo permite.

El configurador siempre abre sin opciones marcadas. Aunque Odoo mantenga una
variante provisional oculta en la línea, esa variante no se interpreta como
una selección del vendedor.

La vista definitiva sigue el patrón visual del configurador de Ventas: imagen
del producto, casillas para opciones acumulables, desplegables para atributos
de variante, cantidad, precio y total.

La factura debe permanecer en borrador durante la configuración.

El guardado automático no confirma ni publica la prefactura. Si faltan campos
obligatorios, el sistema mantiene la edición y solicita completarlos antes de
abrir el configurador.

## 8. Declarar una medida excepcional como producto especial

Una medida excepcional no debe convertirse en un valor global ni aparecer en
los desplegables normales.

1. Abrir **Armar producto** desde la línea de factura.
2. Configurar los atributos normales que sirven como base.
3. Marcar **Declarar como producto especial**.
4. Escribir Ancho y Alto especiales.
5. Completar especificaciones e instrucciones de fabricación.
6. Pulsar **Confirmar**.
7. Revisar y completar componentes, operaciones y centros de trabajo de la
   LDM especial.
8. Pulsar **Crear producto y LDM**.

El sistema crea un producto especial exclusivo y conserva como origen la
configuración normal seleccionada. Ancho y Alto se guardan en el producto, la
factura, la LDM y la orden de fabricación, pero no se crean como valores de
atributo ni contaminan el catálogo de medidas.

## 9. Administración y correcciones

Un administrador puede abrir:

**Inventario → Productos → Variantes del producto**

Desde la variante puede corregir:

- referencia interna;
- código de barras;
- precio adicional;
- estado activo o archivado;
- información logística permitida por Odoo.

La pestaña **Variante personalizada** muestra:

- valor personalizado;
- factura de origen;
- última entrega;
- fecha prevista de archivo.

### Corregir el texto de una medida

Si el valor todavía no tiene historial, el administrador puede corregirlo en
la configuración del atributo. Si ya fue utilizado en facturas, inventario o
fabricación, se recomienda crear el valor correcto, sustituirlo en documentos
en borrador y archivar la variante incorrecta.

### Cambiar atributos utilizados

No se debe cambiar directamente el modo de creación de un atributo que ya está
asociado a productos. El procedimiento seguro es:

1. crear un atributo nuevo con la configuración correcta;
2. agregarlo de forma controlada a las plantillas correspondientes;
3. validar las combinaciones generadas;
4. conservar el atributo anterior para el historial;
5. migrar solamente documentos que permanezcan en borrador.

## 10. Archivo de variantes personalizadas

Después de completar una entrega, la variante personalizada recibe una fecha
de archivo 30 días posterior.

El proceso automático solo la archiva cuando:

- no tiene existencias disponibles;
- no tiene movimientos de inventario abiertos;
- no aparece en facturas de cliente en borrador.

Se archiva únicamente la variante. La plantilla, el valor del atributo y los
documentos históricos se conservan. Si la misma combinación vuelve a
solicitarse, el selector puede reactivar la variante archivada.

## 11. Controles antes de permitir la venta

El administrador debe comprobar:

- que los atributos que diferencian stock no estén configurados como `Nunca`;
- que las opciones acumulables no generen variantes innecesarias;
- que las referencias internas sean únicas;
- que cada variante tenga precio adicional correcto;
- que las rutas y unidades de medida pertenezcan a la plantilla;
- que la LDM corresponda a la variante cuando aplique fabricación;
- que el código de barras esté definido antes de imprimir etiquetas.

## 12. Problemas frecuentes

### El atributo muestra “Nunca” bloqueado

Puede estar utilizando `Varias casillas` o ya estar asociado a productos. No se
debe forzar desde PostgreSQL. Debe crearse un atributo dinámico nuevo.

### No aparece el atributo al crear un valor personalizado

El atributo está configurado como `Nunca`, no pertenece a la plantilla o no
tiene una línea activa en el producto.

### La variante ya existe

El sistema debe reutilizarla. Si estaba archivada, será reactivada en lugar de
crear un duplicado.

### El precio no coincide

Revisar el precio base de la plantilla y **Variant Extra Price** en la variante.

### No imprime la etiqueta

Completar la referencia interna o el código de barras de la variante.

## 13. Reglas del configurador guiado

El wizard **Armar producto** aplica estas reglas:

- muestra valores por atributo y no una lista de variantes;
- comienza sin valores preseleccionados;
- exige exactamente una selección en cada atributo generador de variantes;
- admite varias selecciones en atributos informativos configurados como
  `Nunca`;
- conserva esas opciones informativas en la línea de factura y su descripción;
- muestra la variante y precio resultantes antes de aplicar;
- mantiene en el mismo formulario la creación de una medida o valor
  personalizado;
- impide configurar líneas de facturas que ya no estén en borrador.

## 14. Recomendaciones de seguridad

- Probar cambios de atributos en la instancia de pruebas.
- Respaldar la base de datos antes de modificar combinaciones existentes.
- No eliminar variantes con movimientos contables o de inventario.
- Preferir archivar y conservar trazabilidad.
- Actualizar módulos desde la interfaz únicamente después de sincronizar el
  código y reiniciar el servicio siguiendo el procedimiento operativo.
- Validar un producto completo antes de aplicar cambios masivos al catálogo.
