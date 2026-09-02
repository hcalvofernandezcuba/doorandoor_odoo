# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Sales New Docs Website",
    "version": "18.0.1.5.2",
    "category": "Website",
    "summary": "18.0.1.5.2 - Documentación móvil sin dependencia operativa obligatoria",
    "description": """
DoorAndDoor Sales New Docs Website
==================================

Este modulo publica en el website la documentacion Markdown operativa de los
modulos DoorAndDoor leyendo directamente sus archivos del directorio `docs`.

Objetivo:
- mantener la documentacion en el mismo repositorio
- editarla desde el IDE habitual del proyecto
- mostrarla en el website sin duplicar contenido

Incluye las guias informativas usadas para capacitacion de usuarios
despues de cada mejora operativa importante del modulo principal,
incluyendo reglas de reserva temporal, stock visible y documentos operativos.
Publica las guias integrales de pruebas del proyecto y de configuracion de
productos normales, variantes, Transformados, Especiales y plantillas maestras.
La guia de pruebas consolida la secuencia vigente de producto, venta, pago,
fabricacion, credito, documentos, inventario y despacho.

18.0.1.5.2
------------
Permite publicar las guías Markdown de Mobile Hanger desde su carpeta `docs/`
sin exigir que el módulo operativo esté instalado. El website solo lee archivos
del código y no necesita cargar los modelos ni grupos de seguridad del módulo
documentado.

18.0.1.5.1
------------
Mantiene el índice compatible con el controlador anterior durante el intervalo
entre la actualización del módulo y el reinicio coordinado del servicio en
pruebas. El nombre del módulo fuente se muestra solo cuando el controlador ya
entrega ese dato, evitando un error HTTP 500 durante la transición.

18.0.1.5.0
------------
Establece como regla permanente la publicación automática de todos los archivos
Markdown ubicados directamente en la carpeta lowercase `docs/` de cada módulo
`doorandoor_*`. El índice identifica el módulo fuente, conserva primero las
guías operativas diarias y deja de requerir cambios Python para agregar nuevos
manuales. La portada advierte que el contenido de `docs/` es público.

18.0.1.4.0
------------
Publica como documentos principales dos manuales de operación diaria: Inventario
incluye recepción con hanger, traslados, entradas de fábrica, entregas, conteo
móvil auditable y labels por variantes; Fabricación incluye corte y plan diario,
materiales por OF, operaciones encadenadas, vale auditable de Maquinado a
Ensamblaje, etiquetas unitarias y cierre de turno. Actualiza la portada para
presentar documentación de varios módulos y amplía la resolución de enlaces
Markdown entre sus guías.

18.0.1.3.1
------------
Publica la guia de usuario para validar la fabricacion por venta y reposicion,
con el recorrido de demostracion y las decisiones pendientes del cliente.

18.0.1.3.0
------------
Publica tres guias operativas independientes para la capacitacion: cobros y
pagos controlados, ciclo integral de inventarios y conteo fisico mediante
hanger o movil. Las guias quedan visibles en el indice del website y describen
roles, pasos, resultados esperados y controles de cada operacion.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": [
        "website",
        "doorandoor_sales_new",
        "doorandoor_fabrica_control",
        "doorandoor_inventory_variant_count",
    ],
    "data": [
        "data/website_menu.xml",
        "views/docs_templates.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
