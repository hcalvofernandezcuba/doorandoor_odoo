# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Sales New",
    "version": "18.0.1.0.62",
    "category": "Sales",
    "summary": "Invoice-driven sales, payment release, delivery and production orchestration",
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

Autor
-----

Hanoi Calvo Fernández (doorandoor)
    """,
    "author": "Hanoi Calvo Fernández (doorandoor)",
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
        "data/pickup_order_sequence.xml",
        "data/quote_reservation_cron.xml",
        "security/ir.model.access.csv",
        "views/fulfillment_line_views.xml",
        "views/payment_release_log_views.xml",
        "views/pickup_order_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/res_partner_views.xml",
        "views/res_partner_category_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
        "views/report_signature_templates.xml",
        "views/pickup_order_report.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
