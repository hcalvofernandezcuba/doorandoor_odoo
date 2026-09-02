# Diseño funcional: control de fábrica y reposición por venta

## 1. Objetivo

`doorandoor_fabrica_control` debe reproducir en Odoo el proceso físico real de
DoorAndDoor sin crear inventarios paralelos ni sustituir los documentos nativos.
Cada entrega física se respaldará con movimientos de `stock` y cada fabricación
con `mrp.production` y, cuando corresponda, `mrp.workorder`.

El módulo coordinará dos fuentes de demanda:

1. Fabricación destinada a un cliente y vinculada a venta, factura y pago.
2. Fabricación para reponer en un almacén las unidades vendidas desde su stock.

Ambas fuentes compartirán el proceso interno de fábrica. Cambiarán el origen de
la necesidad, la prioridad, la reserva comercial y el destino final.

## 2. Principios obligatorios

- La validación del medio de pago libera la demanda del cliente para producción.
- Una factura o pedido sin salida física no genera reposición de stock.
- La reposición se calcula sobre cantidades realmente entregadas al cliente.
- Una misma salida nunca puede generar dos reposiciones.
- Los consumos, semiterminados y productos acabados usan movimientos nativos.
- Las entregas parciales conservan saldo y generan backorder cuando corresponda.
- El producto terminado solo queda disponible cuando el almacén valida su recepción.
- Cada documento conserva usuario, fecha, cantidades, origen, destino y firmas.
- La automatización debe ser idempotente y auditable.

## 3. Vía A: fabricación para un cliente

```text
Factura o prefactura
        ↓
Validación del medio de pago
        ↓
Liberación para producción
        ↓
Orden de fabricación
        ↓
Solicitud de materiales al almacén
        ↓
Entrega documentada a Maquinado
        ↓
Maquinado de partes y piezas
        ↓
Entrega documentada a Ensamblaje
        ↓
Ensamblaje por unidad
        ↓
Validación del producto terminado
        ↓
Entrega documentada al almacén
        ↓
Reserva y despacho al cliente
```

### 3.1 Liberación por pago

La liberación registrará:

- factura o prefactura de origen;
- pedido y cliente;
- medio de pago validado;
- usuario y fecha de validación;
- productos, variantes y cantidades liberadas;
- almacén y centro de producción;
- órdenes de fabricación generadas.

El pago autoriza la producción, pero no consume inventario por sí solo.

### 3.2 Estados de la orden

```text
Liberada
→ Materiales solicitados
→ Materiales entregados
→ En maquinado
→ Pendiente de ensamblaje
→ En ensamblaje
→ Terminada parcialmente
→ Terminada
→ Entregada al almacén
```

## 4. Proceso interno común de fábrica

### 4.1 Solicitud de materiales

Producción emitirá una solicitud calculada desde la LdM. La solicitud no
descontará existencias; permitirá comprobar disponibilidad, faltantes,
cantidades preparadas y responsables.

Documento imprimible: **Solicitud de materiales para fabricación**.

### 4.2 Entrega del almacén a Maquinado

La salida física se validará mediante una transferencia interna:

```text
Existencias del centro de producción → Maquinado
```

Admitirá entregas parciales, diferencias, lotes, series y backorders.

Documento imprimible: **Vale de salida de materiales a Maquinado**.

### 4.3 Maquinado

Maquinado registrará materiales recibidos, cantidades procesadas, piezas
buenas, rechazo, desperdicio, retrabajo, operador, máquina y tiempos.

Cuando las piezas se entreguen físicamente a otro responsable se tratarán como
productos semiterminados. Esto permitirá inventario, entregas parciales y
trazabilidad entre Maquinado y Ensamblaje.

Documento imprimible: **Parte de producción de Maquinado**.

### 4.4 Entrega de Maquinado a Ensamblaje

Se respaldará mediante movimiento interno:

```text
Maquinado → Ensamblaje
```

Registrará OF, piezas, cantidades buenas y rechazadas, responsables, fecha y
firmas.

Documento imprimible: **Vale de entrega a Ensamblaje**.

### 4.5 Ensamblaje y terminación por unidad

Cada unidad podrá terminarse sin esperar al total de la OF. Se registrarán
producto, variante, ensamblador, serie, piezas utilizadas, control de calidad,
fecha, hora y observaciones.

La orden mostrará cantidades solicitadas, maquinadas, en ensamblaje,
terminadas, entregadas al almacén y pendientes.

Documento imprimible: **Parte de ensamblaje y terminación**.

### 4.6 Entrega del producto terminado al almacén

Cada entrega del ensamblador generará o alimentará una transferencia:

```text
Ensamblaje → Productos terminados
```

El producto quedará disponible solamente después de que el almacenero valide
su recepción. Se distinguirá producto ensamblado, pendiente de recibir,
recibido y rechazado por calidad.

Documento imprimible: **Vale de entrega de producto terminado al almacén**.

## 5. Vía B: reposición del stock vendido

### 5.1 Disparador

La necesidad se generará al validar la entrega real al cliente:

```text
Venta desde stock del almacén
        ↓
Salida validada al cliente
        ↓
Solicitud de reposición por la cantidad entregada
```

Reglas:

- Entrega total: repone el total entregado.
- Entrega parcial: repone solo la parte entregada.
- Backorder: cada entrega posterior genera su parte pendiente.
- Cancelación sin entrega: no genera reposición.
- Nota de crédito sin devolución física: no altera la reposición.
- Devolución física: compensa una necesidad pendiente o el plan futuro.

### 5.2 Solicitud de reposición

Cada necesidad conservará:

- almacén solicitante y centro de producción;
- producto y variante;
- entrega, pedido, factura y cliente de referencia;
- cantidad vendida y cantidad por reponer;
- cantidades planificada, fabricada, enviada y recibida;
- prioridad y fecha requerida;
- OF, despacho y recepción relacionados.

Estados:

```text
Pendiente
→ Agrupada
→ En fabricación
→ Fabricada parcialmente
→ Pendiente de envío
→ En tránsito
→ Recibida parcialmente
→ Completada
```

### 5.3 Agrupación productiva

Cada entrega genera una necesidad exacta, pero producción podrá agruparlas por
producto, variante, almacén destino, fecha y prioridad. Una OF puede cubrir
varias solicitudes sin perder su trazabilidad.

La fabricación también podrá consolidarse entre almacenes. Al terminar se
separarán los traslados por destino.

Ejemplo:

```text
Orlando vendió 2
Doral vendió 3
Orlando vendió 4

Necesidad Orlando: 6
Necesidad Doral: 3
Fabricación consolidada posible: 9
Despacho final: 6 a Orlando y 3 a Doral
```

### 5.4 Distribución desde el centro de producción

```text
Producto terminado
→ Separación por almacén destino
→ Despacho interalmacén
→ Mercancía en tránsito
→ Recepción en el almacén solicitante
→ Reposición completada
```

Se reutilizará el flujo de traslados controlados de
`doorandoor_process_control`, incluyendo recepción separada, tránsito y avisos
al almacén receptor.

### 5.5 Política por producto y almacén

Cada combinación podrá definir:

- reposición exacta por venta;
- reposición agrupada por período o lote mínimo;
- regla nativa de mínimo/máximo;
- reposición manual;
- sin reposición automática.

La configuración incluirá centro productor, almacén destino, cantidad mínima,
múltiplo, días de agrupación, stock de seguridad, ruta y prioridad.

## 6. Control contra duplicados

Cada movimiento de salida al cliente controlará:

```text
Cantidad entregada
Cantidad que generó reposición
Cantidad pendiente de generar
Cantidad ya fabricada
Cantidad enviada
Cantidad recibida
```

La clave de origen incluirá movimiento de stock, producto, almacén y cantidad.
Repetir una llamada, reabrir una vista o ejecutar nuevamente una tarea no podrá
duplicar solicitudes.

## 7. Documentos imprimibles

1. Orden de producción liberada.
2. Solicitud de materiales según LdM.
3. Vale de salida del almacén a Maquinado.
4. Parte de trabajo de Maquinado.
5. Vale de entrega de Maquinado a Ensamblaje.
6. Parte de trabajo del ensamblador.
7. Certificación o control del producto terminado.
8. Vale de entrega del producto terminado al almacén.
9. Solicitud de reposición por venta.
10. Plan de fabricación por almacén.
11. Traslado del centro productor al almacén destino.
12. Reporte consolidado de trazabilidad.

Todos mostrarán responsables, fechas, cantidades, documentos de origen y
destino, observaciones y espacios de firma cuando proceda.

## 8. Indicadores

El tablero consolidado mostrará por producto y almacén:

```text
Vendido | Solicitado | Fabricado | En tránsito | Recibido | Pendiente
```

Para la fabricación interna mostrará:

```text
Solicitado | Entregado a Maquinado | Maquinado | En Ensamblaje
| Terminado | Recibido en almacén | Pendiente
```

## 9. Integraciones

- `doorandoor_control_cobros`: validación del medio de pago.
- `doorandoor_sales_new`: venta, factura y liberación comercial.
- `doorandoor_produccion_almacen`: almacén origen/destino y traslado posterior.
- `doorandoor_process_control`: operaciones interalmacén, tránsito y avisos.
- `mrp`, `stock`, `sale_management` y `account`: fuentes de verdad nativas.

## 10. Fases de implementación

### Fase 1. Fundación

- Modelos de demanda y solicitud de reposición.
- Identificadores, estados, seguridad y trazabilidad.
- Vínculos con venta, factura, entrega, OF y almacenes.

### Fase 2. Reposición por venta

- Detección idempotente de entregas.
- Configuración por producto y almacén.
- Agrupación y creación controlada de OF.

### Fase 3. Materiales y Maquinado

- Solicitud de materiales.
- Transferencia a Maquinado.
- Entregas parciales, faltantes y reportes.

### Fase 4. Ensamblaje y producto terminado

- Semiterminados y entrega a Ensamblaje.
- Terminación por unidad y control de calidad.
- Recepción de producto terminado.

### Fase 5. Distribución y reportes

- Traslados por almacén destino.
- Informes imprimibles y tablero consolidado.
- Pruebas integrales con clientes.

## 11. Decisiones pendientes

- Catálogo exacto de productos semiterminados de Maquinado.
- Ubicaciones físicas definitivas de Maquinado, Ensamblaje y Calidad.
- Momento exacto en que una devolución compensa una reposición.
- Frecuencia y criterio para agrupar necesidades.
- Productos que usarán serie individual y controles de calidad obligatorios.
- Formato corporativo y firmas de cada reporte.
