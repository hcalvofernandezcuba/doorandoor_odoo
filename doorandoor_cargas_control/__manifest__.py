# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Control de Cargas",
    "version": "18.0.1.5.1",
    "category": "Inventory/Delivery",
    "summary": "18.0.1.5.1 - Gerencia crea choferes sin error ni cuentas involuntarias",
    "description": """
DoorAndDoor Control de Cargas
=============================

Parche 18.0.1.5.1
------------------

Permite crear un perfil operativo de chofer directamente por su nombre, incluso
si todavía no dispone de usuario de Odoo. El vínculo con una cuenta interna es
opcional y se utiliza solamente cuando el chofer necesita acceso a sus rutas.
Evita que la creación rápida intente guardar texto en el identificador entero
del usuario y elimina el RPC_ERROR observado por Gerencia.

Planifica cargas mixtas para traslados entre almacenes sin perder la relación
con los documentos nativos de inventario. La secuencia de descarga determina
automáticamente el orden inverso de carga física del camión.

Alcance 18.0.1.0.0
------------------

* Plan de carga y ruta con chatter y secuencia propia.
* Vehículo, conductor, responsable, origen y horario previsto.
* Paradas ordenadas por descarga y orden inverso de carga.
* Asociación de múltiples operaciones de almacén por parada.
* Estados iniciales para planificación, carga, tránsito y cierre.
* Perfiles separados de consulta, planificación y gerencia logística.

Alcance 18.0.1.1.0
------------------

* Nuevo rol Chofer limitado a las rutas que tiene asignadas.
* Registro de salida, llegada, inicio/fin de conteo y salida de cada parada.
* Último punto de control y próxima parada visibles sin depender de GPS.
* Tiempo real de tránsito entre almacenes y tiempo de conteo por parada.
* Dirección logística editable basada en la oficina asociada al almacén.

Alcance 18.0.1.2.0
------------------

* Formulario de configuración de almacenes y puntos de entrega.
* Dirección logística, latitud, longitud y estado de verificación.
* Indicaciones operativas para acceso, muelles y recepción de camiones.
* Validación conjunta y de rangos para las coordenadas.

Alcance 18.0.1.3.0
------------------

* Vista Mapa basada en OpenStreetMap y Leaflet.
* Rutas activas, incidencias y última ruta completada diferenciadas por color.
* Marcadores de último punto confirmado y próxima parada.
* Apertura directa del plan de carga desde el mapa.
* Coordenadas provisionales por ciudad hasta registrar las coordenadas exactas.

Alcance 18.0.1.4.0
------------------

* Menú Reportes con planes y operaciones de inventario asociadas.
* Manifiesto general, orden físico de carga y hoja de ruta.
* Actas de entrega, recepción y conteo por cada parada.
* Resumen de incidencias y cierre de ruta.
* Trazabilidad visible entre carga, parada, entrega y traslado nativo.

Alcance 18.0.1.5.0
------------------

* Preparación de despachos a partir de entregas y traslados reales pendientes.
* Agrupación automática por almacén o dirección de cliente sin duplicar movimientos.
* Integración con Flota nativa para camiones, matrículas, odómetro y costos.
* Perfiles de choferes, tripulación por viaje y controles de combustible/recorrido.
* Trazas en chatter del plan y de cada operación de inventario asociada.

Historial de versiones
----------------------

* 18.0.1.0.0: versión inicial del módulo. Crea la estructura funcional y de
  seguridad del plan de carga, sus paradas y la relación con stock.picking.
  La integración con mapas, Hanger, GPS y telemetría queda prevista para
  versiones posteriores y no se activa en esta entrega.
* 18.0.1.1.0: incorpora el rol Chofer y el seguimiento temporal por hitos de
  almacén. La posición operativa corresponde al último punto confirmado; no
  representa geolocalización GPS en tiempo real.
* 18.0.1.2.0: agrega la configuración controlada de direcciones y coordenadas
  logísticas que utilizarán las rutas, entregas y el futuro mapa operativo.
* 18.0.1.3.0: activa el mapa operativo OSM con rutas, estados, puntos de control
  y diferenciación de coordenadas verificadas o provisionales.
* 18.0.1.3.1: evita comparar identificadores temporales NewId al ordenar varias
  paradas todavía no guardadas en el formulario de una carga.
* 18.0.1.4.0: incorpora el paquete PDF operativo y las vistas de reportes sin
  duplicar entregas, traslados ni movimientos de inventario.
* 18.0.1.4.1: usa una cabecera exclusivamente logística en los cinco documentos
  de cargas y elimina el Tax ID heredado de la plantilla fiscal corporativa.
* 18.0.1.4.2: impide iniciar cargas reales sin documentos, permite asociarlos
  durante la preparación y habilita rutas de simulación claramente identificadas.
* 18.0.1.5.0: incorpora preparación de despachos, destinos de clientes, Flota,
  choferes, tripulaciones y controles operativos de cada viaje.
    """,
    "author": "Hanoi",
    "maintainer": "DoorAndDoor",
    "company": "DoorAndDoor",
    "website": "https://www.doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "stock",
        "fleet",
        "doorandoor_process_control",
        "doorandoor_commercial_office_tax",
    ],
    "data": [
        "security/cargas_control_security.xml",
        "security/ir.model.access.csv",
        "data/load_plan_sequence.xml",
        "views/load_plan_views.xml",
        "views/dispatch_preparation_views.xml",
        "views/fleet_control_views.xml",
        "views/warehouse_coordinate_views.xml",
        "views/load_report_views.xml",
        "report/load_documents_report.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_cargas_control/static/src/js/load_route_map.js",
            "doorandoor_cargas_control/static/src/xml/load_route_map.xml",
            "doorandoor_cargas_control/static/src/scss/load_route_map.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
