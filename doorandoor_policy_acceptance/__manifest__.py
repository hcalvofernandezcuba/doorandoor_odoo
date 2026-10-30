# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Policy Acceptance",
    "version": "18.0.1.4.0",
    "category": "Sales",
    "summary": "18.0.1.4.0 - Bloquea envío e impresión comercial hasta la firma de políticas",
    "description": """
DoorAndDoor Policy Acceptance
=============================

Publica el PDF oficial de políticas comerciales en el website y conserva su
huella SHA-256. Permite solicitar la aceptación por correo o abrirla en una
pantalla para atención presencial. Registra firmante, cliente, fecha, IP,
navegador, origen, documento comercial y vigencia anual.

La confirmación de cotizaciones y prefacturas, y la contabilización de facturas
de cliente, quedan bloqueadas mientras el cliente no tenga una aceptación
vigente de la versión activa.

18.0.1.4.0
------------
Mantiene libre el envío de las políticas y bloquea en servidor el envío de
cotizaciones, facturas y demás documentos comerciales mientras el cliente no
haya firmado. Protege también las rutas directas de PDF y vista HTML de
cotizaciones y facturas. Conserva para Administrador/Ajustes la excepción de
impresión previamente aprobada, sin permitirle omitir la firma para enviar,
confirmar, facturar o continuar el flujo comercial.

18.0.1.3.4
------------
Retira de las vistas el campo técnico invisible de la aceptación vinculada.
El vínculo y la trazabilidad permanecen en el modelo, pero Odoo 18 deja de
serializar innecesariamente el Many2one y evita el KeyError al abrir borradores.

18.0.1.1.0
------------
Al seleccionar y guardar el cliente en una cotización, verifica su aceptación.
Si está pendiente y existe email, envía una sola invitación automáticamente. Si
falta el email, identifica el bloqueo y abre el acceso directo a la ficha del
cliente para completar sus datos. Cuando el cliente realmente no utiliza email,
el comercial puede abrir el mismo formulario público en otra pestaña y entregarle
la pantalla para que acepte personalmente.

18.0.1.2.0
------------
Muestra en la pantalla del cliente una alerta únicamente mientras las políticas
estén pendientes, con acceso al formulario público. Añade un modo de simulación
exclusivo de Local: sustituye el correo real por un aviso de repo_update_bot con
el URL local para probar la aceptación desde una ventana privada.

18.0.1.2.1
------------
Refuerza la inmutabilidad de la evidencia para usuarios comerciales y normaliza
la herencia de la pantalla pública para evitar advertencias de compilación.

18.0.1.2.2
------------
Dispara la solicitud idempotente al escoger el cliente, aun antes de guardar la
cotización. Reutiliza una solicitud pendiente del mismo cliente y versión para
evitar emails o mensajes Telegram duplicados.

18.0.1.2.3
------------
Publica directamente la ruta oficial `/terminos-y-condiciones` sin depender del
módulo opcional de registro web. Permite instalar el flujo legal de forma
selectiva en Gestión conservando website, ventas y pantalla de cliente.

18.0.1.2.4
------------
Bloquea en servidor el paso Siguiente desde la cotización y todas las rutas de
creación de prefactura o factura mientras el cliente no tenga una aceptación
vigente de la versión activa de las políticas.

18.0.1.3.0
------------
Publica la política inglesa como predeterminada y conserva un selector visible
English/Español. Registra el idioma y la huella exacta del PDF aceptado.

18.0.1.3.1
------------
Añade un acceso legal bilingüe permanente en el pie global del website para
consultar las políticas desde Inicio, Catálogo, Tienda y las demás páginas.

18.0.1.3.2
------------
Publica en Ventas una tabla auditable de clientes con políticas firmadas,
vigencia, firmante, idioma, origen y documento comercial relacionado.

18.0.1.3.3
------------
Corrige en cotizaciones y facturas la dirección pública de políticas para usar
`https://www.doorandoor.com/terminos-y-condiciones`.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "website",
        "mail",
        "sale_management",
        "account",
        "doorandoor_sales_new",
        "doorandoor_pantalla_cliente",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/policy_document.xml",
        "data/mail_template.xml",
        "views/policy_templates.xml",
        "views/customer_display_templates.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
        "views/policy_acceptance_views.xml",
        "views/report_templates.xml",
    ],
    "installable": True,
    "application": False,
    "assets": {
        "web.assets_frontend": [],
    },
}
