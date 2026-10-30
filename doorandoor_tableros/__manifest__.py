# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Tableros",
    "version": "18.0.1.6.0",
    "category": "Reporting",
    "summary": "18.0.1.6.0 - Agrega tablero financiero Stripe de solo lectura",
    "description": """
DoorAndDoor Tableros
====================

Objetivo
--------

Centralizar en un modulo propio los tableros operativos y ejecutivos de
DoorAndDoor, empezando por el tablero de pagos alimentado desde
`Control de Cobros`.

Alcance inicial
---------------

- tablero base de pagos
- filtros manuales por rango de fecha
- selector del tipo de fecha a analizar
- indicadores operativos de cantidad y monto
- referencia visible a clientes y diarios con mayor actividad
- accesos directos a controles, pagos y reporte analitico

Historial resumido
------------------

- 18.0.1.6.0
  Agrega Stripe en Tableros/Finanzas con cobros, estados, clientes,
  devoluciones, bruto, comisiones, neto, liquidaciones y diferencias usando
  exclusivamente datos ya sincronizados en Odoo.

- 18.0.1.5.0
  Agrega Reportes/Ventas exentas de impuestos con facturas fiscales pagadas,
  PO, registro oficial, base, impuestos, total, pago validado, estados, fecha,
  vistas lista/pivote/gráfico y salida PDF consolidada con totales.

- 18.0.1.4.0
  Agrega el tablero nativo Ventas e Impuestos con todas las facturas de cliente
  contabilizadas y pagadas, tanto del nuevo flujo PO como de los flujos
  historicos. Resume ventas, base sin impuestos, impuestos, exentas, clientes y
  vendedores con filtros por periodo, cliente y vendedor.

- 18.0.1.3.0
  Agrega Reservas y Prereservas en Tableros/Ventas con analisis de ocupacion,
  cantidades sin reservar, valor comprometido, riesgo de vencimiento,
  almacenes, productos, clientes y vendedores.

- 18.0.1.2.0
  Incorpora Entregas en la seccion Ventas de los tableros nativos. Presenta
  estados, pendientes y entregados por almacen, productos, clientes y la
  evolucion temporal, usando directamente el control operativo oficial.

- 18.0.1.0.0
  Se crea el modulo `doorandoor_tableros` como base instalable para los
  tableros de DoorAndDoor. La primera entrega incorpora un tablero de
  pagos con filtros manuales `Desde/Hasta`, selector del tipo de fecha y
  KPIs alimentados desde `doorandoor_control_cobros`.

- 18.0.1.0.1
  El tablero base de pagos se amplia para concentrar informacion mas
  completa de cobros y pagos: facturas vinculadas, pagos enlazados,
  controles parciales, montos pendientes, montos enlazados y tiempo
  promedio de validacion. Con esto `doorandoor_tableros` queda listo
  como base real para evolucion futura de KPIs y tableros ejecutivos.

- 18.0.1.0.2
  El tablero de pagos deja de ser solo un bloque de KPIs y pasa a
  mostrar tambien el detalle base dentro del propio formulario. Ahora
  incluye pestañas con controles, pagos y facturas filtrados por el
  mismo rango manual de fechas para que el usuario vea informacion real
  del flujo sin salir del tablero.

- 18.0.1.0.3
  El acceso al tablero de pagos se integra tambien en el arbol principal
  contable bajo `Finanzas / Facturacion / Pagos`. Asi el usuario puede
  encontrar el tablero dentro del recorrido funcional esperado sin
  depender del menu independiente `Tableros`.

- 18.0.1.0.4
  El tablero de pagos refuerza el filtro temporal con un selector de
  `Periodo` y mantiene el rango manual `Desde/Hasta` cuando el usuario
  necesita escoger fechas exactas. Se agregan opciones rapidas como
  `Hoy`, `Esta semana`, `Este mes` y `Mes anterior`.

- 18.0.1.0.5
  Se fuerza la apertura directa de la vista formulario del tablero base
  de pagos y se diferencia visualmente del menu normal de pagos. El
  menu raiz `Tableros` ahora abre el tablero, y en `Finanzas /
  Facturacion / Pagos` la entrada queda como `Tablero base de pagos`
  para evitar confusiones con la lista contable estandar.

- 18.0.1.0.6
  Se integra `Pagos` como `spreadsheet.dashboard` nativo dentro de la
  familia visual `Finanzas` de `Tableros`, al mismo nivel que
  `Facturacion`. El dashboard base ya incorpora filtros superiores de
  periodo, cliente, diario y vendedor en la interfaz nativa de Odoo.

- 18.0.1.0.7
  El dashboard nativo de `Pagos` deja de ser una maqueta textual y pasa
  a mostrar graficos reales sobre `Control de Cobros`: monto por fecha,
  monto por estado, distribucion por diario y top clientes por monto
  reportado. El filtro superior de fecha se mueve a rango manual real
  `desde / hasta`.

- 18.0.1.0.8
  El dashboard nativo de `Pagos` se ancla a la misma base analitica que
  ya usa `doorandoor_control_cobros` en sus vistas pivot y graph.
  Se agregan graficos por `journal_id`, `state`, `payment_state` y
  `matching_status` para reutilizar las agrupaciones reales del modulo y
  cerrar la primera entrega visual de cobros y pagos.

- 18.0.1.0.9
  Se corrige la compatibilidad tecnica del JSON usado por el dashboard
  nativo de `Pagos` dentro de `Tableros` y se ajusta el lienzo para que
  los graficos carguen con suficiente espacio vertical. Esta version
  estabiliza la primera entrega grafica basada en los reportes y pivots
  de `doorandoor_control_cobros`.

- 18.0.1.0.10
  Se reemplazan los graficos circulares del dashboard nativo de `Pagos`
  por variantes de barras para mejorar la lectura operativa de cobros
  por diario y mantener una visual mas uniforme con el resto del
  tablero.

- 18.0.1.1.0
  Se integra un nuevo dashboard nativo de `Constructores` dentro de
  `Ventas` para explotar la relacion entre clientes, constructores
  asociados y ventas reales. El tablero muestra barras de clientes por
  constructor, ventas por constructor, monto vendido por fecha y
  vendedores con mayor monto asociado a constructores.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "account",
        "spreadsheet_dashboard",
        "doorandoor_control_cobros",
        "sale",
        "doorandoor_ficha_cliente",
        "doorandoor_process_control",
        "doorandoor_tax_state",
        "doorandoor_stripe_reconciliation",
        "doorandoor_stripe_refund",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/dashboards.xml",
        "data/cleanup_legacy_menus.xml",
        "views/payment_dashboard_views.xml",
        "views/tax_exempt_sales_report_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
}
