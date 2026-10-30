{
    "name": "DoorAndDoor Logistica Historica de Arrancada",
    "version": "18.0.1.7.0",
    "category": "Operations/Inventory",
    "summary": "18.0.1.7.0 - Convierte stock histórico aprobado en traslados y entregas auditables",
    "description": """
DoorAndDoor Logistica Historica de Arrancada
=============================================

Version 18.0.1.7.0
-------------------

* Aprueba la propuesta de stock existente y reserva exactamente sus labels.
* Crea entrega directa cuando el stock ya está en el almacén destino o un
  traslado por cada almacén origen real cuando debe viajar.
* Espera la validación Hanger de todos los traslados y recepciones antes de
  liberar una sola entrega final al cliente.
* Conserva labels pendientes en los backorders de conteos parciales.

Version 18.0.1.6.1
-------------------

* Muestra los códigos legibles de los labels existentes en lugar de la
  referencia técnica del modelo y su ID interno.
* Mantiene intactas las relaciones con seriales, el inventario y la propuesta
  auditada.

Version 18.0.1.6.0
-------------------

* Clasifica cada histórico entre consumo de stock Odoo, exclusión auditada y
  regularización excepcional.
* Propone por ITEM los labels activos ya existentes, incluso desde varios
  almacenes, sin crear recepciones, stock ni códigos nuevos.
* Conserva PDF, huella, motivo y propuesta revisable antes de liberar cualquier
  movimiento logístico.

Version 18.0.1.5.8
-------------------

* Incluye en el HDEL todos los backorders y parciales enlazados de recepción,
  traslado y entrega, conservando visibles los documentos principales.
* Expande la vista de operaciones relacionadas únicamente mediante enlaces
  explícitos y permite auditar desde qué documento nació cada parcial.

Version 18.0.1.5.7
-------------------

* Los operadores autorizados abren las operaciones y recepciones históricas
  enlazadas sin necesitar Administrador/Ajustes.
* La elevación se limita a leer la definición técnica de la ventana; los
  documentos continúan filtrados por las reglas y almacenes del usuario real.

Version 18.0.1.5.6
-------------------

* En una recepción parcial reserva para el traslado únicamente los labels ya
  confirmados por Hanger en el predespacho; los no escaneados permanecen fuera
  de la cadena y pendientes de recepción.

Version 18.0.1.5.5
-------------------

* La validación en origen crea el control enlazado de recepción destino con
  elevación técnica limitada, sin conceder al operador acceso general al otro
  almacén y conservando los responsables reales de cada etapa.

Version 18.0.1.5.4
-------------------

* Conserva la unidad de medida del ITEM al crear el traslado parcial desde la
  línea física de la recepción histórica.

Version 18.0.1.5.3
-------------------

* Una recepción histórica parcial crea la cadena posterior únicamente con las
  cantidades y labels contados por Hanger.
* Conserva el saldo no recibido en el backorder nativo y evita trasladar o
  entregar productos que todavía no llegaron físicamente.

Version 18.0.1.5.0
------------------

* Inicia Zoho y QuickBooks únicamente con recepción, albarán y labels PDF.
* Crea traslado o entrega solo después de validar la recepción con Hanger.
* Crea la entrega interciudad únicamente después de validar la recepción destino.
* Bloquea la confirmación directa que omite el conteo físico.

Version 18.0.1.4.18
--------------------

* Marca como listo el único ITEM de una recuperación al leer su último label.
* Confirma por el flujo completo las recuperaciones Hanger sin faltantes, sin
  intentar cerrarlas incorrectamente como recepciones parciales.

Version 18.0.1.4.17
--------------------

* Cierra la regularización histórica cuando Hanger valida todos sus labels.
* Conserva operador, ubicación, recepción y reserva del traslado siguiente.

Version 18.0.1.0.0
-------------------

* Incorpora una bandeja independiente para organizar ventas del sistema
  anterior sin crear facturas contables.
* Registra existencias fisicas faltantes mediante una entrada de inventario
  inicial auditable o etiqueta existencias ya cargadas, evitando duplicarlas.
* Genera e imprime labels DoorAndDoor antes de aplicar inventario y conserva
  documento, usuario, evidencia, almacen, lote y ubicacion.
* Calcula la preparacion fisica real de cada entrega: solicitado, localizado,
  reservado y pendiente, sin confundir picking creado con mercancia lista.
* Bloquea cargas historicas incompletas y enlaza recepcion, traslado,
  predespacho, camion y entrega final.
* Define roles de Consulta, Operador y Supervisor. Yuliet recibe el rol de
  Supervisor durante la instalacion si su usuario se encuentra activo.

Version 18.0.1.0.1
-------------------

* Corrige el dominio web de la ubicacion fisica: filtra por el almacen
  seleccionado sin producir InvalidDomainError mientras el formulario aplica
  sus valores iniciales.

Version 18.0.1.0.2
-------------------

* Impide iniciar una regularizacion cuando la operacion historica ya esta
  completamente reservada.
* La cantidad fisica comienza en cero y debe declararse expresamente.
* Predespacho exige una ubicacion DoorAndDoor de predespacho; stock general no
  puede utilizarse accidentalmente como predespacho.

Version 18.0.1.0.3
-------------------

* Permite guardar y revisar el borrador antes de escribir la comprobacion
  fisica; el dato y la evidencia siguen siendo obligatorios para preparar
  labels, mediante mensajes operativos claros.
* Hereda tanto las evidencias enlazadas como los adjuntos directos del
  documento historico.

Version 18.0.1.0.4
-------------------

* Documenta el diagnostico obligatorio antes de regularizar una venta
  historica y diferencia existencias, reservas, traslados y faltantes fisicos.
* Corrige la guia para no presentar HDEL/2026/00011 como una regularizacion:
  sus unidades reservadas deben continuar por DD/OUT/00043.
* Define la futura biblioteca de guias operativas por modulo, rol y proceso.

Version 18.0.1.0.5
-------------------

* Actualiza la guia operativa a la version 1.2 con una matriz inicial para
  seleccionar entre OCR, operacion existente, regularizacion, recepcion,
  traslado, predespacho, stock y producto especial historico.
* Unifica la continuidad diaria en Operaciones - Entregas y traslados y
  documenta el alcance de los responsables locales por sede.

Version 18.0.1.1.0
-------------------

* Inicia desde la factura historica el ciclo directo del mismo almacen y crea
  una recepcion auditable con los ITEM y cantidades pendientes ya definidos.
* Crea un predespacho exclusivo para la recepcion, genera labels sin volver a
  cargar productos y conserva unidos factura, recepcion y ubicacion fisica.
* Despues de confirmar existencias crea la salida desde ese predespacho,
  reserva exactamente los labels recibidos y abre el conteo Hanger.
* Separa claramente los cinco pasos operativos y mantiene fuera de esta primera
  etapa los traslados historicos entre ciudades.

Version 18.0.1.1.1
-------------------

* Reutiliza la linea detallada que Odoo prepara al confirmar la recepcion y
  evita duplicar la cantidad procesada antes de validar el inventario.

Version 18.0.1.1.2
-------------------

* Permite que el Supervisor historico autorizado confirme la recepcion con
  elevacion tecnica acotada, conservando al usuario real en la auditoria y sin
  concederle permiso general para validar operaciones fuera del flujo.

Version 18.0.1.2.0
-------------------

* Agrega en cada documento de almacén el botón Operaciones enlazadas para
  recorrer recepciones, despachos de traslado, recepciones destino y entregas.
* Usa únicamente relaciones explícitas del sistema y respeta las reglas de
  almacén del operador; nunca vincula documentos por textos coincidentes.
* Abre directamente la operación cuando existe una sola y presenta una lista
  controlada cuando el ciclo contiene varias etapas.

Version 18.0.1.3.0
-------------------

* Convierte la factura histórica en el panel único del ciclo logístico.
* Después de confirmar la recepción permite escoger entre traslado interno o
  entrega al cliente sin volver a introducir productos ni cantidades.
* Crea y enlaza la operación elegida, conserva el documento precedente y deja
  auditoría completa en la factura, la recepción y la nueva operación.
* El mismo selector funciona desde cualquier operación de almacén sin enlace,
  copiando sus líneas para acelerar también los flujos no históricos.

Version 18.0.1.3.1
-------------------

* Permite completar o corregir la evidencia y la comprobación física mientras
  la recepción histórica está en Borrador o Recepción preparada.
* Conserva ambos campos bloqueados desde Labels preparados para proteger la
  evidencia que revisará la supervisora antes de confirmar el inventario.

Version 18.0.1.3.2
-------------------

* Elimina el bloqueo de Preparar labels por falta de una descripción manual de
  la comprobación física, ya que ese texto no constituye una validación fiable.
* Mantiene como trazabilidad objetiva el documento adjunto, los ITEM,
  cantidades, labels, recepción, usuario y fechas del proceso.
* Conserva la nota física como observación opcional para incidencias o detalles
  extraordinarios, sin agregar un paso obligatorio al operador.

Version 18.0.1.3.3
-------------------

* Corrige las ventas históricas cuya entrega fue creada antes de terminar la
  recepción: al liberar la logística, cambia el origen desde stock general al
  predespacho específico del documento.
* Libera las reservas anteriores, reasigna la operación y reserva los labels
  recibidos, manteniendo recepción, entrega y auditoría dentro del mismo ciclo.

Version 18.0.1.3.4
-------------------

* En traslados históricos, abre la regularización sobre el almacén de destino
  y limita allí la selección de la ubicación física.
* Mantiene el almacén proveedor únicamente como origen del traslado y conserva
  la creación automática del predespacho exclusivo de cada documento.

Version 18.0.1.3.5
-------------------

* Al confirmar la recepción oficial de un traslado histórico, enlaza esa
  recepción y la entrega final dentro de la venta histórica.
* Reserva en la entrega los labels confirmados en el predespacho del documento,
  evitando operaciones finales sin unidades identificadas para Hanger.

Version 18.0.1.4.0
-------------------

* Crea desde la factura histórica la recepción física en origen, el traslado,
  la recepción en destino y la entrega final, todos enlazados desde el inicio.
* Genera los labels una sola vez en la recepción de origen y los reutiliza en
  el conteo Hanger, la recepción destino y la entrega al cliente.
* Mantiene bloqueada cada validación hasta completar físicamente la etapa
  anterior, conservando documentos, usuarios, fechas y lecturas auditables.

Version 18.0.1.4.1
-------------------

* Enlaza también los movimientos de la recepción destino con la entrega final
  para impedir que Odoo reserve o valide la salida antes de recibir la carga.

Version 18.0.1.4.2
-------------------

* Libera cualquier reserva automática tomada del stock general del destino al
  preparar la entrega y la deja dependiente de su recepción histórica.

Version 18.0.1.4.3
-------------------

* Permite comprobar con Hanger los labels de una recepción histórica validada
  por error desde el flujo estándar, sin repetir el movimiento de stock.
* Bloquea nuevas validaciones estándar mientras la regularización histórica
  conserve labels pendientes de confirmación.

Version 18.0.1.4.4
-------------------

* Permite cerrar la recuperación Hanger con faltantes cuando solo una parte de
  la mercancía histórica está físicamente disponible.
* Aplica y reserva únicamente los labels realmente contados; los restantes
  permanecen pendientes y documentados sin duplicar existencias.

Version 18.0.1.4.5
-------------------

* Al cerrar un conteo de recuperación, revierte de forma auditable la cantidad
  que una recepción histórica había cargado sin evidencia física.
* Ajusta la cadena logística a lo realmente contado y conserva en el HDEL el
  saldo pendiente por recibir de cada producto.

Version 18.0.1.4.6
-------------------

* Ejecuta las cantidades almacenables del retorno correctivo para que el stock
  físico coincida con los labels comprobados por Hanger.

Version 18.0.1.4.7
-------------------

* Permite marcar un ITEM histórico como no recibido y continuar con el siguiente
  producto antes de consolidar el cierre parcial de la recepción.

Version 18.0.1.4.8
-------------------

* Permite escanear aleatoriamente cualquier label esperado del documento y
  consolidar una sola vez el físico recibido y el saldo pendiente.

Version 18.0.1.4.9
-------------------

* Activa la interfaz de conteo libre con validación única en Odoo 18.

Version 18.0.1.4.10
--------------------

* Permite que cualquier operador autorizado del almacén finalice el conteo
  físico histórico sin requerir privilegios de supervisor.

Version 18.0.1.4.11
--------------------

* Registra cada label histórico aceptado como lectura y evento visible en el
  Monitoreo Hanger.

Version 18.0.1.4.12
--------------------

* Cuando la entrada incorrecta fue revertida completamente, crea un reingreso
  auditable únicamente con las unidades comprobadas por Hanger.

Version 18.0.1.4.13
--------------------

* Permite contar todos los labels históricos desde la pantalla móvil continua
  de Hanger y validar una sola vez el físico recibido.

Version 18.0.1.4.14
--------------------

* Permite al operador autorizado validar el conteo sin exponer el modelo
  administrativo de regularización y conserva su identidad en la auditoría.

Version 18.0.1.4.15
--------------------

* Valida técnicamente el reingreso físico sin conceder al operador permiso
  general para cerrar movimientos de inventario.

Version 18.0.1.4.16
--------------------

* Usa el usuario técnico solo para cerrar el movimiento generado y mantiene al
  operador Hanger real como responsable auditado.
""",
    "author": "DoorAndDoor",
    "maintainer": "DoorAndDoor Soporte",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "stock",
        "doorandoor_process_control",
        "doorandoor_inventory_variant_count",
        "doorandoor_import_historic_invoices",
        "doorandoor_cargas_control",
        "doorandoor_mobile_hanger",
    ],
    "data": [
        "security/historic_logistics_security.xml",
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "views/historic_regularization_views.xml",
        "views/historical_delivery_views.xml",
        "views/next_operation_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
}
