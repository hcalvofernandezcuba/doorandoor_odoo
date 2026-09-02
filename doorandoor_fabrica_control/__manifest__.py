# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Fabrica Control",
    "version": "18.0.1.5.1",
    "category": "Manufacturing",
    "summary": "18.0.1.5.1 - Instalación limpia segura del control de planificación",
    "description": """
DoorAndDoor Fabrica Control
===========================

Objetivo
--------

Coordinar el flujo fisico de la fabrica sobre los documentos nativos de Odoo:
liberacion por pago, solicitud y entrega de materiales, maquinado, ensamblaje,
control del producto terminado y entrega al almacen.

El modulo contempla dos fuentes de demanda: fabricacion vinculada a un cliente
y reposicion del stock vendido por cada almacen.

Historial de desarrollo
-----------------------

18.0.1.5.1 - Instalación limpia segura
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Evita consultar las líneas de planes históricos antes de que su tabla exista
  durante una instalación inicial del módulo.
- Conserva sin cambios la migración de planes en bases donde la tabla ya está
  creada.

18.0.1.5.0 - Vale de entrega de Maquinado a Ensamblaje
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Registra entregas parciales de partes o productos desde Maquinado.
- Separa la confirmación de salida de la aceptación física en Ensamblaje.
- Conserva cantidades entregadas, aceptadas y rechazadas, responsables, fechas
  y observaciones en un registro auditable vinculado con la OF.
- Exige como documento origen de la OF una factura de venta o identifica la OF
  como fabricación por reposición, conservando además la referencia que generó
  la necesidad de reponer stock.
- Incorpora vistas, acceso desde la OF, secuencia propia y PDF con firmas.

18.0.1.4.0 - Control nativo entre Maquinado y Ensamblaje
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Configura dos centros de trabajo: Maquinado y Ensamblaje.
- Define tres operaciones dependientes: Maquinado, Recepción desde Maquinado y
  Ensamblaje, manteniendo la recepción en el centro físico de Ensamblaje.
- Incorpora un script idempotente que crea una venta demostrativa, factura,
  pago, necesidad, plan, OF y órdenes de trabajo persistentes.
- Documenta referencias y recorrido de revisión del piloto local.

18.0.1.3.8 - Etiqueta monocromática
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Elimina fondos y separadores de color de la etiqueta 2 x 1.
- Usa fondo blanco, texto negro y divisiones grises aptas para impresión
  térmica, sin modificar los colores de los demás reportes del módulo.
- Conserva la distribución aprobada de tres bloques.

18.0.1.3.7 - Etiqueta organizada en tres bloques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Sustituye el título fijo por el nombre del producto en un bloque superior a
  todo el ancho, con capacidad para dos líneas.
- Reserva el bloque inferior izquierdo para OF, origen y destino.
- Reserva el bloque inferior derecho para unidad, barcode y plan, evitando que
  el nombre del producto se corte por el ancho de una sola columna.

18.0.1.3.6 - Aprovechamiento vertical de etiquetas 2 x 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Distribuye encabezado, OF, producto, origen y destino sobre la altura útil de
  la columna izquierda mediante márgenes e interlineado controlados.
- Conserva el tamaño legible del texto, el barcode ampliado, el papel físico y
  una página independiente por cada unidad.

18.0.1.3.5 - Legibilidad física de etiquetas 2 x 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Recupera el tamaño legible del encabezado, OF, datos, unidad y plan después
  de comprobar que la reducción anterior no se leía correctamente en papel.
- Conserva el código de barras ampliado de la versión anterior.
- Se valida primero en local antes de autorizar otro despliegue a pruebas.

18.0.1.3.4 - Segundo ajuste visual de etiquetas 2 x 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Reduce dos puntos adicionales el texto informativo de la etiqueta.
- Aumenta un punto adicional el código de barras para priorizar su lectura.
- Conserva el tamaño físico, la paginación individual y los colores existentes.

18.0.1.3.3 - Equilibrio visual de las etiquetas 2 x 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Reduce dos puntos la tipografía para liberar espacio visual.
- Aumenta dos puntos el código de barras para facilitar su lectura.
- Mantiene sin cambios el papel de 51 x 25 mm, la escala de 96 DPI y una página
  independiente por cada unidad fabricada.

18.0.1.3.2 - Escala real de impresión 2 x 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Ajusta la resolución de maquetación de 203 a 96 DPI para evitar que
  `wkhtmltopdf` reduzca el contenido a la esquina superior izquierda.
- Conserva el papel físico en 51 x 25 mm y distribuye el contenido sobre el área
  imprimible completa de cada etiqueta.

18.0.1.3.1 - Una etiqueta independiente por producto
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Imprime tantas etiquetas como unidades aprobadas tenga cada OF.
- Fuerza una página física de 2 x 1 pulgadas para cada unidad, evitando que dos
  productos compartan la misma etiqueta.
- Identifica cada copia como `Unidad n/total` y compacta el contenido sin perder
  OF, producto, origen, destino, plan ni código de barras.

18.0.1.3.0 - Trazabilidad documental y separación por OF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Vincula explícitamente la factura que origina cada necesidad por venta,
  conservando el documento desde el plan diario hasta la OF.
- Mantiene el requerimiento consolidado para Almacén y añade el desglose de
  partes y piezas correspondiente a cada OF para preparar kits separados.
- Incorpora etiquetas de 3 x 1 pulgadas con OF, producto, documento origen,
  almacén destinatario, plan y código de barras.
- Añade la lista **Reposiciones diarias** como control operativo de oficina,
  usando la necesidad de producción como registro único y auditable.
- Conserva los colores corporativos y limita los estilos al módulo para no
  modificar la imagen de otros documentos del sistema.

18.0.1.2.1 - Legibilidad y contraste de reportes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Sustituye encabezados negros por gris claro y dorado corporativo.
- Fija explícitamente texto oscuro en cada columna para evitar títulos
  invisibles por las reglas de estilo de wkhtmltopdf.
- Unifica el contraste del plan diario, requerimiento y vale de salida.

18.0.1.2.0 - Corte automático e inmutable a medianoche
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Sustituye la creación inmediata de OF desde el pago por necesidades de
  producción con fecha y hora de elegibilidad.
- Genera un corte diario cerrado usando la zona horaria `America/Havana` y una
  tarea idempotente que comprueba el cambio de día cada quince minutos.
- Las solicitudes posteriores a las 12:00 a. m. quedan pendientes para el
  siguiente plan y no pueden incorporarse al plan ya cerrado.
- Protege en servidor almacén, producto, LdM, cantidad solicitada, creación y
  eliminación de líneas; Producción solo puede decidir la cantidad aprobada.
- Registra fecha, hora y usuario técnico del corte y evita planes duplicados por
  fecha, compañía y centro productor.
- Las OF nacen únicamente al aprobar el plan cerrado.
- Rediseña los PDF con formato corporativo y destinatarios explícitos; agrega un
  vale propio de salida desde Almacén hacia Fábrica, con solicitante, ubicaciones,
  código de barras y firmas de entrega y recepción.

18.0.1.1.2 - Historial técnico acumulativo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Normaliza el historial del manifest para que cada versión documente objetivo,
  alcance funcional, modelos, documentos y validaciones realizadas.
- Establece este formato como guía de continuidad para el desarrollo del módulo.

18.0.1.1.1 - Recorrido de prueba operativa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Agrega `docs/RECORRIDO_PRUEBA_PLANIFICACION_DIARIA.md`.
- Documenta el recorrido desde necesidades por almacén hasta el pedido interno
  de materiales, incluidos resultados numéricos esperados y punto de detención.
- Incluye criterios de factibilidad, eficiencia, control de duplicados e
  inventario sin consumo anticipado.

18.0.1.1.0 - Planificación diaria y solicitud de materiales
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Crea `ddfc.production.need` para registrar necesidades de fabricación por
  almacén, producto, fecha, prioridad y origen.
- Crea `ddfc.daily.plan` y sus líneas para consolidar solicitudes y permitir que
  Producción decida las cantidades aprobadas del día.
- Crea líneas de componentes calculadas mediante explosión nativa de LdM,
  incluyendo LdM fantasma o anidadas.
- Añade el campo calculado `Almacén solicitante` a las OF.
- Al aprobar el plan genera OF confirmadas e idempotentes por almacén y producto.
- Al solicitar materiales genera una única transferencia interna confirmada,
  sin validarla ni descontar existencias automáticamente.
- Añade **Fabricación → Reportes DoorAndDoor**, con necesidades por almacén y
  planes generales diarios.
- Incorpora PDF del plan por almacén con consolidado global y PDF del
  requerimiento de partes y piezas con disponibilidad y faltantes.
- Validación local: tres necesidades, tres OF, nueve componentes consolidados,
  dos PDF válidos y ausencia de cambios de inventario antes de la validación.

18.0.1.0.1 - Capacitación y datos repetibles de prueba
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Añade la guía de usuario del flujo de fabricación por venta y reposición.
- Incluye scripts idempotentes para crear seis puertas demostrativas, sus LdM y
  componentes identificados mediante códigos `DDFC-*`.
- Incluye comprobaciones reversibles de OF, rutas MTO/Manufactura y movimientos
  de componentes, además de OF persistentes para demostraciones visuales.

18.0.1.0.0 - Fundación y diseño funcional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Crea la estructura instalable inicial de `doorandoor_fabrica_control`.
- Documenta la fabricación para cliente y la reposición del stock vendido por
  cada almacén desde el centro productor.
- Describe solicitud y entrega de materiales, Maquinado, Ensamblaje, control de
  calidad, devolución al almacén, documentos imprimibles y trazabilidad.
- Audita los lanzadores existentes de ventas, pagos, inventario y fabricación
  antes de modificar automatizaciones productivas.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "stock",
        "sale_management",
        "account",
        "doorandoor_control_cobros",
        "doorandoor_produccion_almacen",
        "doorandoor_process_control",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "data/planning_cron.xml",
        "views/machining_handoff_views.xml",
        "views/mrp_production_views.xml",
        "views/production_planning_views.xml",
        "report/production_planning_reports.xml",
        "report/machining_handoff_report.xml",
    ],
    "installable": True,
    "application": False,
}
