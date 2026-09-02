# Trazabilidad de origen, materiales por OF y etiquetas

## Objetivo

El plan diario conserva dos niveles simultáneos de información:

1. Un consolidado de partes y piezas para que Almacén prepare la salida total.
2. Un desglose por orden de fabricación para que Fábrica reciba cada kit
   identificado y pueda seguirlo durante todo el proceso.

## Producción originada por venta

Cuando una factura pagada libera una fabricación, la necesidad registra la
factura como documento origen. Ese vínculo aparece en la necesidad, el plan
diario, la OF, el requerimiento de materiales y la etiqueta del kit.

## Producción por reposición

Las solicitudes cuyo origen es `Reposición` se consultan en **Fabricación →
Reportes DoorAndDoor → Reposiciones diarias**. La lista permite controlar fecha,
almacén solicitante, producto, cantidad, documento origen y estado sin crear un
segundo registro que pueda contradecir la planificación.

Cuando la reposición proviene de una transferencia, esta se registra como
`Transferencia origen`. Si se crea manualmente, la referencia escrita de origen
identifica la decisión o documento de oficina que la autorizó.

## Preparación de materiales

Al aprobar el plan, Odoo explota cada LdM por separado. Guarda el detalle de
componentes de cada OF y, en paralelo, suma esas cantidades en el consolidado.
La transferencia interna continúa usando los totales y no descuenta inventario
hasta que Almacén valide físicamente la entrega.

## Etiqueta 2 × 1 pulgadas

Desde un plan aprobado se utiliza **Etiquetas OF 2×1**. Se imprime una etiqueta
independiente por cada unidad aprobada de la OF con:

- número y código de barras de la OF;
- producto a fabricar;
- factura, reposición o referencia manual de origen;
- almacén al que se destina el producto terminado;
- número del plan diario.
- posición de la unidad dentro de la OF (`Unidad 1/3`, `Unidad 2/3`, etc.).

Cada página del PDF corresponde exactamente a una etiqueta física. Por ejemplo,
una OF de tres puertas genera tres páginas 2 × 1, todas relacionadas con la misma
OF y diferenciadas mediante su número de unidad.

El formato usa 96 DPI para la maquetación PDF. La resolución propia de la
impresora térmica se configura en su controlador; no debe trasladarse al campo
DPI de Odoo porque reduciría el contenido dentro del papel.
