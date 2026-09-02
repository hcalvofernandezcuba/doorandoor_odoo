# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Process Control",
    "version": "18.0.2.4.3",
    "category": "Operations",
    "summary": "18.0.2.4.3 - Avisos por almacén, administradores globales y refresco en Odoo 18",
    "description": """
DoorAndDoor Process Control
===========================

Objetivo
--------

Este modulo crea una primera capa operativa para controlar procesos de
ventas, facturacion, manufactura, inventario y entrega desde una vista
unificada.

Compatibilidad
--------------

- Odoo Community Edition 18
- No se asumen componentes Enterprise

Alcance inicial
---------------

- modelo central de procesos
- modelo de tareas operativas
- estados base del flujo
- timestamps por cambio de estado
- vistas list, form y kanban
- accesos rapidos a venta, factura, MO y picking
- integracion inicial con labels de factura y manufactura
- configuracion simple de colores por compania

Historial resumido
------------------

- 18.0.2.4.3
  Envía los avisos a los operadores configurados en el almacén destino y a
  todos los usuarios de Administración/Ajustes. Sustituye el listener legado
  por un servicio compatible con Odoo 18 y registra los destinatarios enviados.

- 18.0.2.4.2
  Implementa actualización automática de vistas usando mensajes record_update
  del bus.bus nativo. Los operarios ven los cambios en tiempo real sin recargar
  la página manualmente. Las notificaciones toast se muestran instantáneamente
  y las vistas de listas/kanban se refrescan automáticamente.

- 18.0.2.4.1
  Corrige las notificaciones instantaneas de inventario usando el canal nativo
  de Odoo 18 y adapta el tablero de traslados a la sintaxis kanban vigente.

- 18.0.2.4.0
  Implementa actualización en tiempo real de recepciones de traslados internos
  entre almacenes. Agrega sistema de notificaciones vía bus.bus, widget JavaScript
  para actualizaciones automáticas, dashboard de recepciones pendientes con
  refresco automático, e indicadores visuales en el formulario de picking. Los
  usuarios del almacén destino reciben notificaciones instantáneas cuando se
  despachan traslados y las vistas se actualizan automáticamente sin recarga manual.

- 18.0.2.3.1
  Corrige el mensaje del chatter al validar un traslado interno: la recepción
  del almacén destino aparece como un enlace legible y navegable, sin mostrar
  etiquetas ni atributos HTML al usuario.

- 18.0.2.3.0
  Convierte los traslados directos entre almacenes en dos etapas controladas.
  Al validar el despacho mueve únicamente la cantidad real a tránsito y crea
  una recepción enlazada para el almacén destino. Las alertas permanecen sobre
  esa recepción hasta su validación física y los parciales conservan backorder.

- 18.0.2.2.0
  Las vistas operativas y gerenciales muestran la prereserva en el almacén
  proveedor elegido por la línea, no únicamente en el almacén comercial.
  Los traslados liberados por pago conservan la trazabilidad nativa y alertas.

- 18.0.2.1.0
  Incorpora una fuente analitica unificada para separar prereservas comerciales
  y reservas fisicas de entregas pagadas, con cantidades, saldos sin reservar,
  valor comprometido, riesgo, cliente, vendedor, producto y almacen.

- 18.0.2.0.4
  Incorpora la fecha real de entrega tomada del picking y una vista grafica
  para analizar cantidades pendientes y entregadas por estado.

- 18.0.2.0.3
  Incorpora el estado Entregado al tablero. Una entrega total permanece como
  historial entregado; una parcial sigue Lista para entregar con su saldo y
  abre el backorder nativo para completar la operacion.

- 18.0.2.0.2
  Agrega la acción Procesar entrega en lista y Kanban para abrir el picking
  nativo ya liberado. No permite crear despachos paralelos y conserva el
  requisito de factura totalmente pagada.

- 18.0.2.0.1
  Amplía la guía de Operaciones de Almacén con el paso a paso de recepciones,
  entregas pagadas, entradas de fábrica y traslados; documenta responsables,
  permisos, alertas, estados automáticos y resultados esperados.

- 18.0.2.0.0
  Incorpora Operaciones > Almacén con accesos simples a recepciones, entregas
  pagadas, entradas de fábrica y traslados usando siempre stock.picking nativo.
  Permite asignar almacenes a cada operador, muestra inicio y destino, y crea
  actividades y notificaciones periódicas para el almacén receptor hasta que
  el traslado se valide o cancele. La frecuencia y el escalamiento son
  configurables por compañía.

- 18.0.1.3.0
  Agrega la cola operativa de entregas pendientes para facturas publicadas,
  totalmente pagadas y con cantidades aún no entregadas. Incluye Kanban por
  almacen, lista y pivote, distinguiendo preparación, producción y entrega.
  Ambos Kanban son informativos, no admiten arrastre ni cambios manuales y se
  recalculan directamente desde los estados oficiales del proceso.

- 18.0.1.2.1
  Agrega una vista Kanban como entrada principal de las prereservas, agrupada
  por almacen y con tarjetas coloreadas por estado y vencimiento.

- 18.0.1.2.0
  Agrega una vista de solo lectura con las lineas prereservadas por prefacturas
  confirmadas, vencimiento, almacen, cliente, producto y vendedor. Los usuarios
  de Inventario acceden desde el menu raiz Operaciones o Inventario/Operaciones.
  Administrador/Ajustes hereda por defecto el rol de gestor de Operaciones y
  puede consultar todas las vistas operativas sin asignaciones adicionales.

- 18.0.1.0.0
  Version inicial del modulo.
  Se incorpora la primera fase de pruebas del control de procesos con
  procesos y tareas manuales, estados operativos, trazabilidad temporal,
  vistas gerenciales y vistas operativas en kanban.

- 18.0.1.0.1
  Corrige la categoria de los grupos de seguridad para usar una referencia valida en esta base Odoo CE 18.
  Esto evita el error de instalacion causado por el xmlid inexistente `base.module_category_operations_management`.

- 18.0.1.0.2
  Mueve el acceso principal del modulo a un menu raiz propio llamado `Operaciones`.
  Esto permite llegar a `Process Flows` y `Process Tasks` desde el menu principal sin depender de Inventario.

- 18.0.1.0.3
  Agrega entradas de `Operaciones` dentro de Ventas, Facturacion, Manufactura e Inventario.
  Cada menu abre tareas y procesos filtrados por area para que cada rol entre desde su modulo natural sin duplicar modelos ni vistas.

- 18.0.1.0.4
  Agrega un wizard de `Cargar historicos` para poblar `Operaciones` con ventas, facturas, MOs y pickings ya existentes.
  La carga es minima, controlada por limite por tipo y opcionalmente crea una tarea inicial de revision para cada proceso importado.

- 18.0.1.0.5
  Corrige el registro del modelo `doorandoor.process.backfill.wizard` importando explicitamente su archivo Python en `models/__init__.py`.
  Esto resuelve el error de actualizacion donde Odoo no encontraba `model_doorandoor_process_backfill_wizard` al cargar permisos.

- 18.0.1.0.6
  Fija el orden logico de estados en las vistas kanban de procesos y tareas.
  Ahora las columnas se muestran en la secuencia `Iniciado -> En proceso -> Entregado -> En ruta -> Cerrado`.

- 18.0.1.0.7
  Ajusta `_group_expand_states` a la firma real usada por esta base Odoo CE 18.
  Esto corrige el error `missing 1 required positional argument: 'order'` al abrir las vistas kanban agrupadas por estado.

- 18.0.1.0.8
  Refuerza la visualizacion de colores en las tarjetas kanban de procesos y tareas.
  El badge de estado ahora renderiza el texto explicitamente y cada tarjeta muestra ademas una barra lateral con el color del semaforo.

- 18.0.1.0.9
  Agrega impresion PDF para `Process Flows` y `Process Tasks` desde las vistas list con seleccion multiple.
  Esto permite llevar una hoja operativa en papel con estado, responsable, documento y tiempo actual del proceso o tarea.

- 18.0.1.0.10
  Colorea los badges de `Estado` y `Semaforo` dentro del PDF de procesos y tareas.
  El reporte impreso conserva ahora la lectura visual por color segun el semaforo calculado de cada registro.

- 18.0.1.0.11
  Simplifica el PDF operativo eliminando la columna `Semaforo`.
  El reporte impreso deja solo la columna `Estado` con color para mantener la lectura visual sin recargar la hoja.

- 18.0.1.0.12
  Agrega filtros por cliente, estado, proceso y responsable en las vistas de procesos y tareas.
  Adapta el PDF de tareas para trabajo manual en papel, eliminando `Ultimo cambio` y `Horas` y agregando columnas vacias de `Iniciado` y `Terminado`.

- 18.0.1.0.13
  Agrega accesos rapidos a `Cotizaciones`, `Prefacturas` y `Facturas` dentro de `Operaciones`, `Ventas` y `Facturacion`.
  Estos accesos no se muestran en `Manufactura`, manteniendo separada la navegacion operativa comercial de la productiva.

- 18.0.1.0.14
  La accion `Prefacturas` ahora abre el formulario con contexto explicito de modo prefactura.
  Esto permite mostrar `Crear factura` solo en ese flujo y conservar `Confirmar` en facturas normales.

- 18.0.1.0.15
  Los grupos funcionales base de Ventas, Facturacion, Manufactura e Inventario ahora heredan automaticamente `DoorAndDoor Process User`.
  Esto permite que usuarios operativos vean `Operaciones` y naveguen sus menus sin asignacion manual adicional del grupo tecnico.

- 18.0.1.0.16
  Se corrige la accion estandar `Prepare Wave` por tipo de picking para que no falle cuando entra sin `active_id` en contexto.
  Esto evita el error `Name 'active_id' is not defined` al abrir ciertos menus o vistas con usuarios operativos.

- 18.0.1.0.17
  Se retira la sobreescritura de `stock_picking_batch.action_prepare_wave_for_picking_type` porque ese modulo no esta instalado en esta base.
  Esto restablece la actualizacion de `doorandoor_process_control` sin depender de un XML ID externo inexistente localmente.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "sale_management",
        "stock",
        "mrp",
        "account",
        "doorandoor_sales_new",
        "doorandoor_stock_labels",
    ],
    "data": [
        "security/process_control_security.xml",
        "security/ir.model.access.csv",
        "data/warehouse_alert_data.xml",
        "views/process_control_views.xml",
        "report/process_control_reports.xml",
        "views/backfill_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/mrp_production_views.xml",
        "views/stock_picking_views.xml",
        "views/warehouse_prereservation_views.xml",
        "views/pending_delivery_views.xml",
        "views/sales_reservation_analysis_views.xml",
        "views/warehouse_operation_views.xml",
        "views/menu_views.xml",
        "views/realtime_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_process_control/static/src/js/record_update_listener.js",
        ],
    },
    "installable": True,
    "application": True,
}
