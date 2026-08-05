# Guía funcional del módulo Doorandoor Ficha de Cliente

## Propósito del módulo

Este módulo amplía la ficha de cliente de Doorandoor para registrar la relación entre un cliente y un constructor o instalador asociado. Su objetivo es dejar trazabilidad comercial y operar con reglas diferenciadas en ventas y facturación.

## Estado real del módulo según el código implementado

La lógica que está realmente implementada en el módulo es la siguiente:

- Se crea un catálogo propio de constructores o instaladores.
- Cada cliente puede quedar vinculado a un constructor desde su ficha.
- La relación se propaga automáticamente a las cotizaciones y pedidos de venta.
- La relación también se propaga a las facturas.
- Si el constructor tiene descuento activo, se aplica el porcentaje definido sobre las líneas de la cotización/pedido.
- Se deja un indicador de origen del precio para saber si la venta está usando el precio base o el precio del constructor.
- Se preparó una base de tablero con métricas por constructor, clientes, ventas y facturas.

## Funcionalidades ya presentes en el código

### 1. Catálogo de constructores

Se añadió un modelo nuevo llamado ddfc.builder.profile con campos como:

- nombre del constructor o instalador,
- código,
- contacto principal,
- teléfono,
- móvil,
- correo,
- ciudad,
- estado,
- país,
- notas internas,
- descuento activo,
- porcentaje de descuento especial.

También se incorporaron contadores de clientes, ventas y facturas, así como fechas de última venta y última factura.

### 2. Asociación cliente-constructor

En el modelo res.partner se añadió el campo ddfc_builder_id para vincular el cliente con un constructor. Esta relación queda visible desde la ficha del contacto.

### 3. Propagación a cotizaciones y pedidos

En sale.order se añadió el campo ddfc_builder_id y otros campos relacionados, de forma que la información del constructor está disponible en la cotización o pedido.

### 4. Aplicación de descuento especial

Cuando el constructor está asignado y su descuento está activo, el módulo aplica el porcentaje definido sobre las líneas del pedido o cotización. En el código, eso se controla desde el método _apply_builder_discount.

Los estados posibles del precio que se registran en el módulo son:

- base: cuando no hay constructor asociado o el descuento no está activo.
- constructor: cuando el constructor está asociado y el descuento activo aplica.

### 5. Trazabilidad en facturas

En account.move se añadió el mismo vínculo del constructor para dejar la trazabilidad también en las facturas.

### 6. Tablero de constructores

Existe un modelo de tablero llamado ddfc.dashboard con métricas básicas por constructor, clientes, ventas y facturas. Además, se añadió un menú llamado Tablero de constructores. Sin embargo, la parte de acción de ventana y vista visual completa todavía debe quedar completamente conectada si se quiere abrirlo como un tablero funcional desde la interfaz.

## Reglas de negocio que el código refleja hoy

Actualmente el módulo hace lo siguiente:

- Si un cliente tiene constructor asociado, ese constructor se replica en la cotización/pedido.
- Si el constructor tiene descuento activo, el módulo aplica el porcentaje configurado sobre las líneas de venta.
- Si no hay constructor o el descuento está inactivo, el sistema deja el precio base.
- La relación del constructor se conserva también en facturas.

## Flujo operativo recomendado para validar el comportamiento

### 1. Crear un constructor

Ir a Constructores y crear un registro con:

- nombre,
- código,
- contacto principal,
- descuento activo,
- porcentaje de descuento especial.

### 2. Asociar el constructor al cliente

Abrir la ficha del cliente y asignar el constructor en el campo Constructor asociado dentro de la pestaña Ficha comercial.

### 3. Crear una cotización o pedido

Crear una venta para ese cliente y revisar que:

- el campo Constructor asociado aparece en la cotización,
- el valor de Fuente de precio se actualiza,
- y el descuento se aplique cuando el constructor tenga descuento activo.

### 4. Revisar la lógica del precio

Validar lo siguiente:

- Si el constructor está asociado y el descuento está activo, la línea debe quedar con el porcentaje definido y la fuente de precio debe aparecer como constructor.
- Si el constructor no está asociado o el descuento está inactivo, la fuente de precio debe quedar en base y las líneas deben volver a precio base.

### 5. Confirmar que la factura conserva la trazabilidad

Crear la factura a partir de la venta y comprobar que el constructor queda visible en el documento de factura.

### 6. Revisar la trazabilidad del registro

Abrir el registro del constructor y comprobar que aparecen los contadores de:

- clientes asociados,
- ventas,
- facturas,
- y las fechas de última venta y última factura.

## Cómo comprobar que se cumple lo solicitado por el cliente

Para revisar si el módulo está cumpliendo lo que se pidió, se recomienda verificar estos puntos uno por uno en Odoo:

1. Crear un constructor válido y guardarlo.
2. Asociarlo a un cliente desde la ficha del cliente.
3. Crear una cotización para ese cliente.
4. Confirmar que en la cotización aparece el constructor y que la fuente de precio cambia según la lógica.
5. Confirmar que el descuento especial se aplica solo cuando el constructor tiene descuento activo.
6. Confirmar que al generar la factura, el constructor sigue visible en la factura.
7. Revisar el registro del constructor para ver si se cuentan los clientes, ventas y facturas asociadas.
8. Revisar el menú de Constructores para verificar que las vistas y los reportes básicos están accesibles.

## Limitaciones reales del módulo en su estado actual

Aunque el módulo ya implementa la relación cliente-constructor, la propagación a ventas y facturas, y el descuento especial, todavía hay puntos que deben considerarse como pendientes o limitaciones:

- no existe una validación automática de duplicidad o elegibilidad del constructor,
- no hay una regla de negocio compleja adicional más allá de la propagación y el descuento,
- el tablero de constructores está parcialmente preparado, pero no está completamente operativo como vista de gestión si no se termina la acción de ventana y la vista correspondiente.

## Resumen para capacitación

El usuario del módulo debe saber que esta solución permite:

- registrar constructores o instaladores,
- vincularlos a clientes,
- ver esa relación en cotizaciones y facturas,
- y aplicar un descuento especial cuando el constructor lo requiera.

## Nota final

Este documento refleja la lógica que ya está implementada en el código del módulo y no la intención futura de una versión más amplia. Si en el futuro se agregan nuevas reglas de negocio, se debe actualizar esta guía para mantenerla alineada con lo que realmente existe en Odoo.
