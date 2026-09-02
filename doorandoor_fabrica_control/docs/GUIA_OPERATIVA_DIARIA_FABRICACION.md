# Guía operativa diaria de Fabricación DoorAndDoor

Esta guía organiza el trabajo desde la necesidad de fabricar hasta la entrega
del producto terminado al almacén. Cada responsable debe actuar sobre el mismo
hilo documental: necesidad, plan diario, orden de fabricación, salida de
materiales, vale entre áreas y entrada de fábrica.

## 1. Responsabilidades del flujo

- **Oficina o almacenes:** registran necesidades con producto, cantidad,
  almacén solicitante, prioridad y documento origen.
- **Planificación/Producción:** revisa el plan cerrado, decide cantidades,
  aprueba las OF y solicita materiales.
- **Almacén de Tampa:** prepara y valida la salida física de materiales.
- **Maquinado:** ejecuta su operación y confirma el vale de salida.
- **Ensamblaje:** acepta o rechaza lo entregado y ejecuta el ensamblaje.
- **Control de calidad/Producción:** registra consumos y finaliza la OF.
- **Almacén destino:** recibe el producto terminado y valida su entrada.

Consultar, imprimir o confirmar un vale de custodia no mueve existencias por sí
solo. Los movimientos se producen al validar transferencias y al finalizar la
fabricación según los documentos nativos de Odoo.

## 2. Revisar las necesidades pendientes

1. Abra **Fabricación → Reportes DoorAndDoor → Necesidades por almacén**.
2. Compruebe para cada necesidad el producto, cantidad, almacén, prioridad,
   fecha y documento origen.
3. Distinga el origen:
   - venta: debe conservar la factura que liberó la fabricación;
   - reposición: debe conservar la solicitud o transferencia que justifica
     reponer el stock de un almacén.
4. Corrija datos antes del corte. Después de incorporarse a un plan cerrado no
   deben alterarse los datos que sustentan la decisión diaria.

Las solicitudes posteriores a medianoche quedan para el plan siguiente. La
acción manual de corte se usa únicamente como recuperación si la tarea
automática no creó el plan.

## 3. Preparar y aprobar el plan diario

1. Abra **Fabricación → Reportes DoorAndDoor → Plan general diario**.
2. Seleccione el plan cerrado del día y confirme Tampa y Preproducción.
3. Revise el desglose por almacén.
4. Ajuste solamente la **cantidad aprobada** de cada línea.
5. Revise **Partes y piezas**, disponibilidad y faltantes. El cálculo incluye
   componentes de listas de materiales anidadas.
6. Imprima el plan general y el requerimiento de materiales si se utilizarán en
   la preparación física.
7. Pulse **Aprobar plan y crear OF** una vez tomada la decisión.

El botón es idempotente: no debe duplicar OF al repetirlo. Si falta una LdM o
hay un producto incorrecto, corrija la configuración antes de continuar.

## 4. Solicitar y entregar materiales

1. Desde el plan aprobado pulse **Solicitar salida de materiales**.
2. Revise el traslado interno creado; la solicitud no descuenta stock.
3. Prepare componentes separados por OF usando el desglose del plan.
4. Compare producto, variante y cantidad con el requerimiento.
5. Imprima el **Vale de salida** con origen, destino, solicitante, barcode y
   firmas.
6. El almacenero registra lo realmente entregado y valida la transferencia en
   el momento de la salida física.
7. Si falta material, no registre una entrega ficticia: deje pendiente el saldo
   y comunique el faltante a Producción.

## 5. Ejecutar la orden de fabricación

1. Abra la OF desde el plan o en **Fabricación → Operaciones → Órdenes de
   fabricación**.
2. Confirme producto, cantidad, LdM, almacén solicitante, factura o referencia
   de reposición y ubicación de destino.
3. Revise la disponibilidad de componentes antes de iniciar.
4. En Shop Floor ejecute las operaciones en este orden:
   - Maquinado;
   - Recepción desde Maquinado;
   - Ensamblaje.
5. Registre tiempos, cantidades y consumos reales. No complete una operación
   que todavía no ocurrió.

Recepción y Ensamblaje permanecen bloqueadas hasta completar la operación
anterior. No cambie manualmente la secuencia para saltar el control de custodia.

## 6. Entregar de Maquinado a Ensamblaje

Desde la OF pulse el botón inteligente **Maquinado → Ensamblaje**. Puede crear
varios vales cuando la entrega sea parcial.

### Salida de Maquinado

1. Cree un vale y seleccione las operaciones de Maquinado y Recepción.
2. Registre cada parte o producto y la cantidad entregada.
3. Anote los rechazos detectados antes de la salida y cualquier observación.
4. Confirme que aparece el documento origen correcto:
   - factura para fabricación por venta;
   - OF y referencia de solicitud/transferencia para reposición.
5. Pulse **Confirmar salida de Maquinado**. El sistema registra usuario, fecha y
   hora.
6. Entregue físicamente las piezas junto con el vale.

### Recepción en Ensamblaje

1. Cuente e inspeccione lo recibido contra el vale.
2. Registre por línea la cantidad aceptada y la rechazada.
3. La suma aceptada más rechazada debe coincidir exactamente con lo entregado.
4. Documente daños o diferencias en observaciones.
5. Pulse **Confirmar recepción en Ensamblaje** para registrar receptor, fecha y
   hora.
6. Imprima o archive el **Vale Maquinado a Ensamblaje** con las firmas
   requeridas.

El vale documenta el cambio de custodia y no crea ubicaciones ficticias ni
movimientos duplicados. Cada entrega parcial debe conservar su propio vale.

## 7. Ensamblar, controlar y finalizar

1. Inicie Ensamblaje solo después de aceptar la recepción desde Maquinado.
2. Registre consumo real, desperdicios o sustituciones según el procedimiento
   autorizado.
3. Registre la cantidad terminada y cualquier unidad rechazada.
4. Complete el control de calidad antes de finalizar.
5. Finalice la OF únicamente cuando el producto exista físicamente y los
   consumos estén revisados.
6. Imprima una etiqueta por cada unidad aprobada. Cada etiqueta identifica
   producto, OF, origen, destino, unidad, plan y barcode.

No reutilice una etiqueta para dos unidades ni entregue al almacén una unidad
rechazada como producto terminado.

## 8. Entregar el producto terminado al almacén

1. Prepare producto, etiquetas y documentos de la OF.
2. El almacenero abre **Operaciones → Almacén → Entradas de fábrica**.
3. Ambas partes comparan OF, variante, cantidad y destino.
4. El almacenero registra lo recibido y valida la entrada.
5. Si existe diferencia, se documenta y queda pendiente; no se completa una
   cantidad ficticia.

Para fabricación por venta, el producto queda disponible para continuar la
entrega al cliente. Para reposición, debe llegar al almacén que originó la
necesidad.

## 9. Cierre diario de Producción

1. Revise necesidades que quedaron fuera del corte y confirme que pasarán al
   próximo plan.
2. Compruebe que cada línea aprobada tenga una sola OF.
3. Identifique traslados de materiales pendientes o parciales.
4. Revise vales de Maquinado despachados aún no recibidos por Ensamblaje.
5. Revise OF iniciadas, bloqueadas o terminadas y documente su causa.
6. Confirme que las unidades terminadas tengan etiquetas y entrada de fábrica.
7. Entregue al siguiente turno una relación por número de plan, OF, traslado y
   vale; evite descripciones sin referencia documental.

## 10. Qué hacer ante una incidencia

- **No aparece una necesidad:** revise fecha de elegibilidad, pago/origen y el
  corte del plan; no cree una OF manual duplicada.
- **Falta LdM:** detenga la aprobación y solicite corregir el producto.
- **Faltan componentes:** comunique el faltante y entregue solo cantidades
  reales mediante el traslado.
- **El vale no permite confirmar:** verifique documento origen, operaciones y
  líneas con cantidades válidas.
- **Aceptado más rechazado no coincide:** vuelva a contar y corrija antes de
  confirmar recepción.
- **Operación bloqueada:** complete y cierre correctamente la operación previa.
- **Cantidad terminada diferente:** registre el resultado real, su causa y el
  tratamiento del saldo; no fuerce la OF para coincidir con el plan.
