# Guía de pruebas — Casos de uso

## 1. Control de la ejecución

Ambiente: ____________________  Fecha: __________  Responsable: ____________________

Versión del módulo: `18.0.1.5.1`

Para cada caso registre `Aprobado`, `Fallido` o `No aplica`, junto con capturas, documento generado y observaciones.

## 2. Datos base sugeridos

Prepare sin afectar inventario productivo:

- compañía habilitada para el probador;
- ubicación interna `PRUEBAS/CONTEO`;
- sububicación `PRUEBAS/CONTEO/BIN-01`;
- variante almacenable `PUERTA-TEST` con existencia 5 en la ubicación;
- ítem `BISAGRA-TEST`, código `BIS-TEST`, código de barras `COUNT-BIS-TEST`, factor 2;
- ítem `CERRADURA-TEST`, código `CER-TEST`, código de barras `COUNT-CER-TEST`, factor 1;
- variante almacenable `MARCO-TEST` con existencia 3 y sin ítems;
- usuarios de prueba Contador y Responsable.

Los casos que validan inventario cambian existencias. Ejecútelos en una base de pruebas o con productos y ubicaciones exclusivos.

## CP-01 — Visibilidad según permisos

**Objetivo:** comprobar accesos del Contador y Responsable.

**Pasos:**

1. Ingresar con un usuario sin grupos del módulo.
2. Confirmar que no aparece **Physical Counts**.
3. Asignar **Inventory Counter** e ingresar nuevamente.
4. Abrir una sesión en revisión.
5. Ingresar como **Inventory Count Manager** y abrir la misma sesión.

**Resultado esperado:** el Contador ve y opera sesiones, pero no ve **Validate Adjustment** ni **Reset to Draft**. El Responsable sí ve ambos botones y la configuración.

**Estado:** __________  **Evidencia:** ______________________________

## CP-02 — Configuración válida de ítems

**Objetivo:** registrar los componentes de una variante.

**Pasos:**

1. Abrir **Physical Counts → Configuration → Variant Count Items**.
2. Crear `BISAGRA-TEST` para `PUERTA-TEST`, factor 2 y su código de barras.
3. Crear `CERRADURA-TEST`, factor 1 y su código de barras.
4. Abrir la variante y comprobar el botón **Count Items**.

**Resultado esperado:** ambos registros se guardan y el botón muestra 2 ítems.

**Estado:** __________  **Evidencia:** ______________________________

## CP-03 — Validaciones de configuración

**Objetivo:** impedir configuraciones ambiguas o inválidas.

**Pasos y resultados esperados:**

1. Crear otro ítem con el mismo código dentro de `PUERTA-TEST`: Odoo lo rechaza.
2. Reutilizar el mismo código de barras en cualquier variante: Odoo lo rechaza.
3. Usar factor cero o negativo: Odoo lo rechaza.
4. Usar un código de barras compuesto solo por espacios: Odoo lo rechaza.
5. Seleccionar un producto no almacenable: no debe estar disponible en el selector.

**Estado:** __________  **Evidencia:** ______________________________

## CP-04 — Inicio y congelación de existencias

**Objetivo:** cargar la fotografía de inventario de una ubicación.

**Pasos:**

1. Crear una sesión para `PRUEBAS/CONTEO`.
2. Pulsar **Start and Load Stock**.
3. Revisar las pestañas de ítems y variantes.

**Resultado esperado:** la sesión pasa a `Counting`; aparecen `PUERTA-TEST` con esperado 5, sus ítems con esperados 10 y 5, y `MARCO-TEST` con esperado 3.

**Estado:** __________  **Evidencia:** ______________________________

## CP-05 — Ubicación vacía

**Objetivo:** impedir sesiones sin existencias.

**Pasos:** crear una ubicación interna vacía, crear una sesión y pulsar **Start and Load Stock**.

**Resultado esperado:** Odoo informa que no encontró inventario y conserva la sesión sin iniciar.

**Estado:** __________  **Evidencia:** ______________________________

## CP-06 — Alcance de ubicación exacta

**Objetivo:** confirmar que una sesión no incluye sububicaciones.

**Pasos:**

1. Colocar un producto únicamente en `PRUEBAS/CONTEO/BIN-01`.
2. Iniciar una sesión para `PRUEBAS/CONTEO`.
3. Iniciar otra sesión para `BIN-01`.

**Resultado esperado:** el producto no aparece en la sesión de la ubicación padre y sí aparece en la sesión de `BIN-01`.

**Estado:** __________  **Evidencia:** ______________________________

## CP-07 — Conteo consistente por ítems

**Objetivo:** derivar correctamente la cantidad de variante.

**Pasos:**

1. En una sesión contando, registrar 8 bisagras y marcar contado.
2. Registrar 4 cerraduras y marcar contado.
3. Registrar la cantidad de cualquier variante sin ítems.
4. Pulsar **Review** y después validar como Responsable.

**Resultado esperado:** 8/2 y 4/1 producen 4 puertas. La variante queda con cantidad contada 4 y Odoo aplica el ajuste desde 5 hasta 4.

**Estado:** __________  **Evidencia:** ______________________________

## CP-08 — Conteo inconsistente bloqueado

**Objetivo:** impedir un ajuste cuando los ítems producen cantidades distintas.

**Pasos:** registrar 8 bisagras y 3 cerraduras, pasar a revisión e intentar validar.

**Resultado esperado:** Odoo bloquea la validación e informa que los totales derivados para `PUERTA-TEST` son incompatibles. No cambia el inventario.

**Estado:** __________  **Evidencia:** ______________________________

## CP-09 — Ítem no encontrado físicamente

**Objetivo:** comprobar el tratamiento explícito del cero.

**Pasos:**

1. Dejar una línea de ítem sin editar e intentar **Review**.
2. Regresar a la línea, escribir `0` y marcarla como contada.
3. Intentar nuevamente **Review**.

**Resultado esperado:** el primer intento se bloquea indicando líneas sin contar. El segundo permite pasar a revisión si todos los demás ítems están contados.

**Estado:** __________  **Evidencia:** ______________________________

## CP-10 — Variante sin ítems

**Objetivo:** contar directamente una variante no configurada.

**Pasos:**

1. En **Variants / Adjustment**, localizar `MARCO-TEST`.
2. Introducir cantidad 2 y marcar **Counted**.
3. Completar los ítems restantes, pasar a revisión y validar.

**Resultado esperado:** la validación acepta la cantidad directa y ajusta `MARCO-TEST` de 3 a 2. Si no se marca como contado, la validación se bloquea.

**Estado:** __________  **Evidencia:** ______________________________

## CP-11 — Captura por código de barras

**Objetivo:** sumar conteos mediante lector o entrada manual.

**Pasos:**

1. En estado `Counting`, introducir `COUNT-BIS-TEST`.
2. Establecer **Scan Quantity** en 2 y pulsar **Add Scan** cuatro veces.
3. Revisar la línea de bisagras.

**Resultado esperado:** la cantidad contada aumenta hasta 8, la línea queda marcada como contada y el campo de código se limpia después de cada captura.

**Estado:** __________  **Evidencia:** ______________________________

## CP-12 — Errores de código de barras

**Objetivo:** validar protecciones de captura.

**Pasos y resultados esperados:**

1. Intentar escanear fuera del estado `Counting`: operación bloqueada.
2. Enviar el campo vacío: Odoo solicita un código.
3. Escanear un código inexistente o archivado: Odoo informa que no existe un ítem activo.
4. Escanear un ítem que no pertenece a productos de la sesión: operación bloqueada.

**Estado:** __________  **Evidencia:** ______________________________

## CP-13 — Trazabilidad por lote, paquete o propietario

**Objetivo:** conservar el detalle de existencias durante el conteo.

**Pasos:**

1. Preparar el mismo producto en dos lotes, paquetes o propietarios dentro de la ubicación.
2. Iniciar una sesión.
3. Revisar las líneas y escanear un ítem del producto.

**Resultado esperado:** existen líneas independientes por detalle. El escaneo se bloquea al encontrar más de una línea posible y solicita registrar la cantidad manualmente en la línea apropiada.

**Estado:** __________  **Evidencia:** ______________________________

## CP-14 — Regreso desde revisión

**Objetivo:** corregir datos antes de validar.

**Pasos:** completar un conteo, pulsar **Review**, pulsar **Back to Counting**, corregir una cantidad y volver a revisión.

**Resultado esperado:** la sesión alterna entre `Review` y `Counting`, conserva las líneas y recalcula las diferencias.

**Estado:** __________  **Evidencia:** ______________________________

## CP-15 — Cancelación y reinicio

**Objetivo:** abandonar una sesión sin ajustar existencias y reutilizarla correctamente.

**Pasos:**

1. Cancelar una sesión sin validar.
2. Comprobar las existencias.
3. Como Responsable, pulsar **Reset to Draft**.
4. Iniciar de nuevo la sesión.

**Resultado esperado:** cancelar no modifica inventario. El reinicio elimina las líneas anteriores, vuelve a borrador y al iniciar toma una fotografía actualizada.

**Estado:** __________  **Evidencia:** ______________________________

## CP-16 — Importación de cantidades

**Objetivo:** actualizar líneas mediante CSV/XLSX.

**Pasos:**

1. Abrir **Physical Counts → Import Item Counts**.
2. Exportar las líneas de la sesión conservando sus identificadores.
3. Completar cantidad y estado contado.
4. Importar el archivo como actualización.
5. Abrir la sesión y revisar los valores.

**Resultado esperado:** se actualizan las líneas existentes sin duplicarlas; los valores corresponden al archivo y permiten continuar a revisión.

**Estado:** __________  **Evidencia:** ______________________________

## CP-17 — Separación por compañía

**Objetivo:** respetar el entorno multicompañía.

**Pasos:** crear sesiones en dos compañías y probar usuarios con acceso a una sola compañía y a ambas.

**Resultado esperado:** cada usuario solo consulta sesiones y líneas de sus compañías permitidas; la ubicación seleccionable pertenece a la compañía activa o es compartida.

**Estado:** __________  **Evidencia:** ______________________________

## CP-18 — Sesión validada y auditoría

**Objetivo:** verificar el cierre del flujo.

**Pasos:** validar un conteo correcto, abrir la sesión y consultar la existencia del producto.

**Resultado esperado:** estado `Validated`, líneas no editables, inventario ajustado, mensaje de aplicación en el chatter y sesión no cancelable.

**Estado:** __________  **Evidencia:** ______________________________

## CP-19 — Barcode generado bajo demanda

**Objetivo:** comprobar la asignación mediante el botón sobre el barcode estándar.

**Pasos:**

1. Crear dos variantes sin completar **Barcode**.
2. Guardarlas y comprobar que siguen sin barcode.
3. Pulsar **Generate Barcode** sobre la plantilla o cada variante.

**Resultado esperado:** el campo **Barcode** es visible. Después de pulsar el botón, ambos productos muestran un barcode numérico de 13 dígitos; el botón se oculta en las variantes que ya tienen código. Los primeros 8 dígitos representan la fecha `AAAAMMDD`; el orden de la segunda variante es una unidad mayor que el de la primera y ambos códigos son diferentes.

**Estado:** __________  **Evidencia:** ______________________________

## CP-20 — Barcode manual preservado

**Objetivo:** permitir códigos definidos por el usuario.

**Pasos:** crear una variante indicando un barcode manual antes de guardar.

**Resultado esperado:** Odoo conserva exactamente el código introducido y el botón no lo reemplaza.

**Estado:** __________  **Evidencia:** ______________________________

## CP-21 — Código independiente por variante

**Objetivo:** comprobar la generación sobre productos con varias variantes.

**Pasos:** crear una plantilla con varios valores de atributo que produzcan al menos dos variantes, pulsar **Generate Barcode** y consultar sus variantes.

**Resultado esperado:** cada variante tiene su propio barcode EAN-13, con la misma fecha de creación y un orden diferente.

**Estado:** __________  **Evidencia:** ______________________________

## CP-22 — Labels del producto y de sus variantes

**Objetivo:** comprobar la integración con `doorandoor_stock_labels`.

**Pasos:**

1. Abrir un producto con al menos dos variantes activas.
2. Pulsar **Labels de productos**.
3. Elegir **Variantes** y comprobar que la tabla muestra y preselecciona todas las variantes con referencia, barcode y atributos.
4. Imprimir una vez con **Producto**.
5. Usar **Desmarcar todas**, volver a **Marcar todas** y retirar una variante individual.
6. Imprimir las variantes seleccionadas con cantidad 2.
7. Imprimir con **Producto y variantes** y cantidad 1.

**Resultado esperado:** los botones modifican la selección completa; se puede retirar una sola variante; la cantidad genera las copias pedidas por cada seleccionada. El PDF combinado contiene el label general y los labels de variantes con sus códigos.

**Estado:** __________  **Evidencia:** ______________________________

## CP-23 — Variante sin código imprimible

**Objetivo:** impedir labels de variantes que no puedan escanearse.

**Pasos:** dejar una variante sin barcode ni referencia interna, seleccionarla en el asistente y pulsar **Print**.

**Resultado esperado:** Odoo bloquea la impresión e identifica la variante que necesita barcode o referencia interna.

**Estado:** __________  **Evidencia:** ______________________________

## CP-24 — Layout físico y asociación del barcode

**Objetivo:** comprobar que cada barcode permanece dentro del label correcto.

**Pasos:** seleccionar ocho variantes, cantidad 1, imprimir y abrir el PDF.

**Resultado esperado:** cada label mide `90 × 66 mm`; aprovecha el espacio con textos y barcode ampliados; muestra producto, almacén y atributos una sola vez como `nombre: valor`; contiene un solo barcode y su número legible dentro del mismo rectángulo. No existen códigos acumulados o superpuestos al final del PDF.

**Estado:** __________  **Evidencia:** ______________________________

## CP-25 — Impresión segura por lotes

**Objetivo:** imprimir una selección grande sin agotar la memoria del servidor.

**Pasos:**

1. Seleccionar las 882 variantes y cantidad 1.
2. Confirmar que el asistente indica 18 lotes.
3. Imprimir el lote 1 y comprobar que contiene como máximo 50 labels.
4. Cambiar a lote 2 y confirmar que no repite las variantes del lote 1.
5. Probar un número de lote mayor que el total.

**Resultado esperado:** cada PDF se genera correctamente y contiene un tramo distinto; un número fuera del rango se bloquea con un mensaje claro; `wkhtmltopdf` no presenta `std::bad_alloc`.

**Estado:** __________  **Evidencia:** ______________________________

## CP-26 — Label general de plantilla multivariante

**Objetivo:** evitar que el label general se utilice como identificación inventariable.

**Pasos:** imprimir **Producto** sobre una plantilla con más de una variante.

**Resultado esperado:** el label muestra **PRODUCT TEMPLATE - NOT FOR INVENTORY COUNT**, sin caracteres dañados por codificación. Los labels de variantes no muestran esa advertencia y contienen sus EAN-13 individuales.

**Estado:** __________  **Evidencia:** ______________________________

## 3. Cierre de pruebas

| Resultado | Cantidad |
|---|---:|
| Aprobados | |
| Fallidos | |
| No aplica | |

Observaciones generales:

________________________________________________________________________________

Aprobado por: ____________________  Firma: ____________________  Fecha: __________
