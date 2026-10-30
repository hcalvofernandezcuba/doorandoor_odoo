# Operaciones de almacén DoorAndDoor

## Objetivo

Centralizar la operación diaria sin duplicar movimientos de Inventario. Todas
las pantallas trabajan directamente con `stock.picking` y conservan la
trazabilidad nativa de Odoo.

## Configuración de operadores

1. Entrar en **Ajustes > Usuarios y compañías > Usuarios**.
2. Abrir el usuario almacenero.
3. En **Operaciones de almacén**, seleccionar sus almacenes operativos.
4. Definir, si corresponde, un almacén predeterminado.

Un operador con almacenes asignados solo puede consultar operaciones cuyo
origen o destino pertenezca a esa selección. Logística y Administrador/Ajustes
pueden consultar todos los almacenes. Mientras un usuario aún no tenga almacén
asignado se conserva el alcance de sus compañías para evitar bloquear la
puesta en marcha; la asignación debe completarse antes de operar.

## Menú operativo

```text
Operaciones
└── Almacén
    ├── Recepciones
    ├── Entregas
    ├── Entradas de fábrica
    └── Traslados
```

### Recepciones

Muestra recepciones nativas y traslados cuyo destino es el almacén del
operador. El documento se valida usando el formulario estándar de Inventario.

#### Flujo del caso: recepción de compras o entrada externa

1. Compras o Logística genera la recepción nativa indicando el almacén destino.
2. Odoo crea un `stock.picking` de tipo **Recepción**.
3. El operador del almacén destino entra en **Operaciones > Almacén >
   Recepciones**.
4. El operador abre el documento, compara producto, cantidad y procedencia con
   la mercancía física.
5. Si la cantidad recibida coincide, registra las cantidades realizadas y
   pulsa **Validar**.
6. Odoo mueve las existencias a la ubicación interna del almacén y deja el
   documento en **Hecho**.
7. La operación desaparece automáticamente de las recepciones pendientes.

Si hay una diferencia física, el operador no debe alterar el producto
solicitado: registra la cantidad realmente recibida y utiliza el tratamiento
nativo de entrega parcial o pendiente de Odoo.

### Entregas

Muestra exclusivamente cantidades pendientes de facturas publicadas y
totalmente pagadas. Operaciones no crea entregas comerciales manuales; la
orden de despacho nace del flujo de la factura pagada.

#### Herramienta principal del almacenero: Hanger

El operador trabaja normalmente desde **Operaciones > Almacén > Mis entregas**
en el Hanger. La cola presenta una sola tarjeta por operación y respeta
automáticamente los almacenes asignados al usuario.

La entrega puede localizarse por código o QR, Pickup Order, factura actual,
referencia del sistema anterior, cliente o producto. Al pulsar **Abrir y
contar**, el Hanger abre la operación móvil. El conteo prepara las cantidades
reales, pero no valida automáticamente la salida; el operador debe revisar y
confirmar la operación antes de entregar la mercancía al cliente.

#### Flujo del caso: entrega comercial al cliente

1. Ventas crea la cotización, prefactura y factura siguiendo el flujo
   comercial establecido.
2. Cobros y Pagos registra y valida el pago real.
3. La factura debe quedar publicada y **totalmente pagada**.
4. Solo entonces el proceso libera la orden de despacho asociada.
5. El operador del almacén origen la consulta en **Operaciones > Almacén >
   Entregas**.
6. Pulsa **Procesar entrega** para abrir la orden de despacho nativa ya
   liberada. Este botón no crea una entrega nueva.
7. El operador prepara exclusivamente los productos y cantidades indicados.
8. Verifica la dirección de entrega y valida el picking nativo cuando la
   mercancía realmente sale.
9. Odoo descuenta las existencias del almacén y actualiza automáticamente el
   estado de la entrega.

Si se valida la cantidad completa, la tarjeta pasa a **Entregado** y queda como
historial visible. Si la validación es parcial, Odoo crea su backorder nativo,
la tarjeta continúa en **Lista para entregar** y muestra solamente la cantidad
restante. **Procesar entrega** abre entonces ese backorder, no el documento ya
terminado.

Una factura borrador, sin pago, con pago en revisión o parcialmente pagada no
debe aparecer como entrega liberada. Tampoco se deben crear órdenes de
despacho manuales para evadir este control.

Si la línea aún no tiene una orden de despacho asociada, no muestra el botón
**Procesar entrega**. Esto indica que todavía espera preparación, producción o
la generación oficial del picking.

#### Ventas procedentes del sistema anterior

Gerencia o un responsable autorizado entra en **Operaciones > Almacén > Crear
entrega histórica**. Debe indicar factura anterior, fecha, cliente, **almacén
proveedor**, **almacén de entrega al cliente**, productos, cantidades,
referencia del pago y adjuntar el respaldo documental.

Si ambos almacenes coinciden, **Liberar al almacén** crea directamente la salida
al cliente y la coloca en **Mis entregas**. Si son distintos —por ejemplo,
proveedor Doral y entrega WPB— el mismo botón inicia una sola cadena controlada:

1. genera el despacho interno desde Doral hacia tránsito;
2. al validar ese despacho, genera automáticamente la recepción en WPB;
3. mantiene bloqueada la entrega al cliente mientras la recepción esté pendiente;
4. al recibir toda la cantidad en WPB, genera y libera la entrega final desde WPB;
5. al validar la entrega final, marca el control histórico como entregado.

El control histórico enlaza el despacho, la recepción y la entrega final, y
registra notas auditables en sus respectivos chatters. El operador puede abrir
cada documento desde el formulario y procesarlo con Hanger. Una recepción
parcial no libera prematuramente la salida al cliente.

La referencia histórica no puede repetirse dentro de la compañía. Este flujo
no crea una factura fiscal nueva en Odoo ni permite omitir el respaldo de la
venta anterior.

### Entradas de fábrica

Muestra movimientos desde una ubicación de Producción hacia un almacén. La
validación física permanece en el picking nativo.

#### Flujo del caso: producto terminado desde fabricación

1. Producción procesa la MO y consume los componentes de su LDM.
2. Al finalizar, Odoo genera o completa el movimiento del producto terminado
   desde **Producción** hacia el almacén definido en la orden.
3. El operador del almacén consulta **Operaciones > Almacén > Entradas de
   fábrica**.
4. Compara la orden, el producto terminado, sus variantes y la cantidad física.
5. Valida el movimiento nativo cuando recibe la mercancía terminada.
6. Odoo incorpora el producto al stock del almacén.
7. La entrada deja de aparecer automáticamente entre las pendientes.

La vista no crea ni modifica la MO o la LDM; únicamente presenta el movimiento
oficial generado por Fabricación.

### Traslados

Muestra movimientos internos entre dos almacenes diferentes, indicando
almacén de inicio y almacén de destino. DoorAndDoor separa el proceso físico en
un despacho hacia tránsito y una recepción enlazada en el almacén destino.

#### Flujo del caso: traslado entre almacenes

1. Gerencia de Logística crea un traslado nativo indicando almacén de origen,
   almacén de destino, productos y cantidades.
2. Odoo prepara un `stock.picking` interno para el despacho del origen.
3. El operador del origen lo ve en **Operaciones > Almacén > Traslados**.
4. El almacén de origen prepara y despacha la mercancía mediante el documento
   nativo.
5. Al validar la salida, la cantidad efectivamente despachada pasa a
   **DoorAndDoor - Mercancía en tránsito**. Todavía no incrementa el inventario
   disponible del destino.
6. El sistema crea automáticamente una recepción enlazada con esa cantidad y
   la muestra en **Operaciones > Almacén > Recepciones**.
7. Los operadores del destino reciben una actividad y recordatorios hasta que
   confirmen la llegada.
8. El destino comprueba físicamente productos, variantes y cantidades; puede
   utilizar el hanger o el flujo nativo de recepción.
9. Solo al validar la recepción las existencias pasan de tránsito al almacén
   destino y se cierran las alertas.

Si el origen despacha parcialmente, la recepción contiene solamente la
cantidad realmente salida. El backorder del despacho conserva el destino final
y generará otra recepción al completarse. Validar repetidamente el mismo
documento no duplica recepciones.

Si el traslado se cancela, el sistema también cierra los avisos. Si está
atrasado, continúa visible y las notificaciones cambian a nivel vencido hasta
su cierre.

## Casos de permisos y visibilidad

### Operador con un almacén asignado

- Solo consulta operaciones cuyo origen o destino sea su almacén.
- Puede abrir el movimiento nativo para ejecutar la operación autorizada.
- No obtiene visibilidad sobre operaciones ajenas.

### Operador con varios almacenes asignados

- Consulta las operaciones relacionadas con cualquiera de sus almacenes.
- Debe verificar el almacén indicado antes de procesar cada documento.

### Administrador/Ajustes y responsable de Logística

- Consulta todos los almacenes y todas las vistas operativas.
- Configura asignaciones de usuarios y tiempos de alerta.
- Logística es quien origina los traslados; la vista de Almacén es la cola de
  ejecución y seguimiento.

### Usuario todavía sin almacén asignado

Durante la puesta en marcha conserva temporalmente la visibilidad de sus
compañías para evitar un bloqueo accidental. Antes de comenzar la operación
real debe asignársele su almacén; desde ese momento el control queda limitado a
esa asignación.

## Estados y comportamiento automático

| Situación oficial | Resultado en Operaciones |
|---|---|
| Movimiento pendiente | Permanece visible en la cola correspondiente |
| Traslado pendiente | Visible para origen y destino, con alertas activas |
| Traslado vencido | Continúa pendiente y genera notificación escalada |
| Entrega total validada/Hecho | Pasa automáticamente a Entregado |
| Entrega parcial validada | Permanece Lista para entregar con el saldo |
| Otra recepción o traslado Hecho | Sale automáticamente de las colas pendientes |
| Movimiento cancelado | Sale de pendientes y cierra sus actividades |
| Factura sin pago completo | No libera ni muestra una entrega comercial |
| Factura totalmente pagada | Libera la entrega para el almacén origen |

Las vistas son informativas y se alimentan de los estados oficiales. No se
arrastran manualmente tarjetas Kanban ni se cambia un estado solo para alterar
su apariencia.

## Alertas de recepción

Al crear un traslado entre almacenes:

1. Se activa una alerta de recepción.
2. Odoo crea una actividad para los operadores del almacén destino.
3. Un cron ejecutado cada hora comprueba los avisos vencidos.
4. La notificación se repite según el intervalo configurado por compañía.
5. Al superar el tiempo de escalamiento se muestra como alerta vencida.
6. Al validar o cancelar el traslado, las actividades y recordatorios se
   cierran automáticamente.

Los parámetros se encuentran en **Ajustes > Process Control > Alertas de
traslados**.

## Prueba mínima

1. Asignar dos usuarios a almacenes diferentes.
2. Crear desde Logística un traslado nativo entre ambos almacenes.
3. Confirmar que el origen lo ve en **Traslados**.
4. Confirmar que el destino lo ve en **Recepciones** y recibe una actividad.
5. Validar la recepción en el formulario nativo.
6. Comprobar que desaparece de pendientes y cesan las alertas.
7. Confirmar que una factura parcial nunca aparece en **Entregas**.
8. Confirmar que una factura totalmente pagada sí aparece y abre su picking.
