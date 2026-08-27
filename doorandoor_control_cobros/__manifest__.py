# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Control de Cobros",
    "version": "18.0.2.8.0",
    "category": "Accounting",
    "summary": "18.0.2.8.0 - Cobra y concilia deudas de crédito autorizado por cliente",
    "description": """
DoorAndDoor Control de Cobros
=============================

Modulo base para separar el reporte de cobro realizado por ventas
de la validacion final realizada por contabilidad.

Reglas iniciales
----------------

- los diarios/metodos de validacion inmediata mantienen el flujo normal
- los diarios marcados con control de cobro requieren revision previa
- el modulo crea una capa operativa antes del impacto contable final

Historial resumido
------------------

- 18.0.2.8.0
  Permite seleccionar una deuda abierta de credito autorizado al registrar un
  cobro real. Crea su Control de Cobro, admite amortizaciones parciales y al
  validar concilia el pago contra la subcuenta 122xxx del cliente sin modificar
  nuevamente la factura original ya liquidada.

- 18.0.2.7.5
  Los operadores del grupo Registrar pagos oficiales pueden consultar en la
  ficha del cliente el credito autorizado, utilizado y disponible. Los campos
  son de solo lectura para ese rol; el limite continua editable unicamente por
  Administrador/Ajustes y la subcuenta tecnica permanece restringida.

- 18.0.2.7.4
  Impide asociar un pago oficial a mas de un control o a una factura distinta,
  incluso ante operaciones concurrentes. Restringe su manipulacion a Control
  de Cobros, muestra el control correspondiente a la factura real y bloquea el
  rechazo ambiguo de pagos que ya fueron conciliados contablemente.

- 18.0.2.7.3
  Publica una señal final después de conciliar y recalcular la factura, evitando
  que las pantallas abiertas conserven el estado intermedio de pago en revisión.
  Consolida además el bloqueo contable del diario de crédito autorizado.

- 18.0.2.7.2
  Incorpora al OTP la URL dinamica de la instancia y un enlace directo a la
  factura, reutilizando web.base.url en local, pruebas y produccion.

- 18.0.2.7.1
  Amplia el mensaje OTP de Telegram con cliente, factura, vendedor, productos,
  importes, saldo de factura y credito disponible antes y despues de la venta.

- 18.0.2.7.0
  Agrega lista, tabla dinamica, grafico y PDF de creditos autorizados por
  cliente. Calcula credito usado, pagos reales y saldo pendiente desde el
  residual contable de cada subcuenta y enlaza factura y asiento de origen.

- 18.0.2.6.3
  El codigo deja de ser obligatorio antes de pulsar Enviar codigo y pasa a ser
  obligatorio solamente despues de crear la solicitud de autorizacion.

- 18.0.2.6.2
  Registra el estado, fecha e identificador del mensaje OTP aceptado por
  Telegram y corrige el tipo tecnico del limite de credito por compania.

- 18.0.2.6.1
  Impide crear, modificar o validar pagos manuales de entrada y salida con el
  diario de credito autorizado. Su uso queda limitado al asistente de una
  factura confirmada y a la validacion del codigo del cliente.

- 18.0.2.6.0
  Incorpora un diario de credito autorizado, limite administrado por cliente,
  codigo temporal de seis digitos enviado al bot de pruebas y bloqueo absoluto
  de la liquidacion sin autorizacion. La factura se liquida reclasificando su
  saldo como cuenta por cobrar financiada, sin simular una entrada bancaria.

- 18.0.2.5.5
  Conserva en cola los eventos de pago que llegan durante una recarga y evita
  registrar como sincronizado un estado mas nuevo que aun no fue renderizado.
  El aviso parcial cambia al total sin recargar la pagina completa.

- 18.0.2.5.4
  Atiende la senal nativa de cambio de bundle y recarga automaticamente las
  sesiones sin cambios pendientes. Evita solicitar combinaciones de teclas a
  los operadores despues de futuras actualizaciones del frontend.

- 18.0.2.5.3
  Incorpora en pagos y controles de cobro un boton exclusivo de
  Administracion/Ajustes que recalcula la factura, registra auditoria y vuelve
  a notificar todas las pantallas abiertas sin crear pagos ni asientos nuevos.

- 18.0.2.5.2
  Agrega una comprobacion ligera y segura del estado de facturas abiertas cada
  diez segundos y al regresar a la pestana. Mantiene el WebSocket inmediato y
  recupera cambios perdidos por reconexiones, cache o reinicios sin requerir F5.

- 18.0.2.5.1
  Evita la recarga redundante de la prefactura cuando Crear factura navega al
  nuevo documento y protege las recargas asincronas si el formulario ya fue
  desmontado, eliminando el error de cliente Component is destroyed.

- 18.0.2.5.0
  Muestra en el control de cobros y en el reporte de factura el saldo contable
  disponible del cliente en anticipos, incluso cuando la factura está pagada.

- 18.0.2.4.1
  Hace buscable la relacion calculada entre pago y control de cobro para que
  Odoo pueda resolver correctamente las dependencias y recomputaciones.

- 18.0.2.4.0
  Amplia el refresco WebSocket a cotizaciones, prefacturas y facturas, y
  fuerza la recarga segura del modelo tras confirmar o reabrir documentos.
  Las vistas con cambios sin guardar mantienen la advertencia protectora.

- 18.0.2.3.3
  El boton Registrar pago de una factura nunca crea pagos, asientos ni
  conciliaciones al seleccionar un diario controlado, incluso para usuarios
  administradores. Solo genera la espera comercial; el pago oficial debe
  ingresar exclusivamente por Control de Cobros/Pagos.

- 18.0.2.3.2
  En diarios controlados oculta la cinta verde nativa de pago en proceso
  mientras el cobro espera validacion y conserva la cinta azul Pago en
  revision, sin alterar saldo, asiento ni conciliacion.

- 18.0.2.3.1
  El pago oficial reutiliza el reporte pendiente de la factura, priorizando
  la misma via de cobro, aunque su importe real sea parcial o excedido.
  El control adopta el diario y el monto reales sin duplicar registros.

- 18.0.2.3.0
  En diarios controlados, Ventas solo selecciona la via y envia la factura a
  espera de pago por su saldo real. Se ocultan los datos contables del
  asistente y el pago oficial posterior reutiliza el reporte pendiente.

- 18.0.2.2.3
  Evita ejecutar manualmente los computes contables despues de conciliar.
  Odoo actualiza el saldo y el estado de pago mediante la conciliacion nativa,
  sin intentar reescribir lineas protegidas de una factura confirmada.

- 18.0.2.2.0
  Emite eventos operativos en tiempo real al crear, vincular, validar,
  rechazar o modificar controles. Las vistas abiertas de factura, pago,
  control y credito se recargan si no tienen cambios pendientes.

- 18.0.2.1.0
  Registrar pago desde Ventas en diarios controlados crea solamente un Control
  de Cobro sin asiento ni conciliacion. El pago oficial reutiliza el reporte
  compatible y la automatizacion cuenta pagos contables unicos, no importes
  reportados, evitando duplicar dinero sobre una factura.

- 18.0.2.0.0
  Asocia pagos por la referencia INV encontrada en el memo aunque el pagador
  sea distinto, conserva el pagador informado y automatiza el control segun
  el porcentaje acumulado del total de la factura. Las facturas fabricables
  liberan la MO al 50%; por debajo quedan en revision y el despacho conserva
  la exigencia de pago total. Los excedentes se trasladan a una subcuenta
  conciliable por cliente bajo 120000. En contabilidad estadounidense se crea
  la cuenta madre cuando no exista.

- 18.0.1.12.1
  Las companias sin cuenta propia de anticipos utilizan la 120000 como cuenta
  madre compartida, sin bloquear facturas ni pagos y conservando el detalle
  por compania y cliente para su reclasificacion contable posterior.

- 18.0.1.12.0
  Traslada excedentes validados a la cuenta 120000 Pagos Anticipados,
  aplica automaticamente esos saldos al publicar nuevas facturas y mantiene
  trazabilidad por cliente, pago, control y asiento contable.

- 18.0.1.11.0
  Agrega una vista gerencial de creditos calculada desde partidas contables
  abiertas, con saldos original, aplicado y disponible, historial de
  aplicaciones y acceso directo al asiento contable.

- 18.0.1.10.0
  Al aplicar un credito validado a otra factura crea un control con origen,
  saldo anterior, importe aplicado y saldo restante. Si liquida la factura,
  actualiza su estado y reutiliza el flujo de liberacion de MO y pickings.

- 18.0.1.9.1
  Conserva intacta la cinta nativa de factura pagada y agrega cintas propias
  para pagos en revision y pagos parciales validados.

- 18.0.1.0.0
  Version inicial del modulo.
  Se crea la estructura base de `Control de Cobros`, el menu principal,
  el modelo operativo de control de cobro, la extension inicial en
  facturas y la configuracion base de diarios.

- 18.0.1.0.1
  Se corrige la extension de `account.journal` para esta base Odoo 18.
  El formulario de diarios muestra el bloque `Control de cobros` y el
  guardado sincroniza correctamente `Flujo de cobro` con
  `Requiere control de cobro`.

- 18.0.1.0.2
  Se conecta `Registrar pago` con `Control de Cobros`.
  Los pagos hechos con diarios controlados crean automaticamente un
  registro visible para revision, bloquean la liberacion operativa
  mientras el control este pendiente y liberan factura, fabricacion y
  despacho solo al validar el control.

- 18.0.1.0.3
  La vista principal de `Control de Cobros` deja de abrir filtrada solo
  por pendientes.
  Los controles validados o cerrados tambien permanecen visibles en la
  lista general para consulta y trazabilidad operativa.

- 18.0.1.0.4
  La validacion del control confirma el `account.payment` enlazado antes
  de resincronizar la factura.
  Esto permite que el pago genere su asiento, cambie el estado de la
  factura y dispare la liberacion de fabricacion o despacho cuando el
  cobro es validado por `Control de Cobros`.

- 18.0.1.0.5
  La validacion del control completa el flujo contable del pago
  controlado.
  Si el pago aun no tiene asiento, se le asigna cuenta transitoria, se
  genera el asiento, se reconcilia contra la factura y luego se valida
  para que el estado de la factura y la liberacion operativa queden
  sincronizados.

- 18.0.1.0.6
  Las facturas validadas por `Control de Cobros` dejan de mostrarse en
  `Procesando el pago` cuando ya quedaron saldadas.
  El modulo fuerza `payment_state = paid` solo para facturas de cliente
  con control validado, residual en cero y sin controles pendientes,
  sin alterar la personalizacion global que usa `in_payment`.

- 18.0.1.0.7
  La validacion del control ahora fuerza la resincronizacion inmediata
  del estado operativo de la factura.
  Se recalculan `ddc_collection_state` y `payment_state` en el momento
  de validar para que las facturas controladas no queden visualmente en
  `Procesando el pago` despues de cerrar el flujo.

- 18.0.1.0.8
  Se agrega un reporte base de pagos dentro de `Control de Cobros`.
  La lista y el reporte muestran el estado del control, el estado del
  pago real y el estado actual de la factura, con agrupacion por diario
  y por estados para consulta operativa de contabilidad.

- 18.0.1.0.9
  Se corrige la vista pivote del `Reporte de pagos`.
  Se elimina una medida invalida sobre `id` que provocaba el error
  `No aggregate function has been provided for the measure 'id'` al
  abrir el reporte en Odoo.

- 18.0.1.1.0
  Se agrega un PDF imprimible para `Control de Cobros`.
  El documento muestra factura, cliente, diario, monto reportado,
  referencia, estado del control y espacios de validacion operativa.
  Ademas, la factura expone un estado funcional del pago para distinguir
  revision, validacion y rechazo sin despublicar la factura.

- 18.0.1.1.1
  El menu `Reporte de pagos` deja de abrir directo en vista pivote.
  Ahora entra primero por lista y formulario para facilitar la
  navegacion operativa y la impresion del PDF de cada control.

- 18.0.1.2.0
  Se agrega un `wizard` base para evolucionar los PDF de cobros.
  El submenu `Asistente PDF` permite centralizar filtros, opciones de
  formato y futuras decisiones con clientes y contabilidad sin romper el
  flujo actual de impresion del control individual.

- 18.0.1.2.1
  Se corrige el orden de carga del `wizard` PDF en el manifiesto.
  La accion del asistente ahora se registra antes del submenu para evitar
  el error `External ID not found` durante la actualizacion del modulo.

- 18.0.1.2.2
  Se reorganiza la navegacion de `Reportes` para mostrar submenus reales.
  `Reporte de pagos` y `Asistente PDF` quedan debajo del bloque
  `Reportes`, y se agrega acceso al modelo transient del wizard para su
  uso operativo desde la interfaz.

- 18.0.1.2.3
  El menu `Reportes` deja de abrir una accion directa.
  Ahora funciona como contenedor visual para mostrar debajo
  `Reporte de pagos` y `Asistente PDF`, evitando que el clic entre
  directo al listado o al pivote.

 - 18.0.1.2.4
  El `wizard` de PDF agrega seleccion por clientes como primer filtro
  operativo. La estructura queda preparada para sumar despues filtros
  adicionales como vendedor sin rehacer la base del asistente.

- 18.0.1.2.5
  El `wizard` de PDF agrega seleccion por vendedores como segundo filtro
  operativo. Con esto el asistente ya permite preparar variantes del
  reporte por cliente y por responsable comercial desde la misma base.

- 18.0.1.3.0
  El `wizard` deja de ser solo un esqueleto y ahora genera un PDF
  preliminar real con filtros aplicados, resumen de totales y detalle de
  controles. Esta salida sirve como base de presentacion para clientes y
  contabilidad mientras se definen variantes visuales y campos extra.

- 18.0.1.3.1
  Se corrige el nombre tecnico del reporte QWeb del `wizard` para que
  Odoo pueda crear el modelo `report.*` sin exceder el limite de nombre
  de tabla en PostgreSQL. Con esto la version preliminar del PDF ya
  puede cargarse correctamente en la base de pruebas.

- 18.0.1.3.2
  Se corrige el XML del PDF preliminar del `wizard`, eliminando una
  entidad invalida para QWeb. Esto permite que el archivo del reporte
  cargue correctamente durante la actualizacion del modulo.

- 18.0.1.3.3
  Se alinea el `report_name` del PDF preliminar con el XMLID real de la
  plantilla QWeb y con el modelo abstracto `report.*`. Esto corrige el
  error `External ID not found` al imprimir el PDF desde el wizard.

- 18.0.1.4.0
  Las transiciones del `Control de Cobros` ahora publican mensajes en el
  chatter del control y de la factura, devuelven notificaciones nativas
  de Odoo al usuario que ejecuta la accion y recalculan el estado visual
  de la factura para mostrar rechazo en rojo y revision como `En proceso
  de pago`.

- 18.0.1.4.1
  La factura ahora muestra carteles visibles para revision, validacion y
  rechazo dentro del formulario. Ademas, `Registrar pago` publica desde
  el inicio un mensaje en el chatter de la factura para que ventas vea
  el proceso en tiempo real sin depender solo del control de cobros.

- 18.0.1.4.2
  Se corrige la estructura XML de la vista de factura usada por los
  nuevos carteles del control de cobros. Esto evita el error de carga
  `Opening and ending tag mismatch` durante la actualizacion del modulo.

- 18.0.1.4.3
  La cinta diagonal de la factura deja de depender solo del texto base
  `En proceso de pago` y ahora se alinea con el flujo del modulo:
  muestra `Pago en revision` durante el control contable y
  `Factura rechazada` cuando el pago es rechazado.

- 18.0.1.4.4
  Se corrige la herencia tecnica usada para ajustar la cinta diagonal de
  la factura, evitando selectores invalidos en Odoo. La barra
  horizontal informativa del proceso se conserva sin cambios.

- 18.0.1.4.5
  Los mensajes del chatter del flujo de cobros ahora se publican con
  formato HTML real y un texto mas legible para ventas y contabilidad.
  Esto evita que se muestren etiquetas tecnicas crudas como `<p>` y
  mejora la lectura del historial en la factura y en el control.

- 18.0.1.5.0
  La validacion contable del `Control de Cobros` ahora fuerza primero el
  posteado del pago y luego reconcilia sus lineas contables contra la
  factura usando cuentas conciliables de cliente/proveedor. Con esto los
  totales pendientes, el residual de la factura y la salida a libros
  mayores quedan alineados con el pago realmente validado.

- 18.0.1.6.0
  Se prepara la Fase 1 para pagos parciales y pagos por identificar.
  `Control de Cobros` ahora soporta controles sin factura asociada,
  estado de asociacion, marca de pago parcial y monto validado. La
  factura agrega totales reportados, validados, rechazados y pendientes
  para analizar varios tramos de pago sobre un mismo documento.

- 18.0.1.6.1
  Se agregan documentos funcionales en `docs/` para aterrizar el flujo
  de pagos parciales, pagos por identificar y el proceso operativo
  completo cuando el pago se detecta antes de conocer la factura
  correcta.

- 18.0.1.7.0
  Se cierra el flujo operativo para pagos detectados antes de conocer la
  factura correcta. `Control de Cobros` ahora agrega un asistente para
  asociar cliente, factura y pago contable existente al control
  detectado, dejando el registro listo para continuar la revision
  contable sin depender de una edicion tecnica del formulario.

- 18.0.1.7.1
  Se corrige la creacion manual de `account.payment` desde `Control de
  Cobros` para Odoo 18. El flujo ya no intenta escribir el campo
  invalido `ref`, usando solo `memo` para conservar la referencia del
  pago detectado.

- 18.0.1.7.2
  Se agrega navegacion directa a `Pagos` dentro del modulo y se mejora
  la busqueda cruzada en `Control de Cobros`. Ahora existe un submenu
  operativo para pagos de cliente y un filtro `Con pago contable` para
  distinguir rapidamente los controles ya enlazados con un pago real.

- 18.0.1.7.3
  Se agregan alertas nativas para evitar reprocesar acciones ya hechas
  en `Control de Cobros`. `Reportar`, `Asociar`, `Crear pago`,
  `Pendiente`, `Revisar` y `Validar` ahora avisan cuando el usuario
  repite un paso; `Rechazar` se mantiene disponible para registrar
  nuevas razones o reiteraciones del rechazo.

- 18.0.1.7.4
  Se limpian los mensajes publicados en el chatter del flujo de cobros.
  El usuario ya no ve etiquetas HTML crudas dentro del texto operativo y
  los avisos quedan redactados de forma mas natural para ventas y
  contabilidad.

- 18.0.1.7.5
  Se corrigen etiquetas visuales del flujo de cobros controlados en
  factura. Se normaliza `Pago en revisión` y se agrega etiqueta
  especifica para `Pago parcial validado` en alerta y cinta, evitando
  inconsistencias cuando el control valida solo una parte del cobro.

- 18.0.1.7.6
  Se corrige el calculo de estado final en facturas con multiples
  controles de cobro. Si el residual de la factura llega a cero tras
  validar un segundo pago (por ejemplo Zelle), el estado funcional pasa
  a `Pago validado` y la factura queda `Pagada`, evitando que permanezca
  erroneamente en `Pago parcial validado`.

- 18.0.1.8.0
  El formulario de pago incorpora un selector de factura existente para
  cobros de cliente. La asociacion valida cliente, compania, moneda,
  tipo de documento y exclusividad pago-factura; al confirmar crea el
  control de cobro sin omitir la revision y conciliacion ya establecidas.

- 18.0.1.8.1
  Se permite que el importe de un pago sea menor que el saldo pendiente
  para completar el flujo de pagos parciales. Cada pago conserva una
  sola factura asociada, mientras una factura puede acumular pagos y
  controles sucesivos hasta quedar totalmente saldada.

- 18.0.1.8.2
  Al seleccionar una factura en un nuevo pago se muestra su saldo
  pendiente actualizado y se indica si el importe liquidara totalmente
  la deuda o se aplicara como un nuevo pago parcial.

- 18.0.1.8.3
  La validacion usa la asignacion contable estandar de Odoo para reducir
  realmente el residual de la factura, incluyendo pagos que ya llegaron
  al estado pagado. Si la deuda no disminuye, el control no se marca como
  validado; los controles inconsistentes existentes pueden reprocesarse.

- 18.0.1.8.4
  La validacion genera el asiento contable de pagos que quedaron pagados
  sin `move_id`, o recupera el asiento activo previamente creado para no
  duplicarlo. Solo despues publica, concilia y actualiza el residual.

- 18.0.1.8.5
  Los pagos superiores al residual dejan de bloquearse. La conciliacion
  liquida la factura por su saldo y conserva la diferencia abierta en la
  cuenta por cobrar como credito a favor del cliente, mostrando ambos
  importes en el formulario del pago.

- 18.0.1.9.0
  El pago incorpora una coleccion de documentos asociados para adjuntar
  capturas, imagenes, PDF, textos y documentos escaneados. Los respaldos
  tambien pueden consultarse desde el Control de Cobro relacionado.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "account",
        "doorandoor_sales_new",
    ],
    "data": [
        "security/control_cobros_security.xml",
        "security/ir.model.access.csv",
        "views/control_cobros_views.xml",
        "views/account_journal_views.xml",
        "views/account_payment_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_move_views.xml",
        "views/invoice_credit_report.xml",
        "views/res_partner_views.xml",
        "views/control_cobros_report.xml",
        "views/cobro_report_wizard_views.xml",
        "views/cobro_match_wizard_views.xml",
        "views/cobro_report_pdf.xml",
        "views/authorized_credit_report.xml",
        "views/customer_credit_views.xml",
        "views/menu_views.xml",
        "views/credit_authorization_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_control_cobros/static/src/js/payment_operational_refresh.js",
        ],
    },
    "installable": True,
    "application": True,
}
