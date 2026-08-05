# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Control de Cobros",
    "version": "18.0.1.7.6",
    "category": "Accounting",
    "summary": "18.0.1.7.6 - Corrige estado final pagado tras cobros parciales/completos en control de cobros",
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
    """,
    "author": "Hanoi Calvo Fernandez for Doorandoor",
    "website": "https://gestion.doorandoor.com",
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
        "views/account_move_views.xml",
        "views/control_cobros_report.xml",
        "views/cobro_report_wizard_views.xml",
        "views/cobro_match_wizard_views.xml",
        "views/cobro_report_pdf.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
}
