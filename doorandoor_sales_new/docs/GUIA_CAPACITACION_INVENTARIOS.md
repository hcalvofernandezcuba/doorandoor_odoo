# Capacitación Integral de Inventarios DoorAndDoor

Guía del ciclo físico desde la recepción hasta la entrega, preservando los
movimientos nativos, la trazabilidad por almacén y el control de cantidades.

## Preparación de usuarios y productos

- Asignar al operador el rol Almacenero DoorAndDoor.
- Seleccionar sus almacenes operativos.
- Reservar acceso global para Logística y Administrador/Ajustes.
- Cada variante física debe tener referencia y barcode únicos.
- Confirmar unidad de medida, almacén y ubicación antes de operar.

## Menú de trabajo

```text
Operaciones
└── Almacén
    ├── Recepciones
    ├── Entregas
    ├── Entradas de fábrica
    ├── Traslados
    └── Conteo de inventario
```

Las tarjetas reflejan estados oficiales. No deben moverse manualmente para
simular avances.

## Recepción de compras

1. Compras confirma la orden con su almacén destino.
2. El operador abre la recepción pendiente.
3. Comprueba proveedor, origen, producto, variante y cantidad.
4. Registra solamente la cantidad física recibida.
5. Valida la recepción.
6. Odoo aumenta las existencias y retira la operación de pendientes.

Si falta mercancía, se valida la parte recibida y se crea el backorder por el
saldo. No se registran cantidades ficticias para cerrar el documento.

## Recepción con hanger o móvil

1. Abrir la recepción y el asistente Recibir con hanger.
2. Cargar los productos esperados.
3. Definir normalmente una unidad por lectura.
4. Escanear el barcode de cada variante.
5. Revisar esperado, contado y diferencia.
6. Aplicar el conteo a la recepción.
7. Validar el movimiento nativo.

El asistente cuenta; el inventario cambia al validar la recepción.

## Traslado entre almacenes

1. Logística crea un único traslado con origen, destino, productos y cantidades.
2. El origen lo consulta en Traslados y prepara la salida.
3. El destino lo consulta en Recepciones y recibe actividades de aviso.
4. El destino registra lo realmente recibido.
5. Al validar, las existencias pasan al destino y cesan las alertas.

Las diferencias se gestionan mediante backorder. No se duplica el movimiento.

## Traslado originado por una venta

1. Ventas consulta existencias de otros almacenes.
2. Selecciona el almacén proveedor en la línea comercial.
3. La selección se conserva entre cotización, prefactura y factura.
4. La prefactura confirmada crea la prereserva temporal.
5. Puede cambiarse el almacén antes de confirmar la factura.
6. El traslado real espera el pago total.
7. El despacho al cliente espera que el traslado haya sido recibido.

## Entrada de fábrica

1. Producción completa la MO y genera el producto terminado.
2. El almacenero abre Entradas de fábrica.
3. Comprueba MO, producto, variante, cantidad y destino.
4. Recibe físicamente y valida el movimiento.
5. El producto entra en stock y puede alimentar su entrega.

## Entrega al cliente

La entrega solo se libera con factura publicada, pago oficial total, residual
cero, mercancía disponible y traslados necesarios recibidos.

1. Abrir Entregas y seleccionar Lista para entregar.
2. Pulsar Procesar entrega.
3. Verificar cliente, dirección, factura, almacén, variantes y cantidades.
4. Preparar físicamente la mercancía.
5. Registrar cantidades realizadas y validar cuando realmente sale.

- Entrega completa: pasa a Entregado y descuenta existencias.
- Entrega parcial: crea backorder y muestra solamente el saldo restante.
- Pago parcial o en revisión: no libera una entrega comercial.

## Captación de bisagras y otros insumos por lote

Las bisagras y otros insumos consumidos por cantidad no usan un serial por
unidad. Deben configurarse como **producto almacenable** con seguimiento
**Por lotes**. Cada partida física recibe un número y una sola etiqueta de
lote; sus consumos se descuentan parcialmente hasta agotarla.

### Carga inicial de una partida

1. Confirme producto, variante, unidad de medida y ubicación física.
2. Cree o seleccione un lote exclusivo para esa partida. No reutilice el mismo
   número en otro producto.
3. Imprima una sola etiqueta del lote; su Code128 representa el lote completo.
4. Cree la sesión en **Carga inicial por lote** con una referencia única.
5. Inicie la sesión, escriba la cantidad total en **Cantidad por lectura** y
   escanee una vez la etiqueta.
6. Compruebe producto, lote, contado y existencia resultante antes de revisar.
7. La cantidad se incorpora solamente cuando el responsable valida el ajuste.

### Conteo físico posterior

1. Cree la sesión en **Conteo físico total** para la ubicación exacta.
2. Cuente las unidades restantes del lote.
3. Escriba el total físico en **Cantidad por lectura** y escanee una vez la
   etiqueta del lote.
4. Confirme que la línea corresponde al producto y lote correctos.
5. Al validar, el total contado sustituye la existencia teórica de ese lote.

### Entradas y consumos de fabricación

- Una recepción agrega cantidad mediante su movimiento nativo; imprimir o
  escanear la etiqueta no aumenta inventario.
- Producción consume la cantidad real desde el mismo lote hasta agotarlo.
- Una nueva partida física requiere un lote nuevo, aunque sus atributos sean
  iguales.
- No valide consumos que produzcan existencia negativa; revise primero
  recepción, lote y ubicación.
- Registre en el chatter documento, lote, cantidad, ubicación, usuario y motivo.
- Nunca imprima una etiqueta por cada bisagra ni use una campaña de seriales
  unitarios para estos insumos.

## Controles operativos

- No crear manualmente entregas comerciales.
- No duplicar traslados generados por ventas.
- No modificar existencias para ocultar diferencias de recepción.
- No validar una salida antes de que la mercancía abandone el almacén.
- No entregar una factura sin pago total.
