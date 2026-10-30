# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Soporte Técnico",
    "version": "18.0.1.9.0",
    "category": "Services/Helpdesk",
    "summary": "18.0.1.9.0 - PDF filtrable y eficiencia de soluciones por técnico",
    "description": """
DoorAndDoor Soporte Técnico
===========================

Base CE propia para organizar incidencias internas. Registra oficina, almacén,
usuario solicitante, área afectada, prioridad, evidencias, responsable técnico
y tiempos de atención sin depender del Helpdesk Enterprise.

Version 18.0.1.2.0
------------------

Separa quién origina la incidencia de quien la recibe y registra, incorpora el
canal de recepción y protege los cambios de estado para administradores,
responsables de soporte y el técnico efectivamente asignado.

Version 18.0.1.3.0
------------------

Al resolver, notifica al originador mediante la mensajería interna de Odoo y
reserva para ese usuario la confirmación final que cambia el ticket a cerrado.

Version 18.0.1.3.1
------------------

Administrador/Ajustes obtiene la bandeja completa y las acciones operativas de
soporte sin requerir una asignación manual adicional al equipo técnico.

Version 18.0.1.3.2
------------------

Permite confirmar el cierre al originador, Administrador/Ajustes o Responsable
de soporte, manteniéndolo bloqueado para técnicos no autorizados.

Version 18.0.1.3.3
------------------

Distingue tickets manuales pendientes de clasificar de los creados desde un
documento de Odoo, evitando atribuir automáticamente un canal incorrecto.

Version 18.0.1.3.4
------------------

Notifica por la mensajería interna de Odoo cada cambio real de estado al
originador y a quien recibió el ticket, indicando estado anterior, estado
nuevo y usuario que ejecutó la transición, incluso cuando soporte realiza el
cambio.

Version 18.0.1.4.0
------------------

Mantiene visibles todas las etapas del tablero aunque estén vacías e incorpora
un reporte diario PDF con la huella de tickets, responsables, áreas, estados y
tiempos de atención para Gerencia.

Version 18.0.1.5.0
------------------

Permite indicar expresamente la acción que debe realizar el usuario para
continuar la solución. Al pasar el ticket a Esperando al usuario, exige la
instrucción y la incluye en la notificación interna de Odoo.

Version 18.0.1.5.1
------------------

Elimina el filtro automático de abiertos en las bandejas. Mis tickets muestra
todos los estados de los tickets originados por el usuario; Todos los tickets
muestra a Soporte y Administrador/Ajustes todos los registros autorizados,
incluidos resueltos, cerrados y cancelados. El filtro Abiertos sigue disponible
como opción manual.

Version 18.0.1.6.0
------------------

Incorpora el botón Confirmar acción realizada para el originador de un ticket
en espera. La confirmación devuelve el caso a En análisis, notifica al técnico
asignado y conserva la instrucción en el historial sin validar automáticamente
la operación funcional relacionada.

Version 18.0.1.7.0
------------------

Incorpora el rol Responsable local de casos y la bandeja Casos de mi sede.
El alcance se calcula por oficina comercial y almacenes operativos asignados,
sin conceder acceso global de soporte, reasignación técnica ni cierre
administrativo de incidencias.

Version 18.0.1.7.1
------------------

Corrige el reporte diario PDF para Odoo 18 al renderizar los campos Área y
Técnico dentro de elementos compatibles con los widgets QWeb de las tablas.

Version 18.0.1.8.0
------------------

Añade un reporte resumido por rango de fechas, una línea por ticket, totales
por estado, resumen de soluciones por técnico y tablero gráfico/pivote para
analizar los casos resueltos y cerrados.

Version 18.0.1.8.1
------------------

Permite definir el análisis impreso por fecha de creación, solución o cierre,
estado, técnicos, solicitantes y área. Los totales, líneas por ticket y resumen
por técnico del PDF respetan exactamente los filtros seleccionados. Añade
filtros directos de fechas al tablero gráfico y pivote.

Version 18.0.1.9.0
------------------

Incorpora fecha de creación, fecha de solución, horas de solución y un nivel
objetivo de eficiencia en listas, PDF, gráfico y pivote. La eficiencia se
clasifica como excelente hasta 4 horas, buena hasta 24, requiere atención hasta
72 y demorada por encima de 72 horas.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "sale_management",
        "account",
        "doorandoor_commercial_office_tax",
        "doorandoor_inventory_variant_count",
    ],
    "data": [
        "security/helpdesk_security.xml",
        "security/ir.model.access.csv",
        "data/helpdesk_sequence.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_daily_report_views.xml",
        "reports/helpdesk_daily_report.xml",
        "views/helpdesk_summary_report_views.xml",
        "reports/helpdesk_summary_report.xml",
        "views/source_document_views.xml",
        "views/helpdesk_menu_views.xml",
    ],
    "installable": True,
    "application": True,
}
