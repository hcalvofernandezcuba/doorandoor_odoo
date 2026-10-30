# Guía operativa diaria de Inventario DoorAndDoor

Esta guía describe cómo recibir, trasladar, contar y entregar mercancía en el
trabajo diario. El principio general es sencillo: registrar lo que ocurrió
físicamente y validar el documento nativo de Odoo que corresponde. Escanear o
imprimir un documento nunca sustituye su validación.

## 1. Antes de comenzar el turno

1. Confirme que está en la compañía correcta.
2. Verifique que su usuario tenga el rol **Almacenero DoorAndDoor** y los
   almacenes donde trabajará.
3. Revise **Operaciones → Almacén**: Recepciones, Entregas, Entradas de fábrica,
   Traslados y Conteo de inventario.
4. Compruebe que cada variante física tenga referencia y barcode únicos.
5. No cambie ubicaciones, cantidades ni estados solo para hacer desaparecer una
   alerta. Corrija el documento que representa el movimiento real.

## 2. Recibir una compra

1. Abra **Operaciones → Almacén → Recepciones**.
2. Localice la recepción por proveedor o documento origen.
3. Compruebe almacén, ubicación, producto, variante y cantidad esperada.
4. Registre únicamente la cantidad que llegó físicamente.
5. Valide la recepción.
6. Si llegó menos, acepte el backorder para conservar pendiente el saldo.

No complete cantidades faltantes para cerrar el documento. El inventario solo
aumenta cuando se valida la recepción.

## 3. Recibir con hanger o teléfono

1. Abra la recepción y pulse **Recibir con hanger**.
2. Cargue los productos esperados.
3. Mantenga **Cantidad por lectura** en `1`, salvo que el paquete represente
   otra cantidad conocida.
4. Pulse **Usar cámara** y encuadre el Code128 completo dentro de la guía
   horizontal.
5. Espere la confirmación visual de producto, barcode y cantidad acumulada
   antes de escanear la unidad siguiente.
6. Si no hay cámara, escriba el barcode y use el botón de registro manual.
7. Revise esperado, contado y diferencia; aplique el conteo a la recepción.
8. Vuelva al movimiento y valídelo cuando la mercancía esté recibida.

El lector evita lecturas parciales, pero el operador debe mantener la etiqueta
plana, iluminada y completa en la imagen. El escaneo prepara cantidades; la
validación del movimiento es la que actualiza existencias.

## 4. Trasladar mercancía entre almacenes

1. Logística crea un solo traslado con origen, destino y cantidades correctas.
2. El almacén de origen prepara la mercancía contra ese documento.
3. El almacén de destino abre la recepción asociada y registra lo recibido.
4. Si hay diferencia, use backorder para el saldo.
5. Valide solo cuando se complete el cambio físico de custodia.

No cree una segunda transferencia para sustituir la ya generada por una venta.
En las ventas con almacén proveedor, el traslado se libera después del pago
total y la entrega al cliente espera que el destino haya recibido la mercancía.

## 5. Recibir producto terminado de Fábrica

1. Abra **Operaciones → Almacén → Entradas de fábrica**.
2. Verifique OF, producto, variante, cantidad y almacén de destino.
3. Compare las unidades y etiquetas con el documento entregado por Fábrica.
4. Registre la cantidad física recibida y valide el movimiento.
5. Informe cualquier rechazo o diferencia antes de disponer del producto.

La terminación de la OF y la recepción en almacén son controles distintos. No
entregue al cliente un producto que todavía no figure disponible en su almacén.

## 6. Preparar y validar una entrega

La entrega comercial queda disponible cuando la factura está publicada y
pagada totalmente, el residual es cero, hay mercancía y los traslados previos
han sido recibidos.

1. Abra **Operaciones → Almacén → Entregas** y filtre **Lista para entregar**.
2. Pulse **Procesar entrega**.
3. Compruebe cliente, dirección, factura, almacén, variante y cantidad.
4. Prepare la mercancía y registre la cantidad que realmente saldrá.
5. Valide en el momento de la salida física.
6. Si la salida es parcial, conserve el backorder con el saldo pendiente.

Nunca cree manualmente una entrega comercial ni valide una salida antes de que
la mercancía abandone el almacén.

## 7. Realizar un conteo físico

### Preparación

1. Detenga entradas, salidas y traslados en la ubicación que se contará.
2. Abra **Operaciones → Almacén → Conteo de inventario**.
3. Cree una sesión para una ubicación interna exacta.
4. Pulse **Iniciar y cargar existencias**. Esta acción congela la cantidad
   teórica que se comparará con el conteo.

Una sesión no incluye automáticamente las sububicaciones. Cree una sesión por
cada ubicación que deba auditarse.

### Conteo con cámara o lector

1. Indique normalmente `1` como cantidad por lectura.
2. Pulse **Usar cámara** y escanee cada Code128 una sola vez.
3. Confirme en **Productos contados** el último producto, la hora, el esperado,
   el contado y la diferencia.
4. Use la entrada escrita si falla la cámara.
5. Para un producto ausente registre expresamente cero; no deje la línea sin
   contar.

No mezcle en una misma línea el conteo directo de variantes con el conteo de
sus componentes. Si existen lotes, paquetes o propietarios, registre la
cantidad en el detalle correcto.

### Carga inicial mediante producto y atributos

Cuando la mercancía aún no tiene existencia cargada o resulta difícil localizar
la variante entre miles de combinaciones:

1. Abra **Physical Counts → Count Sessions** y cree una sesión para la
   ubicación interna exacta.
2. Pulse **Start and Load Stock**. Una ubicación vacía puede comenzar sin
   líneas.
3. En **Barcode Capture**, pulse **Agregar producto configurado**.
4. Seleccione primero la plantilla y luego un valor para cada atributo.
5. Revise la variante resultante, existencia actual y ubicación.
6. Escriba la cantidad física total encontrada.
7. Use **Agregar y continuar** para registrar el producto siguiente o
   **Agregar y cerrar** para volver a la sesión.
8. Revise las líneas en **Variants / Adjustment** antes de pasar a revisión.

Un atributo dinámico, como `swing`, crea la variante real solamente cuando se
confirma una combinación nueva. Esa variante puede tener stock, barcode y
label propios. El selector no crea cantidades reales hasta que un responsable
valida el ajuste.

### Revisión y ajuste

1. Pulse **Revisar** al terminar el recorrido físico.
2. Analice todas las diferencias y vuelva a conteo si necesita corregir.
3. Documente incidencias en notas o chatter.
4. Un usuario **Inventory Count Manager** pulsa **Validar ajuste**.

Solo **Validar ajuste** modifica el inventario real. El operador que cuenta no
debe aprobar sus propias diferencias si el procedimiento interno exige una
segunda revisión.

## 8. Imprimir labels de variantes

1. Abra la plantilla del producto y pulse **Labels de productos**.
2. Seleccione **Variantes** o **Producto y variantes**.
3. Revise referencia, barcode y atributos de las variantes seleccionadas.
4. Indique almacén y copias por variante.
5. Imprima cada lote indicado por el asistente; cada PDF admite hasta 50
   labels.
6. Use para conteo el label individual de la variante, no el label general de
   la plantilla marcado como no válido para inventario.

Si falta el barcode de una variante, use **Generar barcode**. El sistema genera
uno solo cuando el campo está vacío y nunca reemplaza automáticamente uno
existente.

### Label único para insumos por lote

Para bisagras, tornillos u otros insumos administrados por cantidad:

1. El producto debe ser almacenable y usar seguimiento **Por lotes**.
2. Registre el lote real en la recepción o cree el lote autorizado para la
   carga inicial.
3. Imprima una sola etiqueta por lote, aunque contenga muchas unidades.
4. En un conteo, escriba la cantidad física en **Cantidad por lectura** y
   escanee una vez el Code128 del lote.
5. Confirme que la línea resultante conserva producto, lote y ubicación.
6. En carga inicial la cantidad se suma; en conteo físico total sustituye la
   existencia teórica del lote cuando el responsable valida.

No use campañas de seriales unitarios para estos insumos. Una partida nueva
requiere un lote nuevo; los consumos de fábrica descuentan parcialmente del
mismo lote y deben quedar respaldados por la orden de fabricación.

## 9. Cierre del turno

1. Revise recepciones y entregas iniciadas que aún no estén validadas.
2. Compruebe backorders creados por cantidades parciales.
3. Confirme que no queden sesiones de conteo abandonadas en estado Contando.
4. Entregue al siguiente turno los documentos, diferencias e incidencias
   pendientes, identificados por su número de Odoo.

## 10. Qué hacer ante una incidencia

- **Barcode no reconocido:** confirme que corresponde a una variante incluida
  en el documento y que no está leyendo un fragmento de otro código.
- **Cantidad duplicada:** detenga el escaneo, revise Productos contados y
  corrija antes de enviar a revisión.
- **Mercancía parcial:** registre la cantidad real y cree backorder.
- **Almacén o ubicación incorrectos:** no valide; solicite corregir el documento.
- **Diferencia de conteo:** repita el conteo físico y documente el resultado; no
  ajuste existencias por fuera de la sesión.
- **Entrega bloqueada:** revise pago, residual, disponibilidad y traslados; no
  fuerce el estado ni cree otro movimiento.
