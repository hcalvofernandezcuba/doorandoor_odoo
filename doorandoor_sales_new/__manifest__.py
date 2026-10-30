# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Sales New",
    "version": "18.0.3.8.1",
    "category": "Sales",
    "summary": "18.0.3.8.1 - Configurador comercial sin ampliar acceso a ventas ajenas",
    "description": """
DoorAndDoor Sales New
=====================

Objetivo
--------

Este modulo centraliza el nuevo flujo comercial y operativo de DoorAndDoor con la factura como documento maestro.

La meta es soportar un proceso donde:
- la factura origina el pedido comercial interno
- el pago libera cantidades de productos
- la liberacion crea operaciones de inventario o fabricacion
- el usuario puede seguir todo el flujo desde la factura

Alcance funcional
-----------------

Version 18.0.3.8.1
------------------

Permite que un comercial limitado a sus propios documentos complete el
configurador de productos en facturas. El calculo agregado de disponibilidad
lee tecnicamente solo el almacen de pedidos ajenos, sin conceder acceso a esas
ventas ni ampliar los grupos del usuario.

Version 18.0.3.8.0
------------------

Agrega el botón Devolver a borrador, visible y ejecutable exclusivamente por
Administración/Ajustes. Bloquea la reapertura si existen facturas u operaciones
de inventario activas y cancela únicamente solicitudes logísticas todavía
pendientes. Conserva el número de venta y registra usuario, estado anterior y
solicitudes canceladas en el chatter.

Version 18.0.3.7.2
------------------

Permite a los usuarios comerciales imprimir o enviar una factura desde que
Control de Cobros haya validado cualquier importe mayor que cero. Mantiene
bloqueados los pagos solamente reportados, pendientes o sin dinero validado.

Version 18.0.3.7.1
------------------

Muestra en la lista de Variantes de producto la política Precio fijo / Sin
bonificación como una etiqueta roja, para identificar inmediatamente los ITEM
que bloquean cualquier descuento o bonificación.

Version 18.0.3.7.0
------------------

Agrega en Variantes de producto filtros y agrupación por política comercial:
Precio fijo / Sin bonificación, Bonificación propia del ITEM y Sin regla
especial. Muestra la política como columna administrativa y bloquea en servidor
la creación o modificación de bonificaciones de clientes para cualquier usuario
que no pertenezca a Administrador/Ajustes. Los cambios autorizados en la regla
del cliente quedan registrados en el chatter.

Version 18.0.3.6.1
------------------

Conserva el número fiscal original cuando una factura publicada vuelve a
borrador para corregirse y luego se reconfirma. Las facturas nuevas continúan
recibiendo su secuencia exclusivamente al publicarse.

Version 18.0.3.6.0
------------------

Agrega una política comercial por variante/ITEM administrada únicamente desde
Ajustes. Precio fijo bloquea absolutamente cualquier descuento. La bonificación
propia del ITEM prevalece sobre cliente, constructor y grupo sin acumularse, y
la fuente aplicada conserva trazabilidad hasta la factura.

Version 18.0.3.5.1
------------------

Permite imprimir o enviar una factura de pago parcial cuando Control de Cobros
ha validado al menos el 50% del subtotal más todos los impuestos. Para tarjeta
incluye además el cargo de procesamiento calculado sobre ese primer cobro.
Los pagos solo reportados o pendientes no liberan la impresión.

Version 18.0.3.5.0
------------------

Limita cada venta al almacén de su oficina. Cuando falta existencia crea una
solicitud para que Logística seleccione el almacén de origen y genere el
traslado interno hacia la sucursal, sin exponer otros almacenes al comercial.

Version 18.0.3.4.45
--------------------

Permite a Administración/Ajustes imprimir cotizaciones, prefacturas y facturas
en cualquier estado para análisis y resolución operativa. Conserva sin cambios
las restricciones de confirmación y pago aplicables a los demás usuarios.

Version 18.0.3.4.44
--------------------

Sincroniza una entrega de inventario completada con el estado Entregado de su
Pickup Order, registra usuario y fecha y completa sus cantidades entregadas.

Version 18.0.3.4.43
--------------------

Al reanudar el cumplimiento después de una recepción, conserva el importe ya
validado y auditado por Control de Cobros aunque la conciliación contable aún
no haya reducido el residual. Evita devolver productos liberados al estado de
pago pendiente y no modifica asientos ni conciliaciones.

Version 18.0.3.4.42
--------------------

Refresca el estado persistido del despacho y de su recepción antes de decidir
la liberación. Evita que una recepción recién validada con Hanger permanezca
interpretada como pendiente por una lectura anterior conservada en caché.

Version 18.0.3.4.41
--------------------

Al validar con Hanger la recepción de un traslado de abastecimiento, reanuda
de forma idempotente la factura pagada y crea su entrega final y Pickup Order
sin exigir una sincronización manual.

Version 18.0.3.4.40
--------------------

Las ventas pagadas abastecidas desde otro almacén esperan la recepción física
del traslado antes de crear la entrega final y su Pickup Order. La validación
de la recepción reanuda automáticamente el flujo comercial.

Version 18.0.3.4.39
--------------------

Unifica la prioridad de descuentos en cotizaciones: ajuste manual, cliente,
constructor, grupo comercial y precio base. Incorpora vigencia, autorizador,
referencia de la regla aplicada y conserva esa evidencia en la factura. Las
reglas de cliente y grupo quedan disponibles solo para Administración/Ajustes.

Version 18.0.3.4.38
--------------------

Permite imprimir cotizaciones y prefacturas en cualquier etapa, mantiene la
factura fiscal bloqueada hasta el pago total y muestra el teléfono del comercial
asignado en los apartados de los reportes comerciales. Cuando el comercial no
tiene teléfono propio utiliza el de su oficina comercial.

Version 18.0.3.4.37
--------------------

Extiende la protección de impresión al reporte estándar con pagos para que el
menú Imprimir no permita generar una factura pendiente. La factura confirmada
solo puede imprimirse cuando su estado de pago sea Pagado.

Version 18.0.3.4.36
--------------------

Alinea la regresión de liberación de productos fabricados con el flujo vigente
de Fábrica: el pago crea una necesidad auditable, el plan diario aprobado crea
la OF y la terminación habilita la salida y el Pickup Order. No recupera la
creación inmediata de OF que fue sustituida por el corte diario.

Version 18.0.3.4.34
--------------------

Crea o completa automáticamente los Pickup Orders después de liberar una
factura totalmente pagada y generar su entrega. También los sincroniza cuando
un producto fabricado pasa a la operación de salida. La operación es
idempotente: reutiliza el Pickup Order abierto del picking y no duplica líneas.

Version 18.0.3.4.33
--------------------

Aplica la protección visual de numeración fiscal al final de la composición de
la vista de factura, de modo que ninguna herencia posterior reactive el campo
editable en facturas o prefacturas en borrador.

Version 18.0.3.4.32
--------------------

Oculta en facturas y prefacturas el campo técnico de número mientras el
documento está en borrador. Tras la confirmación muestra el identificador
fiscal asignado por Odoo en modo de solo lectura. Las cotizaciones ya mantienen
su identificador Odoo en solo lectura.

Version 18.0.3.4.31
--------------------

Impide que un usuario asigne o altere el número de una factura de cliente.
Al crearla y al confirmarla se descarta cualquier texto introducido en el
campo técnico ``name`` y Odoo asigna obligatoriamente la siguiente secuencia
fiscal del diario. La regla es de una sola vía y se aplica también por API.

Version 18.0.3.4.30
--------------------

Impide enviar o generar el PDF oficial de facturas de cliente cuyo pago no
esté completado. Mantiene una Vista previa HTML disponible para facturas
confirmadas, sin habilitar su envío ni la emisión del documento oficial.

Version 18.0.3.4.29
--------------------

Impide imprimir o enviar facturas borrador y prefacturas, incluso mediante una
acción directa; solo documentos contables confirmados reciben salida impresa.

Version 18.0.3.4.28
--------------------

Evita que la bonificación comercial se ejecute sin un cliente seleccionado al
añadir una línea nueva a la cotización.

Version 18.0.3.4.27
--------------------

Conserva bloqueados los datos comerciales de una prefactura confirmada, pero
permite ajustar Pago con tarjeta mientras el documento contable siga en borrador.

Version 18.0.3.4.26
--------------------

Después de confirmar la prefactura, habilita Crear factura como siguiente paso
del flujo comercial y oculta Emitir/Imprimir PO y Entregas en ese documento.

Version 18.0.3.4.25
--------------------

Sustituye la denominación visible Pre Order por Prefactura en formularios,
botones, mensajes, secuencia y ayudas operativas, sin alterar identificadores
técnicos ni el flujo comercial.

Version 18.0.3.4.24
--------------------

Oculta el bloque estándar duplicado de Dirección de envío y alinea a la
izquierda el único bloque Cliente/Dirección de entrega de la factura.

Version 18.0.3.4.23
--------------------

Traslada Comercial, nombre y teléfono desde la izquierda al bloque derecho,
inmediatamente debajo de la dirección de oficina en facturas Bubble y Wave.

Version 18.0.3.4.22
--------------------

Replica en el diseño Wave la cabecera de factura ya validada con Bubble:
Factura a la izquierda y bloque de logo/oficina a la derecha.

Version 18.0.3.4.21
--------------------

Amplía el logo de la cabecera de factura a 106 px, sin modificar la
alineación derecha ni el resto del formato.

Version 18.0.3.4.20
--------------------

Amplía dos puntos el logo de la cabecera de factura sin alterar su posición,
el bloque de oficina ni ningún otro elemento del PDF.

Version 18.0.3.4.19
--------------------

Amplía dos puntos el logo y normaliza dirección/teléfono de oficina a la
misma escala visual que el bloque de dirección de entrega.

Version 18.0.3.4.18
--------------------

Mantiene el logo de referencia y los datos de oficina como un bloque único,
justificado completamente a la derecha de la cabecera.

Version 18.0.3.4.17
--------------------

Compone la cabecera derecha de factura como un único bloque centrado: logo
DoorAndDoor de tamaño ampliado y datos de la oficina inmediatamente debajo.

Version 18.0.3.4.16
--------------------

Amplía ligeramente el logo de oficina y reduce su margen inferior para
integrarlo con la dirección comercial sin modificar otros bloques.

Version 18.0.3.4.15
--------------------

Amplía cuatro puntos la altura máxima del logo de oficina, conservando su
centrado y el resto del formato de la factura.

Version 18.0.3.4.14
--------------------

Centra dentro de su bloque y eleva dos puntos el logo DoorAndDoor de la
oficina, sin alterar el resto de la distribución validada.

Version 18.0.3.4.13
--------------------

Mantiene en negro los bloques intercambiados Factura y Comercial, evitando que
hereden el color verde del título estándar de la plantilla Bubble.

Version 18.0.3.4.12
--------------------

Intercambia exclusivamente la posición de los bloques Factura y Comercial:
Factura/número/fecha se muestra arriba a la izquierda y Comercial/teléfono a
la derecha del bloque de cliente y entrega. No incluye vencimiento.

Version 18.0.3.4.11
--------------------

Modifica los bloques nativos del diseño Bubble para las facturas: comercial a
la izquierda, logo/dirección/teléfono de oficina a la derecha, cliente y
entrega en el área existente de dirección y número/fecha en el bloque nativo
del documento. No muestra vencimiento ni crea cuadros adicionales.

Version 18.0.3.4.10
--------------------

Retira la cabecera adicional que duplicaba datos corporativos, de cliente,
entrega y factura. Conserva un solo encabezado del formato establecido.

Version 18.0.3.4.9
-------------------

Inserta la cabecera comercial antes de las líneas de factura, usando la tabla
de productos como ancla estable ante extensiones de impuestos y reportes.
Oculta visualmente la banda estándar sin eliminar sus nodos técnicos.

Version 18.0.3.4.8
-------------------

Conserva oculto el nodo estándar de dirección de facturación para mantener la
compatibilidad con reportes heredados, mientras la cabecera DoorAndDoor
imprime exclusivamente el diseño comercial y de entrega.

Version 18.0.3.4.7
-------------------

Fija la cabecera de factura en dos columnas estables para PDF: comercial a la
izquierda; logo, datos y teléfono de oficina a la derecha; debajo, cliente y
entrega frente a número y fechas de la factura. Elimina el título estándar
duplicado del documento.

Version 18.0.3.4.6
-------------------

Reorganiza la cabecera impresa de las facturas: comercial responsable y
teléfono, cliente, dirección efectiva de entrega y datos del documento. Se
suprime la dirección de facturación y los campos internos de origen/código de
cliente de la banda principal.

Version 18.0.3.4.5
-------------------

Muestra de forma explícita en cada factura impresa el vendedor responsable y
la dirección de entrega asociada a la venta. Los datos permanecen visibles
aun cuando la dirección de facturación y entrega coincidan.

Version 18.0.3.4.0
-------------------

Cierra las rutas de creación de líneas con precio o descuento manual para
usuarios sin Ajustes y bloquea el cambio de lista cuando la venta ya contiene
productos. Los precios automáticos de listas, bonos y variantes se conservan.
Los traslados internos causados por un PO se crean con elevación técnica
limitada y trazabilidad del vendedor solicitante, sin otorgarle permisos
generales de Inventario.

Version 18.0.3.3.0
-------------------

Al liquidar completamente la entrega del nuevo flujo PO, genera una sola
factura fiscal desde la Orden de Venta, la contabiliza y enlaza prefactura,
PO y factura. Las entregas parciales mantienen el PO abierto y no facturan
hasta completar todas las cantidades.

Version 18.0.3.2.1
-------------------

Incrusta el código de barras y el QR directamente en los reportes, evitando
que el PO dependa de la URL HTTP local para imprimirlos. Mantiene el formato
Letter compacto y el enlace QR hacia el documento en Odoo.

Version 18.0.3.2.0
-------------------

Agrega una vista independiente de Órdenes de Venta emitidas como PO debajo de
Ventas y permite acceder al proceso de Entregas desde la prefactura confirmada,
respetando la autorización operativa definida por Cobros.

Version 18.0.3.1.0
-------------------

El PO utiliza una acción de reporte propia en tamaño Letter con márgenes y
encabezado compactos, conservando la identidad visual, datos comerciales,
impuestos, totales y firmas de los documentos DoorAndDoor.

Version 18.0.3.0.1
-------------------

Oculta las dos variantes estándar de `Crear factura` en las Órdenes de Venta
del flujo PO y bloquea también en servidor cualquier intento de facturación
prematura. Las órdenes históricas conservan la acción anterior.

Version 18.0.3.0.0
-------------------

Corrige la definición del nuevo PO: el registro técnico es la Orden de Venta
(`sale.order`) y su impreso para el cliente se titula `PO`. Las prefacturas del
flujo nuevo emiten ese documento y ya no crean directamente la factura; las
órdenes y Pickup Orders históricos conservan el comportamiento heredado.

Version 18.0.2.8.0
-------------------

Selecciona automáticamente el almacén proveedor con disponibilidad, conserva
el almacén comercial como destino y permite continuar cuando ningún almacén
cubre la venta, dejando el faltante documentado para Logística.

Version 18.0.2.7.1
-------------------

El indicador de existencias responde tanto al pasar el mouse como al hacer
clic. El clic muestra una notificación completa y evita que el detalle quede
recortado dentro de las tablas; también prepara su uso en pantallas táctiles.

Version 18.0.2.7.0
-------------------

Unifica en cotización, prefactura y factura un indicador de almacenes. Al pasar
el mouse consulta al servidor y muestra la existencia vigente del producto en
cada almacén, sin crear reservas, movimientos ni modificar el inventario.

Version 18.0.2.6.0
-------------------

Conserva el comercial que inició la cotización y lo transfiere a la prefactura
y factura. Los reportes reconstruyen desde el chatter la secuencia real de
responsables: muestran un solo nombre cuando no hubo cambios o el comercial
inicial y cada reasignación posterior cuando participaron varias personas.

Version 18.0.2.5.2
-------------------

Mantiene las líneas de factura en solo lectura después de confirmar, incluido
el pago parcial, en proceso de pago y pagado. Oculta las opciones para agregar
productos, secciones o notas y bloquea también en servidor la creación o
eliminación directa de líneas mientras el documento no vuelva a borrador.

Version 18.0.2.5.1
-------------------

Conserva explícitamente por línea el almacén proveedor desde la cotización
hasta la prefactura y factura. Un asistente permite reasignarlo antes de
contabilizar; sincroniza los tres documentos, vuelve a validar la prereserva
en el nuevo origen y conserva el futuro traslado condicionado al pago total.

Version 18.0.2.5.0
-------------------

Permite seleccionar el almacén proveedor por línea. Al confirmar la
prefactura valida y prereserva allí la disponibilidad de forma concurrente.
La factura conserva el compromiso y, al quedar totalmente pagada, lo convierte
una sola vez en traslado interno hacia el almacén comercial. El despacho al
cliente espera la recepción del traslado y permanece sujeto al pago total.

Version 18.0.2.4.4
-------------------

Sincroniza fulfillment al terminar realmente el picking, incluida la
confirmacion del asistente de entregas parciales. Usa la cantidad entregada
nativa, conserva el saldo pendiente y enlaza el backorder para continuar la
entrega sin considerar como entregada la cantidad solamente planificada.

Version 18.0.2.4.3
-------------------

El boton Confirmar de la factura fiscal solo se muestra mientras el documento
esta en borrador. Al registrarse desaparece del encabezado, incluida la factura
pagada, evitando una accion visualmente invalida y confusa para el usuario.

Version 18.0.2.4.2
-------------------

Antes de crear entregas o fabricacion por un pago, confirma tecnicamente la
venta interna vinculada, incluso cuando fue generada durante la publicacion de
la factura o pertenece a una factura historica. La confirmacion no ejecuta el
aprovisionamiento nativo ni altera las reglas de liberacion por pago.

Version 18.0.2.4.1
-------------------

Al publicar una factura fiscal vinculada, la cotización se confirma también en
el estado técnico nativo si había quedado en borrador. La confirmación mantiene
desactivado el aprovisionamiento: el picking continúa reservado exclusivamente
para el flujo de factura totalmente pagada.

Version 18.0.2.4.0
-------------------

Solo los administradores de Ajustes pueden modificar manualmente precios y
descuentos en cotizaciones, prefacturas y facturas. Los cálculos automáticos
de listas, variantes y bonos continúan habilitados para Ventas.

Version 18.0.2.3.0
-------------------

Las cotizaciones y prefacturas confirmadas se muestran completamente en solo
lectura. Tambien se bloquea en servidor la creacion, modificacion y eliminacion
de sus lineas; solo un administrador de Ajustes puede devolver el documento a
borrador antes de editarlo.

Version 18.0.2.2.2
-------------------

La comprobacion de reservas durante la seleccion de productos es de solo
lectura. Evita escrituras y conflictos concurrentes sobre facturas mientras
se calculan las existencias disponibles.

Version 18.0.2.2.1
-------------------

La confirmacion de cotizaciones ya no ejecuta el aprovisionamiento nativo de
sale_stock. Las entregas se originan desde la factura y la validacion de todo
picking de cliente exige que las facturas relacionadas esten publicadas y
totalmente pagadas. Las prefacturas nunca habilitan un despacho.

Version 18.0.2.2.0
-------------------

Cotizaciones, prefacturas y facturas emiten eventos relacionados al confirmar,
reabrir, crear la factura fiscal o publicarla, permitiendo actualizar las
vistas limpias abiertas en otras sesiones sin F5.

Version 18.0.1.0.84
-------------------

La guia incorpora la prueba operativa que separa el aviso de pago realizado
por Ventas del unico pago contable oficial recibido y validado por Cobros.

Version 18.0.1.0.83
-------------------

Se consolida la guia definitiva de corridas y regresion para productos
normales, Transformados, Especiales, variantes Al instante, LDM, pagos,
fabricacion, documentos, inventario, credito y despacho.

Version 18.0.1.0.82
-------------------

La guia establece la politica vigente de atributos Al instante para que todas
las combinaciones comerciales existan como variantes físicas imprimibles. Se
documenta la conversion segura de productos heredados como dinamicos.

Version 18.0.1.0.81
-------------------

Se documentan las diferencias entre atributos Al instante, Dinamicos y Nunca,
su efecto en el configurador comercial, el inventario y la impresion de labels,
incluyendo el procedimiento para materializar variantes dinamicas desde Ventas.

Version 18.0.1.0.80
-------------------

Las lineas de cotizacion, prefactura y factura muestran una alerta no
bloqueante cuando la cantidad solicitada supera la existencia disponible en el
almacen de la venta. Para productos transformados, la alerta controla la
variante terminada base consumida por su LDM sin impedir continuar el flujo.

Version 18.0.1.0.79
-------------------

Se agregan guias operativas integrales para ejecutar pruebas de regresion y
configurar productos normales, variantes, Transformados, Especiales Bayu de
Lola y plantillas maestras WINDOWS o DOORS. Estos documentos quedan preparados
para publicarse en el portal de documentacion del website.

1. Factura publicada
   - crear pedido de venta en borrador
   - vincular lineas de factura con lineas de venta
   - crear lineas internas de cumplimiento

2. Pago aplicado
   - calcular liberacion segun politica configurada
   - decidir ruta: stock o fabricacion
   - crear pickings o producciones por la parte cubierta

3. Logistica
   - seguimiento de entregas
   - trazabilidad por factura, pedido, picking y produccion
   - integracion gradual con impresion, firmas y documentos operativos

Relacion con otros modulos
--------------------------

Actualmente este modulo depende de doorandoor_delivery_status.

La intencion por ahora no es reemplazarlo de inmediato, sino reutilizar sus utilidades visuales para movimientos y operaciones de stock mientras doorandoor_sales_new asume la logica principal del nuevo flujo.

Estructura principal
--------------------

- models/account_move.py
  Extiende factura y concentra el flujo principal.

- models/account_move_line.py
  Agrega enlaces tecnicos hacia lineas de venta y cumplimiento.

- models/fulfillment_line.py
  Modelo central para rastrear cantidades facturadas, liberadas, enviadas y entregadas.

- models/mrp_production.py
  Sincroniza la produccion terminada con la generacion del despacho de salida.

- models/stock_picking.py
  Actualiza el estado de entrega al validar operaciones de salida.

- views/account_move_views.xml
  Agrega smart buttons, configuracion y pestaña de cumplimiento en factura.

Historial resumido
------------------

- 18.0.3.4.4
  El PO deja de usar la cabecera corporativa flotante que se superponía al
  contenido. Incorpora dentro de la página un encabezado estable con logo,
  empresa, dirección y Tax ID, conservando Letter, tabla, totales, QR y firmas.

- 18.0.3.4.3
  Amplía la reserva superior del PO a 70 mm después de validar el encabezado
  corporativo real de pruebas, evitando solapamientos con cliente, título,
  impuestos y tabla de productos.

- 18.0.3.4.2
  Reserva espacio superior e inferior adecuado en el formato Letter del PO para
  impedir que cliente, título, tabla y totales se superpongan con el encabezado
  y pie corporativos.

- 18.0.3.4.1
  Denominación histórica de la prefactura en formularios, estados, botones, mensajes,
  secuencia e impreso. Conserva la gestión validada: la prefactura reserva, el PO
  recibe pagos y autoriza entrega, y la factura fiscal nace automáticamente al
  cerrar la entrega.

- 18.0.2.1.1
  Activa por migracion el cron horario aun cuando una instalacion historica lo
  hubiera deshabilitado bajo noupdate.

- 18.0.2.1.0
  La prefactura en borrador no reserva inventario. La reserva de 24 horas
  comienza al confirmarla; al vencer se libera sin borrar el documento.
  El cron elimina despues de medianoche las prefacturas no confirmadas del
  dia anterior y restablece el enlace de su cotizacion.

- 18.0.2.0.1
  El numero PRE se guarda en un campo comercial independiente y no contamina
  la secuencia contable. La factura creada conserva el nombre vacio hasta que
  Odoo le asigna su numero fiscal INV al confirmarla.

- 18.0.2.0.0
  La prefactura dispone de estado propio, numero PRE y reserva de 24 horas.
  Al confirmarla queda cerrada; Crear factura genera un documento fiscal nuevo
  en borrador y sin numero, que inicia cobros solamente al contabilizarse.

- 18.0.1.1.0
  Cotizaciones confirmadas y facturas publicadas quedan cerradas para cambios
  comerciales. Solo Administracion/Ajustes puede devolverlas a borrador; el
  boton se oculta para el resto de usuarios y el servidor valida el permiso.

- 18.0.1.0.88
  La proteccion posterior a la confirmacion bloquea solamente cambios
  comerciales de producto, cantidad, precio, impuestos, cuenta y analitica.
  Permite escrituras tecnicas requeridas por conciliacion, campos calculados
  y enlaces internos de fulfillment.

- 18.0.1.0.85
  Se revierte al flujo nativo de Odoo con confirmación manual en cada etapa:
  - Las cotizaciones se crean con número inmediatamente
  - El botón "Confirmar" confirma la cotización sin crear prefactura automáticamente
  - El botón "Crear Prefactura" es manual desde cotizaciones confirmadas
  - Las prefacturas se confirman manualmente para convertirse en facturas
  - Se mantiene la trazabilidad y funcionalidad de reservas y cumplimiento

- 18.0.1.0.0 a 18.0.1.0.3
  Se crea la base del modulo, la generacion de sale order desde factura y la liberacion por pago con bitacora.

- 18.0.1.0.4 a 18.0.1.0.8
  Se corrigen vistas, sincronizacion historica, compatibilidad con lineas de producto y seguridad de logs, ademas de simplificar la vista de cumplimiento.

- 18.0.1.0.9 a 18.0.1.0.11
  Se incorpora la automatizacion de despachos por stock y el lanzamiento base de ordenes de fabricacion.

- 18.0.1.0.12 a 18.0.1.0.14
  Se agregan bloques de firma en reportes, referencia visible a ordenes de despacho en factura y el cierre del ciclo factura -> fabricacion -> entrega.

- 18.0.1.0.31
  Se evita la duplicacion de pickings y movimientos de stock cuando la factura intenta liberar una salida ya existente de la venta relacionada.

- 18.0.1.0.32
  Se agregan codigos de barra y QR en factura, picking y orden de recogida, y se eliminan importes del reporte operativo de entrega.

- 18.0.1.0.33
  Se agrega una reserva temporal de inventario por 24 horas para cotizaciones/prefacturas, con liberacion automatica al vencer o al convertirse en factura.

- 18.0.1.0.34
  La reserva temporal se traslada al documento de prefactura basado en `account.move` borrador, y el reporte impreso muestra el titulo `Prefactura`.

- 18.0.1.0.35
  El stock visible en facturacion y ventas descuenta como comprometidas las cantidades de facturas confirmadas, sin esperar al pago. La reserva temporal de prefactura por 24 horas se mantiene solo para documentos en borrador.

- 18.0.1.0.36
  La vista formulario de factura reemplaza el widget dinamico de impuestos por un resumen fijo con las etiquetas `Subtotal`, `Total Pimpuestos` y `Total`, eliminando el texto variable del porcentaje como `15%`.

- 18.0.1.0.37
  El documento comercial de cliente en `draft` se presenta funcionalmente como `Prefactura`, conservando la reserva temporal de stock por 24 horas. Al confirmar, el mismo documento pasa a verse como `Factura`.

- 18.0.1.0.38
  La `Prefactura` en `draft` agrega botones propios de `Imprimir` y `Enviar` en el encabezado, reutilizando las mismas acciones del documento final para permitir compartirla antes de confirmar.

- 18.0.1.0.39
  Se corrige el layout visual del bloque de totales en la vista de factura para evitar superposiciones entre etiquetas e importes en `Subtotal`, `Total Pimpuestos` y `Total`.

- 18.0.1.0.40
  Las cotizaciones creadas desde Ventas quedan sin numero y fuera de la lista estandar hasta pulsar `Validar cotizacion`. En ese momento se asigna la secuencia `sale.order` y la cotizacion pasa a registrarse en el listado.

- 18.0.1.0.41
  Se corrige la herencia XML de la vista de cotizaciones para evitar el error de actualizacion del modulo y permitir cargar el flujo de `Validar cotizacion`.

- 18.0.1.0.42
  Se elimina la personalizacion fragil del titulo en la vista de cotizaciones y se conserva el cambio funcional de `Validar cotizacion` con una herencia XML compatible con esta base.

- 18.0.1.0.43
  Se refuerza el ocultamiento de cotizaciones no validadas en la lista de `Cotizaciones` mediante contexto y filtro en modelo, evitando que registros con nombre `New` aparezcan antes de `Validar cotizacion`.

- 18.0.1.0.44
  Se corrige la compatibilidad del override `_search` en `sale.order` para evitar el error RPC al abrir las vistas de cotizaciones en esta base de Odoo 18.

- 18.0.1.0.45
  Se ajustan las acciones reales de menu de `Cotizaciones` para ocultar tambien las cotizaciones no validadas en la vista usada por onboarding y por equipos de ventas, evitando que aparezcan registros `New`.

- 18.0.1.0.46
  Se corrige el filtro de listas de `Cotizaciones` para no vaciar el menu: se ocultan solo las cotizaciones no validadas con nombre `New`, mientras se mantienen visibles las cotizaciones historicas numeradas y las ordenes ya creadas.

- 18.0.1.0.47
  El ocultamiento de cotizaciones `New` se mueve desde dominios de accion a un filtro de busqueda por campo auxiliar visible en lista, evitando errores de acceso durante la edicion del formulario y manteniendo ocultos solo los borradores no validados.

- 18.0.1.0.48
  Se reemplaza el filtro por busqueda de `Cotizaciones` por un dominio directo sobre el campo almacenado `ddsn_quote_list_visible`, asegurando que los registros `New` no aparezcan en la lista mientras los documentos numerados siguen visibles.

- 18.0.1.0.49
  Se implementa la base tecnica del flujo `Cotizacion -> Prefactura -> Factura`: validar cotizacion crea prefactura reservada por 24 horas, confirmar prefactura publica factura y confirma la venta, se agrega renovacion manual de reserva y se enlazan cotizacion, prefactura y factura final.

- 18.0.1.0.50
  Se corrige `action_post()` en prefacturas para esta base de Odoo 18, usando el recordset original en lugar del valor devuelto por `super()`, evitando el error `'bool' object has no attribute 'mapped'` al confirmar la prefactura.

- 18.0.1.0.51
  Se ajusta el control del boton de entregas desde ventas para que solo se habilite con pago total de la factura vinculada, manteniendolo visible pero inactivo mientras no se cumpla esa regla.

- 18.0.1.0.52
  Se unifica la etiqueta visual de impuestos en ventas y facturacion usando el texto fijo `Total de Impuestos`, eliminando tanto la leyenda variable por porcentaje en cotizaciones como el texto incorrecto `Total Pimpuestos` en la factura.

- 18.0.1.0.53
  Se actualiza la documentacion funcional y publicada en website para reflejar el flujo actual iniciado en `Ventas`, incluyendo `Cotizacion -> Prefactura -> Factura`, reglas de reserva de 24 horas y navegacion operativa desde ventas.

- 18.0.1.0.54
  Se corrige la generacion de barcode y QR en reportes PDF operativos usando URLs absolutas basadas en `web.base.url`, restaurando su visualizacion en `Orden de Recogida` y reportes de entrega.

- 18.0.1.0.55
  La direccion de entrega en `Ventas` se ajusta para Odoo CE 18 permitiendo seleccionar direcciones ya registradas del cliente o crear una nueva direccion tipo `delivery` desde la propia orden de venta.
  La nueva direccion queda asociada al cliente para reutilizarla en ventas futuras.

- 18.0.1.0.56
  El selector de direccion de entrega en `Ventas` se afina para trabajar como lista de direcciones tipo `delivery` del cliente, manteniendo como opcion la direccion principal del cliente.
  Al cambiar el cliente, la venta toma automaticamente la primera direccion de entrega registrada o la direccion principal si no existen direcciones adicionales.

- 18.0.1.0.57
  La orden de venta muestra debajo del selector un resumen visible de la direccion de entrega elegida.
  Esto permite validar de inmediato la direccion seleccionada sin necesidad de abrir la ficha completa del contacto.

- 18.0.1.0.58
  El mismo resumen visible de direccion de entrega se extiende a las vistas de `Prefactura` y `Factura`.
  Asi el usuario puede confirmar rapidamente la direccion seleccionada tambien en facturacion sin abrir el detalle del contacto.

- 18.0.1.0.59
  La factura impresa en Odoo CE 18 deja vacio el bloque estandar de `Payment Communication` y cuenta bancaria.
  En esta instancia esos datos dejan de mostrarse en el documento PDF de factura.

- 18.0.1.0.60
  El reporte impreso de factura se compacta reduciendo tamano general, espaciados, barcode, QR, firmas y bloque inferior.
  El objetivo es permitir que facturas con mas lineas de producto entren con mayor facilidad en una sola hoja dentro de Odoo CE 18.

- 18.0.1.0.61
  Se ajusta una variante visual de la factura reduciendo 2 puntos el bloque de direcciones del cliente y envio.
  Al mismo tiempo se devuelve presencia al cuadro de productos aumentando 2 puntos su tamano visual para evaluar mejor el equilibrio del diseno.

- 18.0.1.0.62
  Se empareja el tamano del bloque de datos del cliente con el de direccion de envio.
  Tambien se incrementa nuevamente el tamano visual de la tabla de productos para priorizar su lectura en la factura impresa.

- 18.0.1.0.63
  El boton estandar de publicacion en facturas de cliente en borrador se renombra visualmente a `Crear factura`.
  Esto alinea mejor la accion visible con el lenguaje operativo usado por el cliente dentro de Odoo CE 18.

- 18.0.1.0.64
  Amplia el renombrado visual de `action_post` a todas las variantes del boton presentes en la vista de factura.
  Esto evita que siga apareciendo el texto `Confirmar` cuando otra variante del mismo boton es la que queda visible en pantalla.

- 18.0.1.0.65
  Reemplaza visualmente el boton estandar `Confirmar` en facturas de cliente por un boton propio `Crear factura` que llama a la misma accion.
  Esto evita depender de variantes internas de la vista base de Odoo CE 18 que seguian mostrando `Confirmar` en borrador.

- 18.0.1.0.66
  Corrige la duplicidad de botones en prefacturas reemplazando el nodo del encabezado en lugar de sumar un boton adicional.
  En borrador de factura de cliente debe quedar visible solo `Crear factura`, evitando confusion operativa para el usuario.

- 18.0.1.0.67
  Simplifica el ajuste del encabezado de factura dejando solo el cambio de texto sobre `action_post`.
  Se elimina la estrategia de reemplazo visual para evitar duplicidades y se conserva unicamente el rename del boton a `Crear factura`.

- 18.0.1.0.68
  Ajusta el rename del boton de publicacion para apuntar especificamente al nodo `action_post` con texto base `Confirm` en la vista de factura.
  Esto responde a la estructura real de Odoo CE 18 donde el boton visible en prefacturas no era la variante `Post`, sino la variante `Confirm`.

- 18.0.1.0.69
  Reemplaza el `xpath` dependiente del texto `Confirm` por una referencia estructural al segundo boton `action_post` del encabezado.
  Esto evita errores de actualizacion por traduccion o diferencias de etiqueta y mantiene el rename visual a `Crear factura` en prefacturas.

- 18.0.1.0.70
  Ajusta nuevamente la herencia del encabezado usando `replace` sobre el segundo boton `action_post` del header.
  Esto evita la ruta de parseo que seguia fallando en la actualizacion y mantiene el texto visible `Crear factura` para prefacturas.

- 18.0.1.0.71
  Extiende el cron de prefacturas para que la reserva siga liberandose a las 24 horas y, ademas, elimine automaticamente prefacturas borrador obsoletas a las 48 horas.

- 18.0.1.0.72
  El reporte impreso de `Picking` agrega un encabezado visible con el titulo del documento y el numero de picking.
  Esto reduce confusion operativa al identificar rapidamente que el PDF corresponde a una salida o traslado de inventario.

- 18.0.1.0.73
  El boton principal de publicacion en factura vuelve a distinguirse por contexto de accion.
  `Prefacturas` muestra `Crear factura`, mientras que `Facturas` conserva `Confirmar` para no mezclar ambos flujos en la misma vista.

- 18.0.1.0.74
  Se corrige la accion de cotizaciones por equipo para no depender de `active_id` cuando el contexto no lo trae cargado.
  Esto evita el error `Name 'active_id' is not defined` al entrar con ciertos usuarios o desde vistas privadas.

- 18.0.1.0.75
  La cotizacion queda forzada al vendedor actual al crearla y tambien al validar `Validar cotizacion`.
  Esto evita bloqueos con usuarios `User: Own Documents Only` cuando el flujo de prefactura intenta trabajar una venta que Odoo no reconoce como propia.

- 18.0.1.0.76
  El vendedor actual se fuerza de manera estricta para usuarios `User: Own Documents Only`, incluso si el cliente trae otro comercial por defecto.
  Esto evita que el chatter muestre al creador correcto pero la propiedad real del documento quede en otro usuario y bloquee la validacion de cotizaciones.

- 18.0.1.0.77
  Se corrigen los calculos de reservas visibles en cotizaciones y prefacturas para vendedores con `User: Own Documents Only`.
  El computo ya no rompe al leer `sale.order` ajenas durante la evaluacion de stock reservado, manteniendo la restriccion documental pero permitiendo validar la propia cotizacion.

Autor
-----

Hanoi Calvo Fernández (doorandoor)
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": [
        "account",
        "sale_management",
        "stock",
        "mrp",
        "mail",
        "doorandoor_delivery_status",
    ],
    "data": [
        "data/preinvoice_sequence.xml",
        "data/pickup_order_sequence.xml",
        "data/quote_reservation_cron.xml",
        "security/ir.model.access.csv",
        "data/stock_transfer_request_sequence.xml",
        "views/supply_warehouse_change_wizard_views.xml",
        "views/stock_transfer_request_views.xml",
        "views/fulfillment_line_views.xml",
        "views/payment_release_log_views.xml",
        "views/pickup_order_views.xml",
        "views/account_move_views.xml",
        "views/product_product_views.xml",
        "views/invoice_number_guard_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_supply_views.xml",
        "views/res_partner_views.xml",
        "views/res_partner_category_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
        "views/report_signature_templates.xml",
        "views/po_report_action.xml",
        "views/pickup_order_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_sales_new/static/src/js/stock_tooltip_field.js",
            "doorandoor_sales_new/static/src/xml/stock_tooltip_field.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
