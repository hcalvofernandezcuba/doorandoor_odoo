# Guía de usuario: flujo de fabricación DoorAndDoor

Esta guía permite explicar y validar con los usuarios el flujo inicial de
fabricación antes de automatizar nuevos documentos.

## Planificación diaria disponible en 18.0.1.1.0

En **Fabricación → Reportes DoorAndDoor** están disponibles:

- **Necesidades por almacén:** registra producto, cantidad, fecha, prioridad y
  documento que origina cada petición.
- **Plan general diario:** carga y consolida las necesidades pendientes para
  que Producción decida las cantidades aprobadas.

El recorrido controlado es:

1. Registrar las necesidades de los almacenes.
2. Crear el plan del día e indicar Tampa y la ubicación de Preproducción.
3. Comprobar el plan creado por el corte automático posterior a medianoche. La
   acción manual de corte se reserva para recuperación si falla la tarea.
4. Revisar el desglose por almacén y modificar únicamente las cantidades que
   Producción decide fabricar.
5. Confirmar que el corte está cerrado y pulsar **Aprobar plan y crear OF**. Se generan las OF y se calculan las
   partes y piezas, incluyendo componentes de LdM anidadas.
6. Revisar disponibilidad y faltantes en **Partes y piezas**.
7. Imprimir el plan general y el requerimiento de materiales.
8. Pulsar **Solicitar salida de materiales** cuando Producción autorice la
   preparación. Esto crea un traslado interno sin validarlo ni descontar stock.
9. El almacenero revisa cantidades y valida la salida física cuando realmente
   entrega los materiales.
10. Usar **Imprimir vale de salida** para entregar a Fábrica un documento con
    origen, destino, solicitante, usuario que imprime, código de barras y firmas.

Repetir los botones no debe duplicar OF ni pedidos. Consultar o imprimir nunca
modifica las existencias.

## 1. Procesos que se validarán

1. **Fabricación por venta:** una puerta vinculada a la necesidad de un cliente,
   liberada cuando se cumpla la política de pago.
2. **Fabricación por reposición:** Tampa fabrica una puerta estándar para
   restituir en otro almacén una unidad entregada desde su stock.

Los productos demostrativos usan el prefijo `DDFC-` y están separados del
catálogo operativo.

## 2. Qué aporta actualmente Odoo

La orden de fabricación (OF) concentra:

- producto y cantidad que se fabricará;
- lista de materiales (LdM);
- componentes que deben consumirse;
- movimiento de entrada del producto terminado;
- responsable, fechas, origen y trazabilidad básica.

Confirmar una OF planifica sus movimientos, pero no descuenta materiales ni
incorpora el producto terminado al inventario. Eso ocurre al registrar los
consumos y finalizar la fabricación.

## 3. Recorrido de la demostración

1. Entrar en **Fabricación → Operaciones → Órdenes de fabricación**.
2. Buscar `DDFC-PRUEBA-VISUAL` en el campo Origen.
3. Abrir primero la OF por venta y revisar sus componentes.
4. Comparar cantidades con la LdM y con la entrega física del almacenero.
5. Revisar el movimiento del producto terminado y su ubicación de destino.
6. Abrir la OF de reposición y explicar la futura transferencia Tampa →
   almacén solicitante.

## 4. Flujo físico que debe confirmar el cliente

1. Venta y facturación.
2. Validación del medio de pago y porcentaje liberado.
3. Liberación de la necesidad de fabricación.
4. Solicitud y entrega de materiales desde el almacén de Tampa.
5. Entrega documentada a maquinado.
6. Entrega documentada de maquinado a ensamblaje.
7. Terminación y control de calidad.
8. Devolución documentada del producto terminado al almacén.
9. Entrega al cliente o transferencia al almacén de reposición.

## 5. Puntos todavía no automatizados

La versión inicial aún no crea documentos independientes para:

- solicitud y entrega de materiales a maquinado;
- entrega de piezas maquinadas a ensamblaje;
- recepción y aceptación del producto terminado;
- firma o impresión de cada cambio de custodia;
- reposición automática según la cantidad realmente entregada por almacén.

Tampoco modifica los lanzadores existentes de ventas, pagos o fabricación. Se
validará primero el proceso para evitar órdenes duplicadas o liberaciones en un
momento incorrecto.

## 6. Preguntas para los usuarios

- ¿Quién autoriza fabricar y con qué porcentaje de pago?
- ¿Quién entrega y recibe en cada cambio de área?
- ¿Los materiales se entregan para toda la OF o por unidades parciales?
- ¿Cómo se registran desperdicios, daños y sustituciones?
- ¿Quién valida calidad y puede rechazar el producto terminado?
- ¿La reposición es unidad por unidad o se agrupa por período y almacén?
- ¿Qué documentos requieren firma, código de barras e impresión?

## 7. Resultado esperado

La reunión debe definir qué pasos nativos se conservan, qué eventos liberan
cada producción, quiénes son responsables y qué documentos adicionales se
implementarán. No debe completarse una OF demostrativa hasta comprender los
movimientos de inventario que producirá.
