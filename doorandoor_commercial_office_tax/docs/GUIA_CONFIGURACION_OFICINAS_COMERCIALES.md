# Guía — Oficinas comerciales e impuesto por vendedor

## Objetivo

DoorAndDoor mantiene una sola compañía y una sola cuenta bancaria. Cada vendedor
pertenece a una oficina comercial y la tasa de venta de esa oficina se aplica a
sus cotizaciones y facturas.

## 1. Crear las oficinas

Con perfil **Contabilidad / Administrador**, ir a:

`Facturación → Configuración → Commercial Offices`

Crear una oficina por ciudad. Completar obligatoriamente:

- Nombre de oficina.
- Dirección completa, ciudad, estado, ZIP y país.
- Teléfono de oficina.
- Impuesto de ventas.
- Almacén operativo de la oficina.

El impuesto debe existir previamente en `Facturación → Configuración → Impuestos`
y pertenecer a DoorAndDoor.

## 2. Asociar una oficina a cada vendedor

Ir a:

`Ajustes → Usuarios y compañías → Usuarios → [Vendedor] → Commercial Office`

Seleccionar una oficina de la lista. La pestaña solo es editable por Contabilidad
o Ajustes. El vendedor puede consultar la oficina en sus documentos, pero no
cambiar su configuración.

Al asignar una oficina, el sistema garantiza los permisos mínimos de Ventas y
Facturación. Los permisos de caja se controlan por separado en la caja de esa
misma oficina, distinguiendo operadores y responsables.

## 3. Resultado operativo

Al crear una cotización o factura, Odoo copia la oficina del vendedor. El
impuesto de las líneas se sustituye por el impuesto configurado para esa oficina.
La oficina se conserva en el documento para trazabilidad, incluso si el vendedor
cambia de oficina posteriormente.

El almacén operativo se copia a la cotización y a la venta interna originada
por una factura directa. Ese almacén se utiliza como destino de fabricación y
como origen de la entrega y del Pickup Order.

## Controles

- Clientes exentos continúan sin impuesto conforme al certificado registrado.
- Una oficina inactiva no puede seleccionarse en documentos nuevos.
- Cada impuesto debe pertenecer a la misma compañía DoorAndDoor.
- Cada almacén operativo debe pertenecer a la misma compañía de la oficina.
- Antes de activar una oficina, Contabilidad valida la tasa aprobada para esa
  ciudad.
