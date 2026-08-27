# Conteo de inventario desde móvil o hanger

## Objetivo

Registrar un conteo físico por ubicación usando el barcode de cada variante o
ítem. El escaneo no modifica el inventario inmediatamente: primero crea un
conteo auditable, después se revisan las diferencias y finalmente un responsable
autorizado aplica el ajuste.

## Preparación

1. Cada variante física debe tener un barcode único.
2. El operador debe tener asignado el rol **Almacenero DoorAndDoor** y acceso a
   la compañía correspondiente.
3. No deben realizarse entradas, salidas o traslados sobre la ubicación mientras
   se ejecuta el conteo.

## Flujo operativo

1. Abrir **Operaciones > Almacén > Conteo de inventario**.
2. Crear una sesión y seleccionar la ubicación interna que se contará.
3. Pulsar **Start and Load Stock**. El sistema toma una fotografía de las
   existencias teóricas de esa ubicación.
4. Indicar la **Cantidad por lectura**. Normalmente debe ser `1`.
5. Pulsar **Usar cámara** y enfocar el barcode. Cada lectura válida se guarda y
   suma automáticamente.
6. Si la cámara no está disponible, escribir el barcode y pulsar **Registrar
   código escrito**.
7. Revisar las pestañas de ítems y variantes: cantidad esperada, contada y
   diferencia.
8. Pulsar **Review**. Si existe un producto no contado, registrar expresamente
   cero cuando corresponda.
9. Un usuario con rol **Inventory Count Manager** valida mediante **Validate
   Adjustment**. Solo este paso modifica `stock.quant` y genera la trazabilidad
   del ajuste.

## Controles

- No se acepta un barcode ajeno a la sesión.
- No se permite mezclar el conteo directo de una variante con el conteo de sus
  componentes.
- Lotes, paquetes y propietarios deben corregirse en su línea específica.
- La sesión conserva usuario, fecha, ubicación, cantidades y diferencias.
- Una sesión validada no vuelve a modo de conteo.
