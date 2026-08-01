# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Control de Cobros",
    "version": "18.0.1.0.8",
    "category": "Accounting",
    "summary": "18.0.1.0.8 - Agrega reporte de pagos con estados actuales",
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
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
}
