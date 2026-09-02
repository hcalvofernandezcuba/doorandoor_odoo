# Revisión de los flujos existentes antes de incorporar lanzadores

## 1. Propósito

Este documento identifica los puntos que actualmente crean o sincronizan
ventas, entregas y órdenes de fabricación. `doorandoor_fabrica_control` no debe
crear un segundo flujo paralelo ni volver a procesar eventos ya cubiertos.

La revisión se realizó antes de implementar lanzadores en el nuevo módulo.

## 2. Módulos que participan actualmente

### `doorandoor_sales_new`

Es el coordinador principal del cumplimiento comercial:

- publica la factura fiscal;
- confirma técnicamente la venta sin lanzar aprovisionamiento nativo duplicado;
- crea y sincroniza `doorandoor.fulfillment.line`;
- calcula cantidades liberadas según pagos;
- decide si una línea va a stock o a fabricación;
- crea pickings de cliente u órdenes de fabricación;
- vincula factura, venta, línea, picking y OF;
- sincroniza cantidades realmente entregadas al validar el picking;
- al terminar una OF prepara el picking de salida si el pago permite entregar.

### `doorandoor_control_cobros`

Controla el momento financiero que permite avanzar:

- impide liberar mientras existan controles de cobro pendientes;
- recalcula el estado operativo después de validar pagos;
- considera pago total para productos servidos desde stock;
- permite liberar fabricación al alcanzar el 50 % del total validado;
- conserva el requisito de pago total antes de entregar al cliente.

### `doorandoor_produccion_almacen`

Extiende las OF creadas por el cumplimiento:

- toma de la venta el almacén de origen;
- toma el almacén de entrega definido comercialmente;
- incorpora ambos almacenes a la OF;
- al terminar fabricación puede crear un traslado interno al almacén destino;
- hace que el picking de cliente use el almacén de entrega correspondiente.

### `doorandoor_special_products`

Asegura que los productos especiales:

- tengan una LdM validada antes de publicar la factura;
- usen siempre la ruta de fabricación;
- usen la LdM especial correspondiente;
- reutilicen o amplíen una OF abierta de la misma línea cuando proceda;
- lleven a la OF medidas, familia e instrucciones de fabricación.

### `doorandoor_process_control`

Controla el traslado interalmacén posterior:

- separa despacho y recepción;
- usa ubicación de tránsito;
- genera recepción en el almacén destino;
- mantiene alertas y actividades hasta la recepción física.

## 3. Flujo vigente de venta a fabricación

```text
Cotización / prefactura
        ↓
Factura fiscal publicada
        ↓
Creación o sincronización de fulfillment
        ↓
Validación de controles de cobro
        ↓
Cálculo de cantidad liberada
        ↓
Decisión stock o MRP
        ↓
Picking de cliente u orden de fabricación
```

### 3.1 Publicación de la factura

`account.move.action_post()` confirma técnicamente la venta vinculada y crea o
sincroniza las líneas de cumplimiento. Si la factura se creó directamente,
puede generar la venta auxiliar necesaria.

La confirmación comercial mantiene desactivado el aprovisionamiento estándar
para que Odoo no cree documentos duplicados antes del pago.

### 3.2 Sincronización por pago

La creación o eliminación de conciliaciones llama a
`_ddsn_sync_release_from_payments()`. El control de cobros también ejecuta esta
sincronización al validar o modificar sus controles.

Si existen controles pendientes, la liberación se bloquea.

### 3.3 Umbral especial de fabricación

Cuando una factura contiene líneas cuya ruta es MRP, el umbral automático es
50 %. Al alcanzar ese acumulado validado,
`_ddc_release_manufacturing_at_threshold()` libera la cantidad total facturada
de las líneas de fabricación y crea o amplía sus OF.

Esto representa una regla comercial deliberada:

```text
50 % validado → se puede fabricar el 100 %
100 % pagado → se puede entregar al cliente
```

El nuevo módulo debe escuchar o extender el documento ya creado; no debe crear
otra OF al detectar el mismo pago.

### 3.4 Terminación de la OF

`mrp.production.button_mark_done()` sincroniza la línea de cumplimiento. Cuando
la factura está totalmente pagada, se crea o completa el picking de salida al
cliente. `doorandoor_produccion_almacen` puede crear antes el traslado interno
al almacén de entrega.

### 3.5 Entrega al cliente

`stock.picking.button_validate()` bloquea una salida de cliente si sus facturas
no están publicadas y totalmente pagadas. Al completar el picking, la cantidad
entregada se toma de la cantidad oficial de la línea de venta, respetando
parciales, backorders y devoluciones.

Este punto es el disparador adecuado para la futura reposición por venta.

## 4. Configuración efectiva revisada en local

```text
payment_release_policy = sequential_line
fulfillment_route_policy = by_stock
partial_stock_policy = split_stock_mrp
picking_creation_policy = per_payment
mrp_creation_policy = per_line
```

## 5. Hallazgos que deben resolverse antes de programar

### 5.1 `by_stock` no evalúa actualmente la disponibilidad

La selección **By Stock Availability** existe y es la configuración local
activa, pero `_ddsn_get_line_route()` no contiene una rama que consulte stock
para esa opción. Al caer al retorno final, clasifica la línea como
`ready_stock`.

Consecuencia: un producto sin existencia no cambia automáticamente a MRP solo
por usar `by_stock`.

### 5.2 La política de stock parcial está declarada pero no aplicada

Las opciones `split_stock_mrp`, `all_mrp`, `wait_full_stock`,
`reserve_partial` y `manual` están en campos y ajustes, pero no se encontraron
ramas funcionales que las ejecuten durante la decisión de ruta.

Antes de reutilizarlas debemos definir cantidades separadas para stock y MRP,
sin sobrecargar el campo de estado de una sola línea.

### 5.3 El 50 % libera el total de fabricación

No es un error técnico, pero debe confirmarse como regla de negocio. El método
actual cambia `qty_released` al total facturado y pone el saldo pendiente de
pago en cero para las líneas MRP.

La entrega continúa protegida por pago total, pero los indicadores de
"cantidad pendiente de pago" dejan de representar literalmente el saldo
financiero de esa línea.

### 5.4 La agrupación actual es por factura

`group_by_product` busca OF abiertas dentro de las líneas de cumplimiento de
la misma factura. No consolida necesidades del mismo producto entre facturas o
almacenes diferentes.

La futura reposición necesitará un planificador propio que agrupe solicitudes
sin perder el movimiento de entrega que las originó.

### 5.5 Existe riesgo de doble traslado posterior

`doorandoor_produccion_almacen` crea un traslado al almacén de entrega al
terminar la OF, y `doorandoor_process_control` transforma traslados entre
almacenes en despacho y recepción controlados.

El nuevo módulo debe enlazarse al traslado ya generado. No debe crear otro
despacho para el mismo producto, OF y almacén.

### 5.6 Producción interna todavía no está documentada por etapas

Los componentes y productos terminados usan movimientos MRP, pero no existen
todavía documentos independientes para:

- solicitud de materiales;
- entrega del almacén a Maquinado;
- entrega de Maquinado a Ensamblaje;
- entrega unitaria del producto acabado al almacén.

Ese es el espacio funcional de `doorandoor_fabrica_control`.

## 6. Puntos de extensión recomendados

### Fabricación para cliente

- Crear el expediente de fábrica cuando `_ddsn_get_or_create_mrp_production()`
  devuelve una OF.
- Usar una relación única por OF para impedir duplicados.
- No volver a interpretar pagos ni crear una segunda OF.

### Reposición por venta

- Escuchar `_action_done()` de pickings salientes.
- Procesar solo movimientos hacia ubicación de cliente y con cantidad hecha.
- Guardar por movimiento la cantidad que ya generó reposición.
- Tratar devoluciones mediante movimientos físicos inversos.

### Etapas internas

- Crear transferencias nativas entre ubicaciones de Existencias, Maquinado,
  Ensamblaje, Calidad y Productos terminados.
- Vincularlas a la OF y al expediente de fábrica.
- Usar backorders nativos para entregas parciales.

## 7. Orden seguro de trabajo local

1. Congelar y probar los lanzadores actuales sin el nuevo módulo.
2. Crear pruebas de regresión para pago 0 %, 49 %, 50 % y 100 %.
3. Probar rutas forzadas de stock, MRP y productos especiales.
4. Probar OF completa, parcial y cancelada.
5. Probar entrega completa, parcial, backorder y devolución.
6. Implementar el expediente de fábrica sin modificar los lanzadores.
7. Implementar reposición con clave idempotente por movimiento.
8. Ejecutar toda la matriz local.
9. Solo con resultado positivo preparar la subida a pruebas.

## 8. Conclusión

El flujo actual ya define correctamente dos fronteras esenciales: fabricación
autorizada por cobro y entrega autorizada por pago total. El nuevo módulo debe
apoyarse en las OF y pickings existentes.

No deben modificarse lanzadores hasta cubrir con pruebas los hallazgos de ruta
por stock, stock parcial, umbral del 50 % y traslado posterior.
