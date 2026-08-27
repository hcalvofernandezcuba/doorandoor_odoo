# Guía integral de pruebas de flujos DoorAndDoor

## 1. Objetivo y regla de ejecución

Esta guía define el flujo definitivo para validar productos, ventas, pagos,
fabricación, inventario, documentos y despacho. Debe ejecutarse primero en
local, después en pruebas y finalmente en producción.

Cada corrida debe usar documentos nuevos. No se modificará código mientras una
corrida esté incompleta: ante un fallo se registra hora, usuario, documento,
acción y captura, y se revisa el log del mismo momento.

## 2. Evidencias obligatorias

- Compañía, usuario, cliente, producto y almacén.
- Cotización, prefactura, factura y pago utilizados.
- Control de Cobro, residual y estado funcional.
- Variante, barcode, LDM, MO, picking o Pickup Order generados.
- Asiento contable cuando exista pago o crédito.
- Documento impreso y resultado: aprobado, rechazado o pendiente.
- Confirmación de que no existen documentos duplicados.

## 3. Tipos de producto

### 3.1 Producto normal

Producto reutilizable del catálogo. Puede tener variantes, controla stock por
variante y cada variante debe tener barcode único.

### 3.2 Producto Transformado

Parte de una variante terminada existente en stock. Se modifican uno o varios
atributos, se crea un producto independiente y su LDM consume el producto
terminado base. No se fabrica directamente desde materias primas.

### 3.3 Producto Especial

Producto completamente nuevo fabricado desde materias primas. Nace desde una
plantilla y una LDM maestra, conserva una configuración base, modifica solo los
atributos indicados y obtiene LDM, referencia y barcode propios.

### 3.4 Plantilla maestra

Estructura técnica no vendible que aporta familia, configuración de referencia,
componentes, operaciones y reglas para crear Especiales.

## 4. Política de atributos y variantes

La política vigente de DoorAndDoor es utilizar **Crear variantes: Al instante**
para Modelo, Color, Ancho, Alto, Cristal, Medidas y demás atributos comerciales.

No utilizar por ahora:

- De forma dinámica.
- Nunca.

Antes de agregar valores calcular:

`Total de variantes = valores atributo 1 × valores atributo 2 × ...`

Si el total es excesivo, dividir el catálogo en familias. No forzar miles de
combinaciones en una plantilla.

## 5. Preparación del entorno

1. SRE actualiza los módulos indicados y reinicia Odoo cuando exista código
   Python nuevo.
2. Recargar completamente el navegador y abrir una sesión nueva.
3. Confirmar versiones instaladas, compañía, moneda, país fiscal y almacén.
4. Confirmar permisos de Ventas, Contabilidad, Fabricación y Almacén.
5. Preparar clientes con y sin crédito.
6. Preparar producto normal, producto con variantes, producto fabricable y
   plantillas maestras WINDOWS o DOORS.
7. Confirmar diarios y cuentas contables de pago.

## 6. Configuración y prueba de producto normal

### 6.1 Preparación administrativa

1. Crear el producto base y marcarlo almacenable.
2. Activar Ventas y configurar precio, impuestos, unidad, rutas y almacén.
3. Agregar atributos y valores en modo **Al instante**.
4. Guardar y confirmar que Odoo creó todas las variantes previstas.
5. Generar barcode únicamente para variantes sin código.
6. Confirmar unicidad de los barcodes.
7. Abrir Labels y verificar que aparecen todas las variantes.

### 6.2 Prueba comercial

1. Crear una cotización nueva.
2. Seleccionar cliente, direcciones y almacén.
3. Elegir el producto base, no una lista interminable de combinaciones.
4. Confirmar que se abre el configurador guiado.
5. Elegir un valor por atributo y confirmar.
6. Verificar que se agrega una sola variante exacta.
7. Revisar precio, impuestos, cantidad y stock por almacén.

Resultado esperado:

- El configurador arma la variante correcta.
- El stock se calcula después de conformar el producto.
- Si falta existencia se muestra alerta informativa sin bloquear la venta.
- El label identifica la misma variante seleccionada.

## 7. Flujo del producto Transformado

1. Confirmar que el producto terminado base es almacenable.
2. Activar administrativamente **Permitir productos transformados**.
3. Seleccionar en Ventas la variante terminada exacta.
4. Activar **Declarar como producto transformado**.
5. Marcar únicamente los atributos que cambian.
6. Escribir sus nuevos valores.
7. Completar especificaciones e instrucciones de fabricación.
8. Confirmar la creación.

Resultado esperado:

- Se crea producto independiente con referencia ESP y barcode único.
- El nombre y la configuración incluyen atributos modificados y conservados.
- La LDM consume una unidad de la variante terminada base.
- La alerta de inventario revisa la variante base, no el Transformado vacío.
- El producto queda fuera de nuevas selecciones normales y puede archivarse
  después de 30 días sin movimientos.

No utilizar este flujo cuando el producto nace desde materias primas.

## 8. Configuración de plantilla maestra

La plantilla debe configurarse así:

- Puede venderse: desactivado.
- Puede comprarse: desactivado.
- Plantilla maestra de fabricación: activado.
- Familia: WINDOWS o DOORS.
- Nombre comercial resultante definido.
- Atributos y variante/configuración de referencia.
- LDM maestra con componentes básicos.
- Operaciones y centros de trabajo cuando correspondan.

Plantilla general definida para el proyecto:

```text
Plantilla Maestra DoorAndDoor Especiales
Código: DD-MASTER-ESPECIALES
Familia: DOORS
LDM: DD-MASTER-ESPECIALES-LDM
Componente inicial: bisagras × 3
```

La receta inicial es editable y Producción debe completarla con materiales y
operaciones reales.

## 9. Flujo del producto Especial

### 9.1 Creación

1. Abrir cotización, prefactura o factura en borrador.
2. Pulsar **Agregar producto especial**.
3. Seleccionar la plantilla maestra.
4. Seleccionar la **Configuración base** o variante de referencia.
5. Seleccionar la LDM maestra cuando corresponda.
6. Revisar todos los atributos y valores precargados.
7. Marcar **Modificar** solo en los atributos que cambian.
8. Escribir el nuevo valor únicamente en las filas marcadas.
9. Agregar atributos nuevos cuando sean necesarios.
10. En **Componentes de la receta**, conservar, excluir, agregar o ajustar
    cantidades.
11. En **Operaciones de fabricación**, conservar o excluir operaciones.
12. Completar cantidad y precio.
13. Completar obligatoriamente especificaciones e instrucciones.
14. Pulsar **Crear especial y agregar**.

Regla de los atributos:

- Sin marcar: conserva el valor base.
- Marcado: exige un nuevo valor.
- Atributo nuevo: exige nombre y valor.
- El nombre final usa la configuración completa.

### 9.2 Especificaciones e instrucciones

Ejemplo de especificaciones:

```text
Ventana especial de 32 × 84, color blanco, cristal Clear.
Tolerancia máxima de fabricación: 1/8".
```

Ejemplo de instrucciones:

```text
Cortar perfiles según las medidas finales.
Verificar escuadra, cristal y acabado antes de liberar.
```

### 9.3 Resultado esperado

- Producto almacenable independiente.
- Referencia ESP y barcode EAN-13 único.
- Configuración completa, no solo valores modificados.
- LDM independiente sin alterar la maestra.
- Con LDM maestra: copia solo componentes y operaciones seleccionados.
- Debe conservarse o agregarse al menos un componente.
- Sin LDM maestra: crea receta mínima con el componente automático.
- La línea comercial queda válida y trazable.

## 10. Cotización, prefactura y factura

1. Validar la cotización para crear la prefactura.
2. Confirmar enlaces, cantidades, precios, impuestos y reserva temporal.
3. Publicar la prefactura como factura.
4. Confirmar que no se duplican líneas, documentos ni reservas.

Los documentos impresos deben mostrar el nombre en la primera línea y cada
atributo debajo:

```text
Boston Stock
Modelo: FIX
Color: Bronce
Ancho: 30
Alto: 64
Cristal: Gray
```

```text
[ESP-2026-00049] California Transformado
Modelo: SH
Color: Blanco
Ancho: 20
Alto: 31
```

## 11. Pagos por memo

### 11.1 Reporte de Ventas frente a pago oficial

En un diario configurado con control, el vendedor puede informar que el cliente
realizó un pago, pero ese aviso no representa todavía dinero recibido.

1. Un usuario de Ventas con acceso a Facturación abre la factura.
2. Pulsa **Registrar pago**, selecciona el diario controlado e informa importe
   y referencia.
3. Confirmar que el sistema muestra **Pago reportado**.
4. Revisar que se creó un Control con origen **Reportado por ventas**.
5. Confirmar que no existe `account.payment`, asiento ni conciliación nueva.
6. Confirmar que el residual de la factura no cambió.
7. El responsable autorizado registra el pago oficial recibido por Zelle,
   banco o caja, usando la misma factura, diario e importe.
8. Confirmar que el pago oficial se enlaza al Control pendiente compatible.
9. Validar el Control y revisar factura, fabricación y despacho.

Resultado esperado:

- El reporte comercial nunca duplica dinero.
- Existe un solo pago oficial y un solo Control económico.
- El acumulado y el umbral utilizan pagos contables únicos, no importes
  reportados.
- Un Control reportado no puede validarse sin pago oficial enlazado.
- Solo usuarios del grupo **Registrar pagos oficiales** pueden crear o validar
  el pago real en el flujo controlado.

### 11.2 Pagador distinto

1. Publicar una factura nueva.
2. Crear pago Zelle a nombre de otra persona.
3. Escribir el número exacto de factura en el memo.
4. Publicar el pago.

Debe asociarse a una única factura, conservar el pagador informado y crear un
solo Control de Cobro.

### 11.3 Referencia inválida

Un pago sin referencia válida no debe conciliarse con una factura incorrecta;
queda para identificación manual de Contabilidad.

## 12. Umbral de fabricación

El porcentaje se calcula siempre sobre el total de la factura.

### Menos del 50 %

- Pago asociado y Control en revisión.
- Factura parcialmente pagada.
- No libera MO.
- Contabilidad conserva seguimiento manual.

### Acumulado igual o superior al 50 %

- Libera una sola vez la fabricación completa de líneas fabricables.
- No crea todavía despacho.
- No requiere validación manual adicional.

### Superior al 50 % pero menor al total

- La MO no se duplica ni aumenta incorrectamente.
- El despacho permanece pendiente.

## 13. Pago total y despacho

1. Completar el 100 %.
2. Confirmar residual cero y factura pagada.
3. Completar la MO cuando exista.
4. Revisar picking o Pickup Order.

La fabricación no debe duplicarse y el despacho se habilita únicamente según
las reglas de pago completo.

## 14. Excedente y crédito del cliente

1. Registrar pago mayor al residual con referencia válida.
2. Confirmar que la factura se liquida por su saldo exacto.
3. Confirmar que el excedente se acredita a la subcuenta del cliente bajo
   `120000 Pagos Anticipados`.
4. Revisar Control de Cobro y asiento.
5. Aplicar el crédito en una factura posterior.

Debe mostrarse importe recibido, aplicado y saldo restante; nunca utilizar la
cuenta de otro cliente.

## 15. Fabricación, inventario y labels

1. Abrir MO y verificar producto, cantidad, origen y LDM.
2. Para Transformado, confirmar consumo del terminado base.
3. Para Especial, confirmar materias primas de su LDM propia.
4. Completar fabricación y verificar que alimenta el despacho sin duplicados.
5. Abrir el producto y confirmar referencia y barcode.
6. Imprimir label de la variante y escanearlo.

## 16. Regresión obligatoria

Repetir después de cada entrega:

- Venta normal sin variantes.
- Venta normal con variantes.
- Transformado.
- Especial con LDM maestra.
- Especial sin LDM maestra.
- Pago manual sin memo.
- Pago parcial menor del 50 %.
- Acumulado del 50 %.
- Pago total y excedente.
- Fabricación estándar no Especial.
- Entrega de producto de stock.
- Impresión de cotización, prefactura, factura y labels.

## 17. Orden de corrida y criterio de cierre

1. Actualizar módulos.
2. Reiniciar Odoo mediante SRE.
3. Recargar navegador.
4. Confirmar versiones.
5. Revisar plantilla maestra.
6. Probar producto normal.
7. Probar Transformado.
8. Probar Especial.
9. Revisar LDM y documento impreso.
10. Probar pagos menor del 50 %, igual al 50 %, total y excedente.
11. Verificar MO, despacho y asientos.

El flujo se aprueba cuando todos los casos pasan, el log no presenta errores
nuevos, no existen duplicados y Contabilidad confirma pagos y anticipos.
