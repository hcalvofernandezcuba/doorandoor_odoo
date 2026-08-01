# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Process Control",
    "version": "18.0.1.0.17",
    "category": "Operations",
    "summary": "18.0.1.0.17 - Retira override de modulo no instalado",
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
    "author": "Hanoi Calvo Fernandez for Doorandoor",
    "website": "https://gestion.doorandoor.com",
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
        "views/process_control_views.xml",
        "report/process_control_reports.xml",
        "views/backfill_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/mrp_production_views.xml",
        "views/stock_picking_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
}
