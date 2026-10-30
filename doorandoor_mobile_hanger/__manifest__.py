# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Mobile Hanger",
    "version": "18.0.1.21.2",
    "category": "Inventory/Operations",
    "summary": "18.0.1.21.2 - Registra y muestra en vivo todos los disparos Hanger de sesiones IC",
    "description": """
DoorAndDoor Mobile Hanger
=========================

Version 18.0.1.21.2
--------------------

Registra en las sesiones IC cada disparo aceptado, rechazado, duplicado o sin
entrada, con operador, label, producto y causa legible. El monitor se actualiza
en vivo mediante el bus nativo de Odoo y conserva la evidencia para Soporte.

Version 18.0.1.21.1
--------------------

La pestaña Seriales leídos del Monitoreo Hanger para sesiones IC muestra el
código físico del label en lugar del nombre técnico del modelo y su ID. El
cambio es exclusivamente de presentación y no modifica conteos ni seriales.

Version 18.0.1.21.0
--------------------

Conserva evidencia positiva y negativa de los disparos Hanger tanto en
operaciones de almacén como en sesiones IC. Publica cada evento por el bus
nativo de Odoo, actualiza en caliente las vistas de monitoreo y permite que
usuarios seleccionados reciban una notificación personal desde cualquier
pantalla, sin convertir cada lectura en mensajes del chatter.

Version 18.0.1.20.30
---------------------

Los albaranes de traslado impresos anteriormente con el indicativo INT siguen
abriendo desde Hanger después de renombrar el documento operativo a TRS. El
alias solo resuelve la referencia; conserva los permisos reales por almacén.

Version 18.0.1.20.29
---------------------

La validación desde Hanger aplica únicamente las cantidades físicamente
contadas y crea automáticamente una recepción pendiente por el saldo no
recibido. Las reservas propuestas por Odoo nunca sustituyen el conteo físico.

Version 18.0.1.20.28
---------------------

Las recepciones validadas desde Hanger cargan los labels escaneados en el
inventario y actualizan su almacén y ubicación física de destino.

Version 18.0.1.20.27
---------------------

Los albaranes históricos pendientes abren el receptor móvil continuo de
Hanger, no el formulario administrativo del primer ITEM.

Version 18.0.1.20.26
---------------------

Los conteos históricos pendientes permanecen visibles como trabajo activo,
registran su progreso y usan una acción estable que no duplica la URL al
actualizar el monitor.

Version 18.0.1.20.25
---------------------

Una recepción histórica ya validada que necesita recuperar su evidencia
serializada abre desde el albarán el próximo control Hanger pendiente, sin
volver a ejecutar el movimiento de inventario.

Version 18.0.1.20.24
--------------------

Monitoreo Hanger muestra cada operación desde que el operador abre el conteo,
aunque todavía no haya leído ningún label. Presenta operador, última actividad,
estado esperando lectura o atención, progreso, lecturas positivas y negativas,
labels reservados y labels realmente leídos. Permite buscar por esos datos para
que Soporte diagnostique sin herramientas externas.

Version 18.0.1.20.23
--------------------

Al contar una entrega o traslado con reserva completa, Hanger acepta cualquier
label físico del mismo lote y del mismo ITEM exacto. Sustituye automáticamente
el label reservado, libera su reserva y documenta ambos códigos en el chatter.
Conserva el rechazo para otro ITEM, almacén, lote o reserva activa ajena.

Version 18.0.1.20.22
--------------------

Cuando una operacion cerrada conserva un backorder y Hanger demuestra un
conteo fisico parcial, el albaran imprime solamente los productos y labels
realmente escaneados. Conserva por separado la tabla nativa de cantidades
pendientes y evita presentar como entregadas unidades que nunca salieron.

Version 18.0.1.20.21
--------------------

El boton Actualizar monitoreo vuelve a abrir explicitamente el mismo formulario
administrativo del traslado o de la sesion IC. Evita que la recarga desde la
lista unificada derive al formulario operativo del documento.

Version 18.0.1.20.20
--------------------

El boton Abrir monitoreo de una sesion IC abre ahora un formulario
administrativo de solo lectura con progreso, ultima lectura, seriales, items y
variantes contadas. Evita entrar por error al formulario operativo de conteo.

Version 18.0.1.20.19
--------------------

Integra el monitor unificado en la accion operativa historica de Monitoreo
Hanger, conservando su identificador y enlaces existentes. Asi las operaciones
de almacen y las sesiones IC activas o validadas aparecen en la misma pantalla
que ya utiliza Soporte, sin depender de un menu administrativo nuevo.

Version 18.0.1.20.18
---------------------

Unifica en Monitoreo Hanger las operaciones de almacén y todas las sesiones
IC no anuladas. Permite filtrar por tipo, estado, almacén y operador, conserva
los procesos validados para soporte y abre cada documento en su vista de
monitoreo o conteo sin ampliar el acceso operativo de los usuarios limitados.

Version 18.0.1.20.17
---------------------

Permite validar y cerrar directamente desde el Hanger a Administrador/Ajustes,
Inventario/Administrador y Supervisor Hanger aunque no tengan un perfil
operativo ni almacenes asignados. Conserva la validación por almacén para los
operadores limitados y registra siempre al usuario real en la auditoría.

Version 18.0.1.20.16
---------------------

Resuelve primero las referencias exactas de operaciones de almacén antes de
consultar Pickup Orders. Los operadores de Hanger pueden escanear traslados de
sus almacenes sin necesitar acceso a facturas o asientos contables; la consulta
técnica de Pickup Orders sigue limitada a identificar la operación y la
validación final conserva las reglas reales del usuario y sus almacenes.

Version 18.0.1.20.15
---------------------

Agrega el botón Imprimir albarán tanto a la operación completa como a la
vista móvil del Hanger. El botón genera directamente el PDF nativo Delivery
Slip para recepciones, traslados y entregas no canceladas, sin depender del
menú técnico de impresión.

Version 18.0.1.20.14
---------------------

Permite usar en entregas y traslados cualquier label disponible del mismo ITEM
y almacén aunque pertenezca a otro lote físico. Cuando la cantidad ya está
completamente reservada, Monitoreo Hanger muestra el label realmente contado y
el esperado que será liberado; la aceptación sustituye uno por uno, conserva
ambos lotes, responsable, fecha y operación en la auditoría, y mantiene los
bloqueos para productos diferentes, otros almacenes, duplicados o reservas de
otra operación.

Version 18.0.1.20.13
---------------------

Después de validar realmente una operación desde el Hanger, elimina el
asistente transitorio ya terminado, limpia la navegación móvil y abre un
lanzador nuevo para escanear el siguiente documento. Conserva cualquier
asistente nativo legítimo cuando Odoo todavía no ha cerrado la operación,
evitando terminar prematuramente backorders o transferencias inmediatas.

Durante cualquier conteo clasifica cada disparo antes de procesarlo: las
referencias de órdenes, Pickup Orders y URL/QR de Odoo cambian a la operación
leída, mientras los labels físicos permanecen en el conteo actual. La cámara
ejecuta la navegación aun en modo continuo y los errores de acceso a documentos
ya no se registran falsamente como productos rechazados.

Version 18.0.1.20.12
---------------------

Cuando una línea requiere varias unidades y solo parte de sus labels están
reservados, permite que el Hanger acepte y reserve labels adicionales del mismo
ITEM y lote hasta completar la cantidad del documento. Conserva la lista
cerrada cuando ya están reservadas todas las unidades y mantiene el rechazo
para otro lote, evitando sustituciones silenciosas o cantidades duplicadas.

Version 18.0.1.20.11
---------------------

Mantiene visibles el producto y lote esperados por la operación aunque no
exista un label pendiente elegible para liberar. En ese caso la columna Label
esperado a liberar queda vacía, se oculta Aceptar label y solo se permite anular
el evento fallido; ningún label aceptado se propone como sustituto.

Version 18.0.1.20.10
---------------------

Excluye de cualquier sustitución los labels ya aceptados. Aceptar label solo
se ofrece cuando existe otro label esperado aún no contado, del mismo producto
y lote; la fila muestra ese pendiente exacto. Si no existe, solo puede anularse
el evento fallido y el conteo correcto permanece intacto.

Version 18.0.1.20.9
--------------------

Muestra en cada evento fallido el label, producto y lote realmente contados
junto al label, producto y lote esperados que serían liberados. El botón Aceptar
label utiliza exactamente la sustitución mostrada, permitiendo revisar la
decisión antes de modificar reservas sin alterar un conteo ya realizado.

Version 18.0.1.20.8
--------------------

Acepta el label realmente entregado como sustitución uno por uno del label
esperado del mismo producto y lote. Si el esperado ya estaba contado, conserva
la cantidad, libera su reserva y marca su lectura como sustituida; si aún no se
había contado, suma solo la nueva unidad. Mantiene la opción independiente de
anular el evento fallido sin tocar el conteo.

Version 18.0.1.20.7
--------------------

Restringe Aceptar label a entregas y traslados donde exista una unidad esperada
pendiente del mismo producto y del mismo lote. Libera exactamente ese serial
esperado, reserva el label realmente entregado y lo suma al conteo. Si no existe
una sustitución exacta o el serial ya fue contado, bloquea la acción.

Version 18.0.1.20.6
--------------------

Ofrece dos decisiones administrativas sobre intentos fallidos: Aceptar label,
que revalida producto, almacén, reserva, duplicidad y límite del documento antes
de sumar una unidad; y Anular evento, que descarta el fallo sin alterar el
conteo. Las lecturas aceptadas permanecen protegidas. Los seriales únicos ya
contados nunca pueden aceptarse una segunda vez.

Version 18.0.1.20.5
--------------------

Permite a responsables de Inventario anular desde Monitoreo Hanger una lectura
aceptada incorrecta o doble mientras la operación continúa En conteo. Revierte
una unidad, sincroniza las pantallas de conteo abiertas, habilita nuevamente el
label cuando corresponde y conserva evento, responsable, fecha y chatter como
trazabilidad; nunca altera operaciones terminadas o canceladas.

Version 18.0.1.20.4
--------------------

Permite que el operador cierre desde el flujo controlado Hanger sin recibir
acceso al costo de los productos: las verificaciones se realizan con el usuario
real y solo la valoración interna de stock se ejecuta de forma técnica,
conservando operador, fecha y chatter auditables. Además compara el serial con
los labels ya reservados antes de intentar reservarlo, evitando sustituciones
silenciosas de unidades físicas del mismo ITEM.

Version 18.0.1.20.3
--------------------

Permite que los vendedores autorizados preparen e impriman los labels grandes
de sus entregas mediante una lectura tecnica limitada de los seriales ya
reservados. No concede acceso directo a conteos ni a la administracion de
inventario.

Version 18.0.1.20.2
--------------------

Identifica internamente el cierre directo originado en el Hanger para que las
recepciones sin seriales unitarios también queden en estado Validada y cerrada,
con usuario y fecha auditables, además del estado Hecho de inventario.

Version 18.0.1.20.1
--------------------

Extiende la validación directa controlada a todos los procesos contados con
Hanger: entregas, recepciones y traslados. El operador responsable valida la
operación desde el botón Validar operación cuando el conteo está completo y sin
diferencias. Dirección de Logística conserva el monitoreo y la trazabilidad del
usuario, fecha, cantidades y documento, sin constituir un paso obligatorio de
cierre.

Version 18.0.1.20.0
--------------------

Permite que el operador cierre directamente una entrega mediante el botón
Validar entrega del Hanger, únicamente después de aplicar un conteo completo y
sin diferencias. El servidor restringe esta excepción a entregas de clientes,
al almacén asignado y a perfiles operativos Hanger; la validación general desde
las vistas estándar continúa bloqueada. Recepciones y traslados mantienen el
flujo Aplicar y enviar a validar.

Version 18.0.1.19.10
---------------------

Añade una confirmación háptica perceptible de 180 ms exclusivamente después de
que el servidor acepta y guarda un label. Las lecturas rechazadas o duplicadas
no vibran. Conserva el bloqueo que obliga a los operadores Hanger a enviar la
operación a validación sin poder cerrarla directamente.

Version 18.0.1.19.9
--------------------

Impide en servidor que los perfiles Hanger de conteo, entrega y almacén validen
o cierren directamente una operación, incluso desde la vista completa estándar
de Odoo. Estos operadores deben usar Enviar a validar; el cierre queda reservado
a supervisores, Administradores de Inventario y Administrador/Ajustes.

Version 18.0.1.19.8
--------------------

Completa la sincronización del cierre Hanger liberando siempre la operación,
factura, usuario y fecha de reserva de los labels unitarios cuando una salida o
traslado termina. Conserva la actualización de estado y mapa aun cuando un
administrador valida desde la acción estándar de Odoo.

Version 18.0.1.19.7
--------------------

Sincroniza el estado Hanger, los seriales físicos y el mapa del almacén cuando
un administrador valida desde la acción estándar de Odoo una operación que ya
tiene el conteo Hanger completo. Evita operaciones en estado Hecho que continúen
figurando En conteo y con sus ítems todavía reservados en el almacén de origen.

Version 18.0.1.19.6
--------------------

Muestra Aplicar y enviar a validar dentro del cuerpo del formulario para vistas
móviles de pantalla completa, donde Odoo oculta el footer. Detiene la cámara al
alcanzar la cantidad esperada para evitar relecturas del último label.

Version 18.0.1.19.5
--------------------

Restaura el flujo JavaScript probado en 18.0.1.18.0 y elimina por completo la
cantidad manual agregada en 18.0.1.19.0. Los productos con label compartido
continúan aceptando disparos repetidos, siempre una unidad por lectura.

Version 18.0.1.19.4
--------------------

Captura a nivel de ventana los disparos de DataWedge que Android entrega fuera
del campo barcode. Conserva la captura normal del campo y evita duplicarla
cuando este mantiene el foco.

Version 18.0.1.19.3
--------------------

Retira Cantidad por lectura de la pantalla operativa y de la llamada JavaScript
para que el barcode sea el único campo receptor del teclado físico Zebra. Los
productos con label compartido conservan el conteo por disparos repetidos y los
seriales únicos mantienen el rechazo de duplicados.

Version 18.0.1.19.2
--------------------

Abre el asistente de conteo como navegación completa en Zebra/Android. Evita
que la ventana modal se cierre al terminar el disparo documental y devuelva al
operador al lanzador antes de poder leer el label del producto.

Version 18.0.1.19.1
--------------------

Completa con la lista explícita de vistas la acción que abre el conteo desde
el disparo documental. Evita el error JavaScript ``reading map`` de
``preprocessAction`` cuando el widget móvil recibe directamente la acción por
RPC, sin pasar por el normalizador de botones del cliente web.

Version 18.0.1.19.0
--------------------

Determina desde la configuración del producto si el label es único o
compartido. Los labels compartidos de piezas pequeñas pueden contarse repitiendo
el disparo o indicando una cantidad por lectura; los seriales únicos conservan
el bloqueo de duplicados. Impide cantidades menores que uno o superiores a la
demanda del documento y registra en Monitoreo Hanger el incremento y acumulado.

Version 18.0.1.18.2
--------------------

Permite repetir un label compartido para sumar cada pieza de productos masivos
en entregas y limpia siempre el campo después de un rechazo, evitando códigos
concatenados. Al cerrar una salida parcial conserva activo el label maestro y
su ubicación de lote, mientras libera la reserva del documento completado.

Version 18.0.1.18.1
--------------------

El acceso operativo desde documentos escaneados y Trabajo diario abre
directamente el asistente que recibe labels. Elimina la ficha intermedia sin
campo de lectura, evitando interpretar el pitido físico como conteo aceptado o
confundir el estado nativo En espera con Pendiente de validación Hanger.

Version 18.0.1.18.0
--------------------

Agrega un menú administrativo independiente Monitoreo Hanger, invisible para
los operadores, con progreso, operador, última actividad y detalle de aperturas,
lecturas aceptadas y rechazos. Los intentos fallidos enviados por el navegador
se conservan en un registro persistente independiente de los logs técnicos y
pueden consultarse mediante Actualizar monitoreo mientras el operador trabaja.

Version 18.0.1.17.1
--------------------

Corrige una regresión de la interfaz móvil: mientras el conteo está incompleto,
el botón grande de envío a validación ya no permanece accionable ni puede
recibir accidentalmente el Enter emitido por el Hanger. En su lugar se muestra
la orientación para entrar al conteo; la acción de envío aparece únicamente
después de aplicar todas las lecturas requeridas.

Version 18.0.1.17.0
--------------------

Incorpora el modo transitorio de reserva al escanear para documentos que aún
no incluyen ítems preasignados. En salidas y traslados el Hanger acepta solo
labels unitarios existentes, aplicados al inventario, disponibles en el almacén
de origen y pertenecientes a un producto esperado; bloquea códigos genéricos,
ítems de otros almacenes u operaciones y registra la reserva con usuario, hora,
factura y chatter. Las lecturas continuas ya no se descartan cuando el teclado
del Hanger demora más de 1.2 segundos en inyectar el código completo. Al validar
la operación actualiza también la ubicación operativa del serial: las entregas
lo retiran del lote y del mapa del almacén hacia Clientes, mientras los traslados
lo sitúan en el destino y liberan su reserva para operaciones posteriores.

Version 18.0.1.16.0
--------------------

Completa desde el Hanger el cierre operativo de conteos, entregas, recepciones
y traslados. Agrega acciones grandes y visibles dentro de las pantallas móviles
y permite aplicar las lecturas y enviar la operación a validación en un solo
paso, sin depender de botones ocultos en el encabezado ni de abrir la vista
administrativa. Si el conteo está incompleto conserva las validaciones y muestra
la causa al operador. Incorpora además un botón Actualizar en las pantallas
principales del Hanger para refrescar estados y cantidades sin salir y entrar.

Version 18.0.1.15.0
--------------------

Integra Labels de factura con el flujo existente de pago y fulfillment. Al
imprimir, prepara o localiza el despacho liberado, reserva labels unitarios ya
existentes en el almacén y registra factura, operación, usuario y fecha. Las
reimpresiones conservan los mismos códigos y quedan auditadas. El Hanger impide
contar seriales reservados para otra operación o sustituir los asignados al
despacho, evitando duplicidades entre venta, preparación y entrega.

Version 18.0.1.12.3
--------------------

El escáner de documentos reconoce también las URLs limpias de Odoo 18 con
formato ``/odoo/action-<acción>/<registro>``. La acción se valida antes de
abrir el registro para evitar confundir facturas u otros documentos con una
operación de almacén, conservando los permisos Hanger por almacén.
El disparo físico del Hanger crea el asistente transitorio y ejecuta de forma
automática la apertura de la operación; ya no se limita a llenar el campo ni
requiere pulsar manualmente el botón ``Abrir operación``.

Version 18.0.1.12.4
--------------------

El formulario de apertura documental detecta el final del disparo por una
pausa corta y no descarta referencias que el teclado del Hanger inyecta en más
de 1.2 segundos. Los conteos continuos conservan su filtro rápido original.

Version 18.0.1.12.5
--------------------

El barcode documental se envía directamente al servidor mediante un método
sin registro, evitando que OWL rechace el asistente nuevo por campos todavía
no guardados. La llamada y la apertura quedan trazables en el log HTTP.

Version 18.0.1.12.6
--------------------

El campo documental toma y recupera automáticamente el foco al abrirse la
pantalla, permitiendo que el Hanger físico en modo teclado entregue el Code128
al componente sin exigir un toque previo sobre el formulario.

Version 18.0.1.13.0
-------------------

Reconoce labels unitarios ``inventory.unit.serial`` durante entregas,
traslados y recepciones, registra cada lectura contra la operación concreta y
evita duplicar un serial dentro del mismo documento. Limpia explícitamente el
campo después de cada disparo para conservar el conteo continuo del Hanger.

Version 18.0.1.14.0
-------------------

Incorpora el cierre controlado del conteo de entregas, traslados y recepciones.
El operador Hanger envía una operación completa a revisión sin mover inventario;
supervisores, Inventario Administrador y Administrador/Ajustes reciben el aviso
y pueden validar y cerrar la operación. Registra usuarios y fechas en el chatter.

Version 18.0.1.14.1
-------------------

Restringe los avisos de operaciones Hanger enviadas a validación a usuarios
activos de Inventario/Administrador y Administrador/Ajustes. Los operadores que
realizan el conteo no reciben el aviso gerencial por pertenecer a otros grupos.

Version 18.0.1.14.2
-------------------

Mueve las entregas, recepciones y traslados cerrados mediante Hanger a una
columna final de Procesos validados, visible solamente para Inventario/
Administrador y Administrador/Ajustes, sin acciones operativas. Para los
operadores, la tarea desaparece en cuanto queda validada.
Incluye acceso de solo lectura al tablero para Administrador de Inventario,
sin concederle creación, edición ni eliminación sobre la vista técnica.

Version 18.0.1.14.3
-------------------

Clasifica en Procesos validados todas las operaciones de almacén realmente
cerradas en Odoo, incluso los documentos históricos creados antes de existir
el estado de validación Hanger. La columna continúa oculta para operadores y
visible únicamente para los perfiles administrativos autorizados.
Cuando la validación termina directamente, regresa a una bandeja nueva para
evitar tarjetas obsoletas; conserva los asistentes nativos de Odoo cuando existe
una diferencia o un backorder que requiere decisión del responsable.

Primera fase de la interfaz móvil para operadores de almacén. Incorpora un
acceso independiente para escanear el código de una entrega, recepción,
traslado o entrada de fábrica, comprueba los almacenes autorizados del usuario
y abre una vista simplificada del movimiento nativo. Los QR de las entregas
apuntan a esta vista móvil sin alterar la lógica de inventario, pago o entrega.

Version 18.0.1.9.1
------------------

Reconoce enlaces QR de Pickup Orders además de enlaces directos a operaciones
de inventario. Resuelve la entrega asociada y conserva los controles de acceso
por almacén antes de abrirla en la vista móvil.

Version 18.0.1.9.2
------------------

Permite a los operadores Hanger abrir la vista móvil después de validar sus
permisos reales sobre la operación y el almacén. Eleva únicamente la lectura
de la definición técnica de la ventana, sin ampliar acceso a inventarios.

Version 18.0.1.10.0
-------------------

Agrega la cola móvil Mis entregas, con una tarjeta por operación, búsqueda por
entrega, factura, cliente, producto y Pickup Order. Respeta los almacenes
asignados y abre directamente el conteo operativo con Hanger.

Version 18.0.1.11.0
-------------------

Agrega `Operaciones > Almacén > Trabajo diario`, un tablero único que agrupa
las operaciones activas en Por despachar, Por recibir y Listo para entregar.
Cada tarjeta conserva el movimiento nativo y abre el paso correspondiente en
la interfaz Hanger, sin modificar los menús ni tableros nativos de Inventario.

Version 18.0.1.12.0
-------------------

Convierte Trabajo diario en una bandeja unificada de despachos, recepciones,
entregas y sesiones de conteo. Los operadores ven únicamente operaciones de
sus almacenes y conteos asignados a su usuario; supervisores y administradores
conservan la vista global. Cada tarjeta abre el documento Hanger original.

Version 18.0.1.1.0
------------------

Convierte el icono informativo en un control funcional de cámara. Solicita la
cámara trasera del dispositivo, detecta QR y Code128 mediante las capacidades
seguras del navegador, completa el código leído y comunica claramente los
casos de permiso denegado o navegador incompatible.

Version 18.0.1.2.0
------------------

Integra html5-qrcode 2.3.8 (Apache-2.0) como lector alternativo. Usa la
detección nativa cuando está disponible y recurre a ZXing cuando Chrome o el
dispositivo no proporcionan BarcodeDetector, manteniendo QR y Code128 dentro
del mismo asistente de Odoo.

Version 18.0.1.2.1
------------------

Mantiene el contenedor HTML del lector montado durante todo el ciclo de la
vista y valida su referencia antes de iniciar la cámara. Evita la condición de
carrera de OWL que podía intentar crear html5-qrcode antes de renderizar el
elemento de video.

Version 18.0.1.2.2
------------------

Elimina el recorte cuadrado que podía excluir los extremos de Code128 largos,
decodifica todos los formatos soportados sobre el cuadro completo y agrega la
captura de una foto como alternativa móvil estándar usando el mismo motor
integrado, sin aplicaciones externas.

Version 18.0.1.3.0
------------------

Sustituye la deteccion en vivo de html5-qrcode y del detector incompleto del
navegador por el motor ZXing que incorpora Odoo 18. Solicita la camara trasera
en alta resolucion, analiza el cuadro completo y admite QR, Code128, EAN y los
demas formatos soportados por Odoo. La captura fotografica queda como respaldo
para QR y comunica que los codigos lineales se leen con la camara en vivo.

Version 18.0.1.4.0
------------------

Integra el lector movil con las sesiones auditables de conteo fisico por
variantes e items. Cada barcode reconocido registra automaticamente la cantidad
configurada, muestra existencias teoricas, conteo y diferencias, y conserva la
revision gerencial antes de aplicar cualquier ajuste de inventario.

Version 18.0.1.4.1
------------------

Agrega dentro del formulario movil un boton visible para iniciar la sesion,
cargar las existencias y activar el lector, evitando que el control quede
oculto en el encabezado compacto de Odoo. Traduce las acciones principales y
muestra una guia clara mientras la sesion permanece en borrador.

Version 18.0.1.4.2
------------------

Envia el barcode detectado directamente a la operacion de conteo, sin guardar
previamente todo el formulario movil. Elimina la carrera que producia el error
de barcode vacio y reduce el tiempo entre la lectura y su registro.

Version 18.0.1.4.3
------------------

Integra el boton de registro manual dentro del lector movil y conserva en el
componente el valor visible. Camara y escritura usan la misma operacion directa,
evitando una segunda llamada vacia desde el boton convencional del formulario.

Version 18.0.1.5.0
------------------

Optimiza la camara movil para EAN, UPC, Code128 y QR con resolucion equilibrada
y enfoque continuo. Muestra inmediatamente el producto, barcode, cantidad
acumulada y hora de la ultima lectura, y prioriza las lineas ya contadas.

Version 18.0.1.5.1
------------------

Restringe la lectura de labels DoorAndDoor a Code128 y exige dos detecciones
consecutivas iguales. Evita que un fragmento desenfocado sea interpretado como
un EAN corto distinto del barcode impreso.

Version 18.0.1.5.2
------------------

Agrega una lista operativa independiente con los productos ya contados,
ordenados por la lectura mas reciente, mostrando barcode, esperado, contado y
diferencia para evitar escaneos repetidos por falta de confirmacion visual.

Version 18.0.1.5.3
------------------

Prioriza el detector nativo optimizado de Chrome/Android y conserva ZXing como
respaldo. Lee una vez el Code128 verificado y usa una resolucion equilibrada,
reduciendo el tiempo de captura sin volver a habilitar EAN parciales.

Version 18.0.1.5.4
------------------

Sustituye el análisis manual de cuadros por el lector continuo html5-qrcode,
optimizado para la cámara trasera y una región horizontal Code128. Mantiene QR
para documentos y envía la primera lectura válida directamente al conteo.

Version 18.0.1.5.5
------------------

Analiza el cuadro completo para no recortar los extremos ni las zonas blancas
del Code128. Solicita alta definición y aplica enfoque continuo y zoom moderado
cuando la cámara Android los ofrece, conservando un ritmo estable de lectura.

Version 18.0.1.5.6
------------------

Conserva la región horizontal preferida por los operadores para encuadrar el
Code128 y mantiene el enfoque continuo y zoom cuando el móvil los soporte.

Version 18.0.1.5.7
------------------

Elimina la captura fotográfica alternativa y deja como única opción visual el
lector continuo Usar cámara, ya validado por los operadores en dispositivos
móviles. Conserva la entrada escrita para contingencias y lectores físicos.

Version 18.0.1.5.8
------------------

Integra el lector continuo Usar cámara dentro de Recibir con hanger. Cada
Code128 reconocido registra una unidad directamente, refresca las cantidades
contadas y conserva la escritura manual como contingencia.

Version 18.0.1.6.0
------------------

Mantiene abierta la pantalla del lector durante recepciones masivas. Cada
disparo del hanger terminado en Enter o cada lectura valida de cámara registra
una unidad por RPC, limpia la entrada y muestra producto y cantidad acumulada
sin recargar el formulario. La cámara exige retirar el mismo label del cuadro
antes de admitir otra lectura idéntica para evitar duplicados por fotogramas.

Version 18.0.1.6.1
------------------

Activa explícitamente el modo continuo en el conteo físico. Cada disparo del
hanger terminado en Enter registra la lectura por RPC, conserva el foco en la
entrada y actualiza el producto y la cantidad acumulada sin recargar la vista.

Version 18.0.1.7.0
------------------

Habilita el conteo continuo con hanger exclusivamente en las entregas de
Pickup Orders. La opción aparece en el pedido de recogida y en su operación de
salida; contar prepara cantidades, pero no valida automáticamente la entrega.

Version 18.0.1.7.1
------------------

Muestra la acción de conteo con hanger dentro de la operación móvil abierta al
escanear el QR de una entrega de Pickup Order, sin habilitarla para otras
entregas de salida.

Version 18.0.1.8.0
------------------

Extiende el conteo continuo con hanger a recepciones, entregas y traslados
internos, además de las sesiones de conteo físico. Las operaciones de salida e
internas solo aceptan productos previstos, respetan el acceso por almacén y no
se validan automáticamente al aplicar cantidades.

Version 18.0.1.9.0
------------------

Define perfiles operativos uniformes para Hanger: contador, entregas,
almacenero y supervisor. Cada perfil exige al menos un almacén autorizado,
conserva la administración general fuera de los dispositivos operativos y
permite auditar desde el usuario qué plantilla funcional se le asignó.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "doorandoor_process_control",
        "doorandoor_stock_labels",
        "doorandoor_sales_new",
        "doorandoor_inventory_variant_count",
    ],
    "data": [
        "security/mobile_inventory_count_security.xml",
        "security/hanger_role_security.xml",
        "security/ir.model.access.csv",
        "views/delivery_queue_views.xml",
        "views/mobile_picking_views.xml",
        "views/report_delivery_partial.xml",
        "views/pickup_order_views.xml",
        "wizard/document_scan_wizard_views.xml",
        "views/menu_views.xml",
        "views/mobile_inventory_count_views.xml",
        "views/mobile_receipt_scan_views.xml",
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_mobile_hanger/static/lib/html5_qrcode/html5-qrcode.min.js",
            "doorandoor_mobile_hanger/static/src/js/camera_barcode_field.js",
            "doorandoor_mobile_hanger/static/src/js/live_hanger_monitor.js",
            "doorandoor_mobile_hanger/static/src/xml/camera_barcode_field.xml",
        ],
    },
    "installable": True,
    "application": True,
}
