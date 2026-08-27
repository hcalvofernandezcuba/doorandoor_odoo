# Guía integral de configuración de productos DoorAndDoor

## 1. Objetivo

Esta guía define cómo debe configurar un administrador cada clase de producto
utilizada en DoorAndDoor. Una configuración correcta evita listas interminables
de variantes, errores de stock, LDM incorrectas y bloqueos en fabricación.

## 2. Elegir el tipo correcto

- **Producto normal sin variantes:** artículo fijo de compra, stock o venta.
- **Producto normal con variantes:** artículo reutilizable con opciones
  comerciales previamente conocidas.
- **Transformado:** modificación excepcional de un producto terminado que ya
  existe físicamente en stock.
- **Plantilla maestra:** modelo técnico WINDOWS o DOORS que aporta receta,
  operaciones y reglas, pero no se vende ni mantiene stock.
- **Especial o Ventas Unicas de producto unico** producto nuevo creado desde una venta, con
  atributos y valores libres, fabricado desde receta propia.

## 3. Producto normal sin variantes

1. Ir a **Ventas o Inventario > Productos > Productos**.
2. Crear el producto y completar nombre, referencia y categoría.
3. Activar **Puede ser vendido** si corresponde.
4. Activar **Puede ser comprado** solo si se compra.
5. Elegir tipo almacenable cuando deba controlar existencias.
6. Configurar unidad de medida, impuestos, precio y costo.
7. Configurar rutas de stock, compra o fabricación.
8. Guardar y probar una línea comercial.

No debe marcarse como plantilla maestra ni permitir transformaciones si esos
flujos no corresponden.

## 4. Producto normal con variantes

### 4.1 Crear atributos

1. Ir a **Ventas > Configuración > Atributos**.
2. Crear atributos reutilizables como Color, Cristal, Modelo, Ancho o Alto.
3. Elegir el modo de visualización apropiado.
4. Elegir el modo **Crear variantes** según la matriz de la sección 4.2.
5. Agregar valores comerciales conocidos.

### 4.2 Tipo de creación de variantes

El tipo se configura en la ficha del **atributo**, no en cada valor. Su elección
determina si Odoo crea ítems almacenables y si estos aparecen en inventario y en
el asistente de labels.

| Crear variantes | Comportamiento | Configurador de Ventas | Stock y labels |
|---|---|---|---|
| **Al instante** | Crea todas las combinaciones al guardar el producto. | Permite seleccionar la combinación en el asistente. | Todas las combinaciones creadas aparecen inmediatamente como variantes y pueden imprimirse. |
| **De forma dinámica** | Crea una combinación solamente cuando se utiliza por primera vez. | Es el modo recomendado para el configurador guiado y catálogos amplios. | Solo aparecen y se imprimen las variantes que ya fueron configuradas/creadas; no las posibilidades todavía inexistentes. |
| **Nunca** | El valor no genera una variante almacenable diferente. | Puede actuar como opción descriptiva, según el configurador nativo. | No proporciona stock, barcode ni label independiente por valor. |

#### Regla DoorAndDoor vigente

- Usar **Al instante** para los atributos comerciales de DoorAndDoor. Esta es
  la política aprobada actualmente para que todas las variantes físicas existan
  antes de vender y estén disponibles en inventario, barcode y labels.
- No usar **De forma dinámica** mientras permanezca vigente esta política.
- Antes de agregar muchos valores, calcular el total de combinaciones y dividir
  el producto en familias administrables si puede exceder el límite de Odoo.
- No usar **Nunca** para una característica que deba identificar una variante
  física, llevar stock separado, barcode propio o label propio.
- No mezclar arbitrariamente modos dentro de una familia de productos. El modo
  pertenece al atributo y afecta a todos los productos que lo utilizan.

Antes de utilizar **Al instante**, calcular el total:

`Total de variantes = valores atributo 1 × valores atributo 2 × ...`

Ejemplo: 10 anchos × 10 altos × 4 colores × 3 cristales generan 1.200
variantes. Ese caso debe permanecer **Dinámico**. En cambio, 2 colores × 2
modelos generan 4 variantes y pueden crearse **Al instante** si se necesitan
todos sus labels antes de vender.

### 4.3 Asociar atributos al producto

1. Abrir la plantilla del producto.
2. Ir a **Atributos y variantes**.
3. Agregar una línea por atributo.
4. Seleccionar los valores permitidos.
5. Guardar.
6. Revisar las variantes generadas. En modo dinámico inicialmente puede existir
   solo la variante base o ninguna combinación comercial materializada.
7. Completar referencia interna, barcode y precio adicional cuando proceda.

### 4.4 Resultado comercial

En cotización, prefactura o factura el vendedor selecciona el producto base.
El configurador guiado permite elegir valores y agrega una sola variante. La
lista normal no debe mostrar todas las combinaciones.

El configurador guiado funciona con atributos **Al instante** y mantiene la
selección ordenada por producto base. Todas las combinaciones ya existen como
variantes reales, aunque la lista comercial muestre solamente el producto base.

## 5. Producto que admite Transformados

Utilizar este caso cuando existe un producto terminado en stock y se va a
desarmar o modificar para cumplir una solicitud excepcional.

1. Abrir el producto terminado base.
2. Confirmar que es almacenable.
3. Mantener **Puede ser vendido** activo.
4. Activar **Permitir productos transformados**.
5. Configurar sus atributos y variantes normales.
6. Confirmar que existe stock del producto terminado que será consumido.

Al crear el Transformado:

- se crea otro producto;
- conserva trazabilidad con el producto base;
- su LDM consume una unidad del producto terminado base;
- no utiliza la receta de una plantilla maestra;
- queda excluido de futuras listas comerciales;
- puede archivarse después del período sin movimientos configurado.

Para impedir transformaciones, desactivar la casilla. Debe permanecer visible
para administradores incluso cuando esté desactivada.

## 6. Plantilla maestra WINDOWS o DOORS

La plantilla maestra es técnica. No representa un producto disponible para
venta ni una existencia física.

1. Crear un producto con nombre claro, por ejemplo `MASTER WINDOW SH`.
2. Desactivar **Puede ser vendido**.
3. No registrar stock ni usarlo en transferencias.
4. Abrir **Plantilla de fabricación**.
5. Activar **Plantilla maestra de fabricación**.
6. Seleccionar familia `WINDOWS` o `DOORS`.
7. Escribir el nombre comercial base del producto resultante.
8. Opcionalmente elegir el componente automático y cantidad, normalmente
   `Bisagra` con cantidad `3`.
9. Guardar.

Las plantillas maestras se excluyen de la lista normal de productos en Ventas.
Solo aparecen en **Agregar producto especial**.

## 7. Atributos de la plantilla maestra

Los atributos configurados en la plantilla se precargan en el asistente del
Especial, pero no lo limitan.

1. Agregar los atributos frecuentes de la familia.
2. Utilizar nombres estables: Ancho, Alto, Cristal, Color, Modelo, Marco.
3. Configurar valores técnicos iniciales si Odoo los exige para guardar la
   línea de atributo.
4. Preferir creación dinámica para evitar combinaciones innecesarias.

En el asistente el vendedor puede eliminar esas filas, agregar otros atributos
existentes o escribir atributos totalmente nuevos.

## 8. LDM (Lista de Materiales) maestra completa

Crear una LDM maestra cuando exista una receta productiva real reutilizable.

1. Crear la LDM para la plantilla maestra.
2. Agregar materias primas reales.
3. No agregar el producto maestro como componente de sí mismo.
4. Configurar unidades y cantidades base.
5. Agregar operaciones, centros de trabajo, tiempos y secuencia.
6. Configurar reglas dimensionales si una medida modifica cantidades.

Fórmula de regla:

`Cantidad = cantidad base + (valor numérico × factor) + merma`

El componente de una regla debe existir en la LDM. Si una regla obsoleta apunta
a otro componente, se omite y se registra una advertencia sin bloquear la
venta.

## 9. LDM automática mínima

La LDM maestra no es obligatoria para el flujo Bayú de Lola.

Si el vendedor crea un Especial sin receta completa:

1. El sistema crea una LDM propia y editable.
2. Agrega tres unidades del componente automático por unidad fabricada.
3. Si no se configuró componente, busca `bisagras` y después `bisagra`.
4. Si ninguno existe, crea un componente genérico.
5. Producción puede editar posteriormente la LDM.

La creación de esta receta no obliga a ejecutar una MO si el flujo comercial
nunca alcanza sus condiciones.

## 10. Producto Especial 

El Especial es un producto completamente nuevo. La plantilla aporta estructura
productiva, pero no limita sus características comerciales.

### 10.1 Creación desde Ventas

1. Abrir una cotización, prefactura o factura en borrador.
2. Pulsar **Agregar producto especial**.
3. Seleccionar la plantilla maestra.
4. Seleccionar la **Configuración base** o variante de referencia.
5. Seleccionar opcionalmente una LDM maestra.
6. Revisar todos los atributos y valores base precargados.
7. Marcar **Modificar** solamente en los atributos que cambiarán.
8. Escribir el nuevo valor únicamente en las filas marcadas.
9. Agregar atributos nuevos cuando el producto lo requiera; estos quedan
   marcados para modificar y necesitan valor.
10. En **Componentes de la receta**, conservar los elementos básicos que
    permanecerán, excluir los que no aplican y ajustar sus cantidades.
11. Agregar componentes nuevos cuando sea necesario.
12. En **Operaciones de fabricación**, conservar o excluir las operaciones
    copiadas desde la LDM maestra.
13. Completar cantidad, precio, especificaciones e instrucciones.
14. Pulsar **Crear especial y agregar**.

### 10.2 Casos de uso del asistente

#### Solo cambia una medida

- Elegir la configuración base.
- Marcar únicamente Ancho o Alto.
- Los demás atributos se conservan automáticamente.
- Mantener los componentes básicos y dejar que las reglas dimensionales
  ajusten las cantidades correspondientes.

#### Cambian varios atributos

- Marcar cada atributo modificado.
- Escribir un valor nuevo por cada uno.
- El nombre resultante incluye también los atributos no modificados.

#### Se sustituye un material

- Excluir el componente original en la pestaña de receta.
- Agregar el componente sustituto y su cantidad.
- Verificar la operación donde será consumido después de crear la LDM.

#### Se eliminan operaciones

- Desmarcar las operaciones que no forman parte del nuevo proceso.
- Los componentes asociados a una operación excluida permanecen en la LDM sin
  operación asignada y Producción puede reasignarlos posteriormente.

#### No existe LDM maestra

- Dejar LDM maestra vacía.
- El sistema crea la receta automática mínima configurada para la plantilla.

#### Se parte de LDM maestra

- Debe conservarse o agregarse al menos un componente.
- La selección crea una LDM independiente y nunca modifica la receta maestra.

### 10.3 Resultado

- Producto almacenable independiente.
- Referencia interna `ESP-año-secuencia`.
- Barcode EAN-13 numérico único.
- Atributos y valores propios.
- LDM copiada o automática.
- Familia y plantilla de origen trazables.
- Documento y línea comercial de origen.
- Exclusión de nuevas selecciones comerciales.
- Archivado después de 30 días sin movimientos, stock, ventas, facturas ni MO
  abiertas.

## 11. Nombre e impresión del Especial

El nombre interno conserva código, nombre y configuración. En documentos
impresos debe verse de forma legible:

```text
[ESP-2026-00001] WINDOW SH Especial

Ancho: 36
Alto: 80
Cristal: Gray
Color: Blanco
```

Cada atributo se imprime debajo del producto según su tipo.

## 12. Barcode y etiquetas

### 12.1 Requisitos

1. Confirmar que el producto tiene referencia interna.
2. Confirmar que cada variante real tiene referencia interna o barcode.
3. Para Especiales y Transformados, confirmar que el barcode automático EAN-13
   fue creado correctamente.
4. En el asistente de etiquetas utilizar preferentemente **Variantes**.
5. Imprimir una etiqueta de prueba.
6. Escanear y confirmar el producto resultante.

### 12.2 Por qué el asistente puede mostrar cero variantes

El asistente de labels lista registros reales de `product.product`; no calcula
combinaciones posibles de manera teórica. Un producto configurado previamente
como **Dinámico** puede mostrar `Variantes seleccionadas: 0` aunque la plantilla
tenga valores permitidos.

No es pérdida de configuración. Significa que esas combinaciones todavía no
han sido conformadas en Ventas ni creadas como ítems almacenables.

### 12.3 Corrección de productos heredados como dinámicos

1. Revisar el número total de combinaciones.
2. Cambiar administrativamente los atributos a **Al instante**.
3. Guardar o regenerar las variantes del producto.
4. Generar barcodes únicamente para las variantes que no tengan uno.
5. Confirmar que todos los barcodes sean únicos.
6. Volver a **Labels de productos** y comprobar las variantes asociadas.

Si el total excede el límite permitido, no forzar la creación: separar el
catálogo en varias plantillas de producto antes de continuar.

### 12.4 Cuándo deben aparecer todas las variantes antes de vender

Para imprimir anticipadamente los labels de todas las combinaciones, los
atributos deben estar en **Al instante**, el producto debe generar todas sus
variantes y cada una debe tener referencia interna o barcode único.

No editar manualmente el barcode automático salvo procedimiento aprobado por
Administración.

## 13. Configuración de fabricación

Para productos que deben ir a MO:

1. Configurar una ruta que incluya fabricación, o usar la política forzada por
   fabricación definida en DoorAndDoor.
2. Confirmar almacén, tipo de operación y ubicaciones.
3. Confirmar LDM activa y unidad de medida.
4. Revisar componentes y operaciones.
5. Probar el umbral de pago sobre una factura nueva.

La fabricación se libera al alcanzar el 50 % acumulado del total de la factura.
El despacho sigue requiriendo pago completo.

## 14. Edición administrativa

Un administrador puede:

- cambiar si un producto permite Transformados;
- corregir atributos y valores normales;
- editar una LDM maestra;
- editar la LDM propia de un Especial;
- cambiar operaciones e instrucciones;
- revisar barcode, referencia y trazabilidad;
- archivar manualmente cuando no existan movimientos abiertos.

No debe convertir un Especial ya utilizado en plantilla maestra ni sustituir
su producto base después de movimientos contables o de stock.

## 15. Errores frecuentes

### La plantilla no aparece

- Confirmar que está activa.
- Confirmar **Plantilla maestra de fabricación**.
- Abrir el botón **Agregar producto especial**, no la lista normal.
- Actualizar el módulo y recargar assets.

### No aparecen atributos precargados

- Confirmar que las líneas están en la misma plantilla seleccionada.
- Verificar productos duplicados con nombres similares.
- Agregar manualmente atributos desde el asistente si el Especial requiere
  características diferentes.

### La línea queda roja

- Confirmar que el producto y la variante fueron creados.
- Revisar el log del momento exacto.
- Confirmar que no quedó una fila con valor pero sin atributo.

### Labels muestra cero variantes

- Revisar en **Ventas > Configuración > Atributos** el campo **Crear variantes**.
- Si está **De forma dinámica**, convertirlo administrativamente a **Al
  instante** después de revisar el total de combinaciones.
- Confirmar que la variante creada está activa.
- Confirmar que tiene referencia interna o barcode.
- Confirmar que Odoo generó todas las variantes después del cambio.
- No usar **Nunca** cuando se requiera stock o label por combinación.

### Error de LDM

- Revisar componentes y unidades.
- Eliminar o corregir reglas obsoletas.
- Dejar la LDM maestra vacía para utilizar la receta mínima si ese es el flujo
  aprobado.

## 16. Matriz de decisión rápida

```text
¿El producto ya existe exactamente?
  Sí -> Producto normal.
  No -> ¿Existe terminado en stock y solo se modificará?
        Sí -> Transformado.
        No -> ¿Nace desde una receta/familia WINDOWS o DOORS?
              Sí -> Especial desde plantilla maestra.
              No -> Crear y configurar un producto normal nuevo.
```

## 17. Cierre de configuración

Antes de entregar un producto al vendedor, probar selección, precio, stock,
variante, impresión, barcode, ruta, LDM y comportamiento del pago. Una ficha
incompleta no debe pasar al catálogo operativo.
