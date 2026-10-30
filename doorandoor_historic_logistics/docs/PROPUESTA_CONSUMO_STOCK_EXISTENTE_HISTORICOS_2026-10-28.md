# Propuesta: ventas históricas consumiendo el inventario real de Odoo

Fecha de análisis: 2026-10-28  
Estado: propuesta funcional para revisión; no implementada  
Entornos modificados: ninguno

## 1. Decisión de Gerencia

Las ventas históricas que se incorporen a Odoo no deben crear existencias nuevas
cuando los productos ya están controlados en el inventario de Odoo.

Se distinguen dos grupos de documentos anteriores:

1. Facturas de Zoho cuyo inventario ya fue gestionado completamente en Zoho.
   Estas facturas no se importarán ni generarán operaciones logísticas en Odoo.
2. Facturas históricas que sí se incorporarán a Odoo para control y entrega.
   Estas deben consumir el stock y los labels existentes en Odoo.

La recepción de regularización desde una ubicación virtual deja de ser el inicio
normal de una venta histórica. Solo podría conservarse como una excepción
supervisada para mercancía físicamente comprobada que realmente no exista aún en
el inventario de Odoo.

## 2. Problema del flujo vigente

Al aprobar un OCR, el flujo actual crea un HDEL y ejecuta siempre una recepción
histórica desde Inventario virtual. Después genera labels nuevos, incrementa la
existencia, crea el traslado cuando los almacenes difieren y finalmente crea la
entrega.

Si la unidad física ya estaba controlada en Odoo con otro label, este recorrido:

- incrementa existencias sin recibir mercancía nueva;
- crea un segundo label para la misma unidad física;
- entrega la unidad nueva ficticia y deja inmóvil la unidad originalmente
  inventariada;
- produce una existencia contable y operativa superior a la existencia física;
- oculta el problema hasta que el almacén agota físicamente esas unidades.

## 3. Nuevo punto de decisión antes de aprobar el OCR

Cada documento debe declarar un tratamiento logístico obligatorio:

- `No migrar: inventario gestionado en Zoho`.
- `Consumir inventario existente de Odoo`.
- `Regularización excepcional de mercancía no inventariada`.

La tercera opción debe quedar restringida a supervisores y exigir justificación,
evidencia física y confirmación expresa. Nunca debe seleccionarse automáticamente
por falta de stock.

Los documentos marcados `No migrar` no crean HDEL, recepciones, traslados,
entregas, stock ni labels. Se recomienda conservar solamente una huella técnica
del PDF o de su referencia para impedir una importación accidental posterior.

## 4. Selección de stock y labels por línea

El origen logístico debe definirse por línea del HDEL, no una sola vez para todo
el documento. Cada línea debe mostrar:

- ITEM y cantidad histórica;
- almacén donde existe actualmente;
- cantidad disponible no reservada;
- labels activos del ITEM en ese almacén;
- ubicación física actual de cada label;
- labels propuestos y labels confirmados;
- cantidad cubierta y faltante;
- ruta resultante: entrega directa o traslado.

Un label es elegible únicamente cuando:

- está activo;
- pertenece al mismo ITEM;
- fue cargado al inventario;
- su almacén y ubicación actuales son internos y coinciden con el origen;
- no está reservado por otra operación activa;
- la existencia real de Odoo respalda la cantidad;
- no fue consumido, entregado o anulado.

El sistema puede proponer labels, pero el supervisor debe poder revisarlos antes
de liberar la operación. La reserva debe ocurrir de forma atómica para impedir
que dos HDEL seleccionen la misma unidad.

Si existe cantidad en Odoo pero faltan labels, no se crea una recepción
histórica. Debe abrirse un control de etiquetado del inventario existente que no
modifique la cantidad y, después, volver a la asignación del HDEL.

## 5. Flujo propuesto

### 5.1 Almacén de stock igual al almacén de entrega

1. OCR y asociación revisada de ITEM.
2. Selección de `Consumir inventario existente de Odoo`.
3. Búsqueda y confirmación de labels existentes.
4. Reserva de esos labels para el HDEL.
5. Creación directa de la entrega desde las ubicaciones reales del almacén.
6. Conteo Hanger de los labels reservados.
7. Validación total o parcial; lo no contado queda pendiente/backorder.
8. Actualización de ubicación/estado de los labels y cierre auditable del HDEL.

No se crea recepción inicial ni labels nuevos.

### 5.2 Almacén de stock diferente al almacén de entrega

1. OCR y asociación revisada de ITEM.
2. Selección, por línea, del almacén que realmente posee cada unidad.
3. Confirmación y reserva de labels existentes.
4. Creación del traslado interno desde las ubicaciones reales.
5. Conteo y validación Hanger del despacho.
6. Recepción destino nativa del traslado, usando los mismos labels.
7. Entrega final al cliente desde el almacén destino.
8. Conteo Hanger y cierre auditable.

La recepción destino sí existe porque corresponde a un traslado real. Lo que se
elimina es la recepción inicial ficticia desde Inventario virtual.

### 5.3 Fuentes mixtas

Un HDEL puede tener líneas o cantidades tomadas de almacenes diferentes. Cada
origen genera solamente su traslado real; las unidades ya existentes en el
almacén de entrega se reservan allí. La entrega final se libera cuando la suma de
unidades recibidas por traslado y unidades reservadas localmente cubre la
cantidad histórica aprobada.

No se crean traslados, recepciones, labels ni existencias ficticias para hacer
coincidir el documento.

## 6. Faltantes y parciales

Si el stock controlado no cubre toda la factura:

- no generar stock ni labels automáticamente;
- mantener la línea en estado `Faltante de inventario`;
- permitir cubrirla desde otro almacén real;
- permitir una entrega parcial con backorder cuando Gerencia lo autorice;
- enviar a fabricación, compra o investigación física por su proceso normal;
- usar regularización excepcional solo cuando exista físicamente una unidad no
  inventariada y haya evidencia aprobada.

## 7. Estados propuestos

- `Excluida: gestionada en Zoho`.
- `En revisión de ITEM`.
- `Buscando inventario Odoo`.
- `Stock localizado parcialmente`.
- `Labels pendientes de confirmar`.
- `Stock reservado`.
- `Traslado pendiente`.
- `Recepción destino pendiente`.
- `Lista para entrega`.
- `Entrega parcial / backorder`.
- `Entregada`.
- `Incidencia de inventario`.

## 8. Cambios de modelo propuestos

Sin implementar todavía:

- En OCR/HIB: `inventory_treatment` y motivo/evidencia de exclusión.
- En HDEL: resumen de cobertura, faltantes y estado de abastecimiento.
- En cada línea HDEL: almacén origen, cantidad asignada, cantidad faltante,
  labels elegibles, labels seleccionados y ruta logística.
- Registro de asignación label-HDEL con restricción única para reservas activas.
- Servicio único que consulte stock, labels, ubicaciones y reservas antes de
  crear cualquier picking.
- Vista de revisión que permita confirmar las propuestas por línea.

No debe reutilizarse `doorandoor.historic.regularization` como camino normal del
nuevo flujo, porque su implementación crea una entrada desde Inventario virtual.

## 9. Cambios de código que deberán evaluarse

- `doorandoor_import_historic_invoices/models/legacy_delivery_ocr.py`:
  impedir que la aprobación inicie siempre la recepción histórica y exigir el
  tratamiento logístico.
- `doorandoor_historic_logistics/models/historical_delivery.py`:
  iniciar entrega o traslado desde stock existente y calcular cobertura por
  línea/origen.
- `doorandoor_historic_logistics/models/next_operation_wizard.py`:
  dejar de exigir una recepción inicial confirmada cuando el origen sea stock
  existente.
- Integración de Hanger y labels:
  reservar y contar labels existentes, conservar su ubicación y moverlos con
  los pickings reales.
- Vistas OCR/HDEL:
  mostrar tratamiento, disponibilidad, labels, faltantes y ruta antes de
  aprobar.

## 10. Tratamiento de operaciones históricas ya creadas

No deben revertirse en bloque. Primero se requiere un informe por HDEL que
compare:

- recepción desde Inventario virtual;
- labels nuevos generados;
- labels anteriores del mismo ITEM y almacén;
- entrega/traslado validado o pendiente;
- cantidad actual de Odoo;
- evidencia física disponible.

Cada caso deberá clasificarse como sin impacto, duplicidad pendiente, duplicidad
ya entregada o diferencia física. La corrección debe preservar documentos y
chatter, usando movimientos auditables; no se deben eliminar labels o pickings
validados para ocultar el origen del problema.

## 11. Pruebas mínimas antes de Pruebas y Gestión

1. Mismo almacén, stock y labels suficientes: crea solo entrega.
2. Almacenes distintos: crea traslado, recepción destino y entrega.
3. HDEL mixto con stock local y traslado desde otro almacén.
4. Stock suficiente pero labels incompletos: bloquea sin incrementar stock.
5. Label reservado por otra operación: lo excluye y explica la causa.
6. Stock insuficiente: muestra faltante, sin recepción ni label ficticio.
7. Conteo parcial Hanger: valida lo contado y crea backorder.
8. Factura excluida por Zoho: no crea operación logística.
9. Concurrencia: dos HDEL no pueden reservar el mismo label.
10. Verificación contable de inventario: el ciclo completo no aumenta cantidad;
    solamente mueve o entrega existencias existentes.

Todas las pruebas deben comenzar en transacción con rollback, continuar en
Local y después en Pruebas con casos controlados. Gestión requiere autorización
posterior, respaldo, ticket, ventana/coordinación operativa y validación de SRE.

## 12. Preguntas para la reunión de continuación

1. ¿La exclusión de Zoho debe conservar solamente referencia y hash, o no debe
   guardarse ningún registro?
2. ¿Quién confirma los labels propuestos: operador, supervisora o ambos?
3. ¿Qué criterio de selección usar: ubicación más cercana, FIFO, antigüedad del
   label o selección manual?
4. ¿Se permiten entregas parciales por defecto o solo con aprobación?
5. ¿Qué hacer cuando el producto existe en stock pero aún no tiene labels?
6. ¿Se mantiene la regularización histórica exclusivamente para excepciones?
7. ¿Qué fecha marca el corte desde el cual Zoho deja de controlar inventario y
   Odoo pasa a ser la fuente única?
8. ¿Cómo se identificarán las facturas de Zoho que ya consumieron inventario
   fuera de Odoo para impedir su importación duplicada?

## 13. Criterio de aceptación

Una venta histórica queda correctamente procesada cuando cada unidad entregada
puede rastrearse desde un label que ya existía en el inventario Odoo o desde una
regularización excepcional explícitamente aprobada; cada movimiento corresponde
a un traslado o entrega física real, y el proceso normal nunca incrementa la
existencia total.
