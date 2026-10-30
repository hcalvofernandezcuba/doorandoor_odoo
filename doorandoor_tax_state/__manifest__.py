# -*- coding: utf-8 -*-
{
    "name": "DoorAndDoor Tax State",
    "version": "18.0.1.3.15",
    "category": "Accounting",
    "summary": "18.0.1.3.15 - Permite a Ventas crear clientes sin exención fiscal",
    "description": """
DoorAndDoor Tax State
=====================

Objetivo
--------

Este modulo agrega una capa simple y controlada para manejar impuestos de
venta por estado dentro de un entorno multicompañia en Odoo.

La logica sigue el comportamiento estandar de Odoo:
- el documento pertenece a una compania
- la compania define su estado fiscal
- las ventas y facturas usan el impuesto de venta asociado a ese estado

Alcance funcional
-----------------

- Campo de estado fiscal en la compania.
- Regla por compania y estado para enlazar un impuesto de venta.
- Aplicacion automatica del impuesto en lineas de venta.
- Aplicacion automatica del impuesto en lineas de factura de cliente.
- Declaracion simple de clientes exentos desde una pestaña Impuestos.
- Numero oficial obligatorio, eliminación automática del impuesto y referencia
  impresa inmediatamente después del total del PO y de la factura.

La exención exige que el operador conserve y registre el número oficial que la
respalda. La vigencia y alcance legal del certificado continúan siendo
responsabilidad del proceso administrativo del cliente.

Control de versiones
--------------------

- `18.0.1.3.15`
  Permite que Ventas cree clientes normales cuando el formulario envía campos
  ocultos de exención vacíos, manteniendo restringido cualquier cambio fiscal real.

- `18.0.1.3.13`
  Muestra `Impuestos (porcentaje)` en cotizaciones, prefacturas y facturas,
  conservando la ciudad exclusivamente como regla interna de cálculo.

- `18.0.1.3.12`
  Asocia explícitamente la regla fiscal de la ciudad al crear cotizaciones,
  prefacturas y facturas aunque la ciudad del usuario use mayúsculas o
  minúsculas diferentes, conservando la tasa aplicada en toda la cadena.

- `18.0.1.3.6`
  Aplica el impuesto de la nueva ciudad y el cargo técnico de tarjeta como una
  operación atómica. Excluye ese cargo de las reglas fiscales y valida el
  balance final de la factura.

- `18.0.1.3.7`
  Muestra en los selectores de venta y factura una etiqueta comercial breve,
  por ejemplo `Doral — 7 %`, sin exponer la ruta técnica de la regla fiscal.

- `18.0.1.3.8`
  Hace que el buscador del selector de Odoo devuelva la misma etiqueta corta
  de ciudad y porcentaje, no el nombre técnico almacenado de la regla.

- `18.0.1.3.5`
  Recalcula líneas, totales y cargo de tarjeta de una factura borrador cuando
  un administrador cambia la ciudad de venta antes de confirmar.

- `18.0.1.3.4`
  Muestra porcentajes fiscales con decimales significativos: por ejemplo
  `7,5 %` o `6,25 %`, sin ceros de relleno, tanto en formulario como PDF.

- `18.0.1.3.3`
  Unifica formulario y PDF: el texto de impuesto muestra exclusivamente el
  porcentaje aplicado, sin ciudad, condado ni estado.

- `18.0.1.3.0`
  Añade la ciudad de venta al pedido y factura. Se propone desde la ciudad del
  usuario, únicamente los administradores pueden ajustarla antes de confirmar,
  se propaga a la factura y aplica/imprime la regla fiscal de esa ciudad.

- `18.0.1.3.1`
  El bloque de totales de factura identifica el impuesto de ventas con la
  ciudad y el porcentaje de la regla seleccionada, manteniendo el importe
  calculado estándar de Odoo.

- `18.0.1.3.2`
  Conserva la ciudad como regla interna de cálculo, pero muestra al cliente
  únicamente el porcentaje de impuesto aplicado en pantalla e impresión.

- `18.0.1.2.2`
  Imprime el impuesto de ventas con jurisdicción y porcentaje cuando existe una
  regla fiscal por ciudad/condado. Para documentos históricos sin regla, muestra
  el porcentaje real del impuesto aplicado sin inventar una jurisdicción.

- `18.0.1.2.0`
  Permite a Ventas consultar la exención y su certificado, pero reserva la
  edición a Contabilidad y administradores. Exige un PDF oficial, registra su
  nombre, fecha y usuario de carga, y protege la regla también en el servidor.
  Contabilidad conserva la edición normal de los demás datos del contacto.

- `18.0.1.1.1`
  Coloca la pestaña Impuestos en la segunda posición del formulario de Contactos
  para facilitar a los operadores la gestión de exenciones fiscales.

- `18.0.1.1.0`
  Agrega la pestaña Impuestos en Contactos con casilla de exención y número de
  registro obligatorio. Las ventas y facturas del cliente exento quedan sin
  impuestos; PO y factura imprimen la referencia fiscal debajo del total con
  tipografía diferenciada.

- `18.0.1.0.0`
  Version inicial del modulo con mapeo de impuesto de venta por estado y compania.

- `18.0.1.0.1`
  Se alinea la herencia del reporte de factura para conservar el bloque consolidado `Total de impuestos` definido por DoorAndDoor.

- `18.0.1.0.2`
  Los vendedores normales reciben permiso de solo lectura sobre reglas y tasas de impuesto por estado.
  Esto permite crear cotizaciones y ventas sin requerir perfil de `Contabilidad/Administrador`, manteniendo la edicion de esas reglas solo en contabilidad.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "depends": [
        "account",
        "sale_management",
        "doorandoor_sales_new",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/doorandoor_tax_state_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
