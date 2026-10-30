# Guía de configuración y uso — Carga inicial de inventario

## 1. Propósito

Este módulo prepara el inventario físico inicial de DoorAndDoor por ubicación,
producto e ITEM/variante. Es válido para cualquier almacén interno. Está
diseñado inicialmente para los formatos PDF de Tampa:

- **Tampa Warehouse PDF**: listado compacto de modelo, ancho, alto,
  configuración y cantidad.
- **Tampa Store PDF**: listado con producto, ancho, alto, configuración,
  color, cristal y cantidad.

El archivo se analiza primero. Ninguna cantidad se modifica al cargarlo ni al
analizarlo. El ajuste de inventario será un paso posterior, bloqueado hasta
que cada fila tenga un ITEM validado.

## 2. Requisitos antes de comenzar

1. Tener rol **Administrador de Inventario**.
2. Tener creadas las ubicaciones internas correctas para Tampa Warehouse y
   Tampa Store. No use una ubicación de proveedor, cliente, tránsito o ajuste.
3. Tener disponibles los productos, atributos y variantes que se desean
   reconocer. El módulo no crea productos ni variantes automáticamente.
4. Contar con el PDF original emitido durante el conteo. Conserve el archivo
   sin editar como evidencia de la carga inicial.
5. Confirmar con almacén el significado de abreviaturas locales, por ejemplo
   `RH`, `LH`, `SLAB`, `BIFOLD`, `CWI`, `GWI`, `GRAY` y `CLEAR`.
6. El servidor Odoo debe incluir `poppler-utils` (`pdftotext`). La imagen
   DoorAndDoor lo incorpora para conservar las columnas de PDF exportados por
   Excel; sin ello, un PDF visualmente correcto puede perder su estructura al
   ser leído.

## 3. Permisos

El menú y los lotes de importación son visibles solo para el grupo
**Administrador de Inventario**. Esta restricción evita que una carga inicial
sea iniciada por ventas o por usuarios de operación sin autorización.

## 4. Abrir el asistente

1. Abra **Inventario**.
2. Vaya a **Configuración > Initial Inventory > Import inventory file**.
3. Complete los campos:

| Campo | Uso |
|---|---|
| Formato fuente | Seleccione Tampa Warehouse PDF o Tampa Store PDF. |
| Ubicación | Ubicación interna donde quedará el conteo. Warehouse y Store siempre se cargan por separado. |
| Fecha de inventario | Fecha física del conteo. |
| Archivo | PDF original que se analizará. |

4. Pulse **Analyze PDF**.

El asistente crea un lote de importación y adjunta el PDF a ese lote. Esto
permite conocer posteriormente quién lo cargó, cuándo y desde qué fuente.

## 5. Cómo lee cada formato

### Tampa Warehouse

Ejemplo de fuente:

```text
1 LITE   24   80 SLAB     238
```

El lector obtiene:

| Dato | Valor |
|---|---|
| Modelo | 1 LITE |
| Ancho | 24 |
| Alto | 80 |
| Configuración | SLAB |
| Cantidad | 238 |

### Tampa Store

Ejemplo de fuente:

```text
FD   37.5   81   LH   BRONZE   CWI   6
```

El lector obtiene modelo, ancho, alto, configuración, color, cristal y
cantidad. Las medidas decimales se conservan como texto de origen para no
alterar su precisión durante la validación.

## 6. Estados de las líneas

Después del análisis, abra la pestaña **Prepared lines**. Cada fila conserva
su número de línea y texto original para poder contrastarla con el PDF.

| Estado | Significado | Acción requerida |
|---|---|---|
| Matched | Se encontró un único ITEM de Odoo compatible con la combinación. | Revisar una muestra y continuar. |
| Pending | Falta cantidad, falta un dato o no hay un ITEM compatible. | Corregir la variante o definir su equivalencia. |
| Ambiguous | Más de un ITEM coincide con la misma combinación. | Definir una regla o corregir los atributos para que exista una sola variante. |

Una cantidad vacía se marca como **Pending**. Nunca se interpreta como cero;
esa decisión debe venir de almacén y quedar explícitamente documentada.

## 7. Criterio de coincidencia de ITEMs

El módulo normaliza mayúsculas, espacios y guiones, y compara los datos de la
fuente contra los atributos, referencia interna y nombre de los ITEMs activos
en Odoo. Una coincidencia solo se acepta si resulta un único ITEM.

Ejemplos de equivalencias que deben estar configuradas de manera consistente:

| Archivo | Atributo Odoo esperado |
|---|---|
| `24`, `37.5` | Ancho |
| `80`, `81`, `96` | Alto |
| `RH`, `LH`, `SLAB`, `BIFOLD` | Tipo, Swing o Configuración |
| `WHITE`, `BRONZE` | Color |
| `CWI`, `GWI`, `GRAY`, `CLEAR` | Cristal |

Si los nombres del PDF y de Odoo no son iguales, se debe acordar una tabla de
equivalencias antes de aplicar la carga. Por ejemplo, `RH` puede corresponder
a un valor Odoo llamado `pre-hung door RH`.

## 8. Revisión obligatoria antes de aplicar stock

Antes de habilitar la fase de ajuste inicial se debe validar:

1. Que cada PDF apunte a la ubicación física correcta.
2. Que no haya líneas Pending o Ambiguous.
3. Que las cantidades vacías hayan sido confirmadas como cero o corregidas.
4. Que los totales por familia de producto coincidan con el conteo de almacén.
5. Que no haya dos líneas que terminen en el mismo ITEM/ubicación sin una
   consolidación aprobada.
6. Que una persona de almacén y una persona de gerencia aprueben el resumen.

## 9. Seguridad y auditoría

- El módulo conserva el PDF adjunto y las líneas extraídas.
- No crea productos, atributos ni variantes de forma automática.
- No permite asumir cantidades vacías.
- Cada almacén o ubicación se procesa como un lote separado.
- La futura aplicación de stock debe generar un ajuste identificable por lote,
  fecha, ubicación y usuario responsable; nunca una entrada manual anónima.

## 10. Alcance de esta primera versión

La versión inicial permite cargar, leer, clasificar y validar los PDF. No
aplica cantidades a stock todavía. Esto es deliberado: primero se valida la
calidad de las equivalencias producto/variante con almacén.

La siguiente fase incorporará una pantalla de resolución de equivalencias y
una confirmación de doble aprobación para generar el ajuste inicial de cada
ubicación.

## 11. Solución de incidencias

| Situación | Qué revisar |
|---|---|
| El PDF genera cero líneas | Verifique que se seleccionó el formato correcto y que el PDF sea el original exportado desde Excel. |
| Un ITEM no coincide | Confirme modelo, medidas, color, cristal y configuración contra los atributos activos en Odoo. |
| Hay varias coincidencias | Falta un atributo discriminante; no elija una variante manualmente sin documentar la regla. |
| La cantidad está vacía | Solicite confirmación física; el sistema no asumirá cero. |
| La variante no existe | Cree o valide la variante por el flujo de productos antes de aplicar inventario. |
