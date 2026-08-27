# Guía paso a paso — Conteo de inventario por variantes

## 1. ¿Qué permite hacer este módulo?

`doorandoor_inventory_variant_count` permite contar físicamente los productos almacenados en una ubicación de Odoo y ajustar sus existencias.

Puede trabajar de dos maneras:

1. **Conteo directo:** se escribe cuántas unidades completas del producto existen.
2. **Conteo por ítems:** se cuentan componentes o atributos y el sistema calcula cuántas unidades completas representan.

Además, permite generar bajo demanda un barcode EAN-13 basado en fecha y orden, e imprimir labels del producto y de sus variantes.

## 2. Instalar o actualizar el módulo

Estas operaciones deben realizarlas un administrador autorizado.

### Instalación inicial

1. Ingrese a Odoo con permisos de administración.
2. Active el modo desarrollador.
3. Abra **Aplicaciones**.
4. Ejecute **Actualizar lista de aplicaciones**.
5. Quite el filtro predeterminado **Aplicaciones**, si impide encontrar el módulo.
6. Busque `doorandoor_inventory_variant_count` o **Inventory Count by Variant and Items**.
7. Pulse **Instalar**.
8. Espere a que Odoo termine y confirme que aparece el menú **Physical Counts**.

### Si el módulo ya estaba instalado

1. Abra **Aplicaciones** en modo desarrollador.
2. Ejecute **Actualizar lista de aplicaciones**.
3. Busque el módulo.
4. Pulse **Actualizar**.
5. Confirme que la versión instalada es `18.0.1.5.0`.

No reinicie manualmente los contenedores Docker. Si la plataforma necesita un reinicio, solicítelo al equipo SRE.

## 3. Asignar permisos a los usuarios

1. Abra **Ajustes → Usuarios y compañías → Usuarios**.
2. Seleccione el usuario que realizará el conteo.
3. Localice la categoría **Inventory Counts**.
4. Asigne uno de estos perfiles:
   - **Inventory Counter** para registrar y revisar conteos.
   - **Inventory Count Manager** para configurar ítems, contar y validar ajustes.
5. Guarde el usuario.
6. Cierre y vuelva a abrir su sesión para actualizar los permisos.

Recomendación: use al menos dos usuarios durante las pruebas, uno Contador y otro Responsable.

## 4. Generar el barcode de un producto

1. Abra **Inventario → Productos → Productos**.
2. Pulse **Nuevo**.
3. Escriba el nombre del producto.
4. Marque el producto como almacenable cuando corresponda.
5. Deje vacío el campo **Barcode**.
6. Guarde el producto.
7. Vuelva a abrirlo y compruebe que **Barcode** continúa vacío.
8. Pulse **Generate Barcode** junto al campo.
9. Revise el valor asignado a **Barcode**.

El campo **Barcode** permanece visible para consultar o editar el valor. Cuando contiene un código, el botón de generación se oculta para evitar reemplazos accidentales.

El campo debe contener ahora 13 números con esta estructura:

`AAAAMMDD + orden diario de cuatro dígitos + verificador EAN-13`

Ejemplo para el primer producto creado el 7 de agosto de 2026:

`2026080700010`

El último número es calculado por el sistema. El segundo producto del mismo día utilizará el orden `0002` y tendrá su propio verificador.

### Usar un barcode manual

1. Cree el producto.
2. Escriba el código deseado en **Barcode** antes de guardar.
3. Guarde y vuelva a abrir el producto.

El código manual debe permanecer sin cambios. Si pulsa **Generate Barcode** cuando todas las variantes ya tienen código, Odoo informa que no existe ninguna variante pendiente y no sobrescribe datos.

### Productos con varias variantes

Cuando una plantilla genera varias variantes, el botón genera un barcode diferente para cada variante que todavía esté vacía. Abra el botón de variantes del producto para consultar cada código.

## 4.1. Imprimir labels del producto y sus variantes

1. Abra el producto.
2. Pulse **Labels de productos**.
3. En **Labels a imprimir**, elija una opción:
   - **Producto** para el label general.
   - **Variantes** para los labels de las combinaciones del producto.
   - **Producto y variantes** para ambos.
4. Si eligió variantes, la tabla **Variantes asociadas** mostrará y preseleccionará todas las variantes activas con referencia, barcode y atributos.
5. Use **Marcar todas**, **Desmarcar todas** o retire variantes individuales hasta obtener la selección deseada.
6. Seleccione el almacén.
7. Indique **Labels Quantity**. Esta cantidad se imprime para cada elemento seleccionado.
8. Consulte **Variantes seleccionadas**, **Total de lotes** y el resumen. Cada PDF admite como máximo 50 labels.
9. Escriba `1` en **Lote a imprimir** y pulse **Print**.
10. Revise el PDF antes de enviarlo a la impresora. Cada página debe medir `4 pulgadas de ancho × 6 pulgadas de alto`, con el contenido vertical y un solo label que ocupe la hoja completa. El barcode debe mostrar número, producto, almacén y atributos legibles sin acercamiento excesivo.
11. Regrese al asistente, cambie **Lote a imprimir** a `2` y repita hasta completar el total indicado.

Para imprimir una variante, esta debe tener barcode o referencia interna. El label muestra la plantilla, los atributos con sus nombres y el código legible. El label general de un producto con varias variantes indica que no debe utilizarse para conteo de inventario.

## 5. Preparar un ejemplo de conteo por ítems

Utilice este ejemplo para aprender y probar el flujo:

- Producto almacenable: `PUERTA DE PRUEBA`.
- Existencia inicial: 5 puertas.
- Ítem 1: `BISAGRA`, factor 2 por puerta.
- Ítem 2: `CERRADURA`, factor 1 por puerta.

Una existencia de 5 puertas equivale a 10 bisagras y 5 cerraduras.

## 6. Configurar los ítems del producto

1. Abra **Physical Counts → Configuration → Variant Count Items**.
2. Pulse **Nuevo**.
3. Configure el primer ítem:
   - **Product:** `PUERTA DE PRUEBA`.
   - **Name:** `BISAGRA`.
   - **Item Type:** `Component`.
   - **Code:** `BIS-PRUEBA`.
   - **Barcode:** `COUNT-BIS-PRUEBA`.
   - **Quantity per Product:** `2`.
   - **Unit of Measure:** unidades.
   - **Active:** marcado.
4. Guarde.
5. Cree el segundo ítem:
   - **Product:** `PUERTA DE PRUEBA`.
   - **Name:** `CERRADURA`.
   - **Item Type:** `Component`.
   - **Code:** `CER-PRUEBA`.
   - **Barcode:** `COUNT-CER-PRUEBA`.
   - **Quantity per Product:** `1`.
6. Guarde.
7. Abra `PUERTA DE PRUEBA` y compruebe que el botón **Count Items** muestra dos registros.

Reglas importantes:

- El código interno no puede repetirse dentro del mismo producto.
- El barcode de un ítem no puede repetirse en ningún otro ítem.
- **Quantity per Product** debe ser mayor que cero.
- Configure los ítems antes de iniciar la sesión de conteo.

## 7. Preparar existencias para la prueba

1. Seleccione una ubicación interna de prueba.
2. Registre 5 unidades de `PUERTA DE PRUEBA` en esa ubicación mediante el flujo autorizado de Inventario.
3. Confirme en el reporte de existencias que la cantidad disponible es 5.
4. Evite movimientos sobre esa ubicación mientras ejecuta el conteo.

La sesión toma una fotografía de una ubicación exacta. Una ubicación padre no incluye automáticamente sus sububicaciones.

## 8. Crear la sesión de conteo

1. Abra **Physical Counts → Count Sessions**.
2. Pulse **Nuevo**.
3. Seleccione la **Location** de prueba.
4. Confirme la compañía y el responsable.
5. Agregue una nota si necesita identificar la prueba.
6. Guarde.
7. Pulse **Start and Load Stock**.

El sistema debe:

- asignar un número a la sesión;
- cambiar el estado de `Draft` a `Counting`;
- mostrar `PUERTA DE PRUEBA` con existencia esperada 5;
- generar una línea esperada de 10 bisagras;
- generar una línea esperada de 5 cerraduras.

Si aparece **No stock was found in the selected location**, compruebe que eligió la ubicación exacta y que el producto tiene existencias allí.

## 9. Registrar un conteo manual por ítems

Suponga que físicamente encontró material para 4 puertas: 8 bisagras y 4 cerraduras.

1. Abra la pestaña **Items to Count**.
2. En la línea `BISAGRA`, escriba `8` en **Counted Quantity**.
3. Confirme que **Counted** quedó marcado.
4. En la línea `CERRADURA`, escriba `4`.
5. Confirme que la línea quedó marcada.
6. Revise las diferencias mostradas.

El sistema calculará posteriormente:

- 8 bisagras ÷ 2 por puerta = 4 puertas.
- 4 cerraduras ÷ 1 por puerta = 4 puertas.

Ambos resultados coinciden, por lo que el conteo es consistente.

Cuando no encuentre un ítem, escriba explícitamente `0`. Una línea vacía se considera pendiente de contar.

## 10. Registrar el conteo con lector de barcode

Esta opción funciona durante el estado `Counting`.

1. Localice **Barcode Capture**.
2. En **Scan Quantity**, indique cuánto sumará cada lectura; normalmente `1`.
3. Escanee o escriba `COUNT-BIS-PRUEBA`.
4. Pulse **Add Scan**.
5. Repita hasta alcanzar la cantidad física.
6. Haga lo mismo con `COUNT-CER-PRUEBA`.

Cada lectura busca primero el barcode de una variante de producto. Si lo encuentra, suma directamente esa variante; si no, busca un ítem de conteo y suma su componente. Un producto sin atributos también posee una única variante técnica, por lo que su barcode se cuenta directamente de la misma forma.

No mezcle en la misma línea scans directos de variante con scans de sus componentes. El sistema bloquea la mezcla para impedir dobles conteos.

Si un producto aparece en varias líneas por lote, paquete o propietario, el sistema bloquea el escaneo ambiguo. Escriba la cantidad manualmente en la línea de trazabilidad correcta.

## 11. Contar un producto sin ítems configurados

1. Abra la pestaña **Variants / Adjustment**.
2. Localice el producto sin ítems.
3. Escriba directamente su cantidad física en **Counted Quantity**.
4. Marque **Counted**.

No se puede validar una variante sin ítems si no se ha marcado su conteo directo.

## 12. Pasar a revisión

1. Compruebe que todos los ítems tienen cantidad, incluso cero.
2. Pulse **Review**.
3. Revise el contador de diferencias y las líneas resaltadas.
4. Compruebe producto, lote, paquete y propietario cuando existan.
5. Si encuentra un error, pulse **Back to Counting**.
6. Corrija la cantidad y vuelva a pulsar **Review**.

Si Odoo informa que existen líneas sin contar, vuelva a **Items to Count**, complete las líneas pendientes y marque **Counted**.

## 13. Validar y aplicar el ajuste

Este paso modifica las existencias reales y requiere **Inventory Count Manager**.

1. Ingrese como Responsable o solicite su revisión.
2. Abra la sesión en estado `Review`.
3. Compruebe nuevamente las cantidades.
4. Pulse **Validate Adjustment**.
5. Confirme el mensaje de advertencia.

Para el ejemplo, Odoo cambia la existencia de 5 a 4 puertas. La sesión pasa a `Validated` y registra el ajuste en el chatter.

### Conteos incompatibles

Si se registran 8 bisagras y 3 cerraduras, los cálculos producen 4 y 3 puertas. Odoo bloquea la validación y no modifica el inventario.

Para corregir:

1. Pulse **Back to Counting**.
2. Verifique físicamente los ítems.
3. Corrija la cantidad equivocada.
4. Regrese a revisión y valide nuevamente.

## 14. Cancelar una sesión

1. Abra una sesión que no esté validada.
2. Pulse **Cancel**.

Cancelar no modifica las existencias.

Para reutilizarla:

1. Ingrese como Responsable.
2. Pulse **Reset to Draft**.
3. El sistema eliminará las líneas anteriores.
4. Seleccione o confirme la ubicación.
5. Pulse nuevamente **Start and Load Stock** para tomar existencias actuales.

## 15. Importar cantidades desde CSV o XLSX

1. Abra **Physical Counts → Import Item Counts**.
2. Filtre las líneas de la sesión que está en `Counting`.
3. Expórtelas conservando el ID o identificador externo.
4. Complete **Counted Quantity** y **Counted** en el archivo.
5. Use **Favoritos → Importar registros**.
6. Importe como actualización de las líneas existentes.
7. Abra la sesión y verifique todas las cantidades antes de revisar.

No elimine los identificadores al preparar el archivo. Sin ellos, Odoo puede intentar crear líneas nuevas en lugar de actualizar las existentes.

## 16. Lista de comprobación rápida

Antes de iniciar:

- [ ] El usuario tiene el permiso correcto.
- [ ] Los productos son almacenables.
- [ ] Los ítems y factores están configurados.
- [ ] Los barcodes de ítems son únicos.
- [ ] Se seleccionó la ubicación exacta.
- [ ] No habrá movimientos durante el conteo.

Antes de validar:

- [ ] Todas las líneas fueron contadas.
- [ ] Se escribió cero cuando no se encontró un ítem.
- [ ] Se revisaron diferencias y trazabilidad.
- [ ] Los cálculos de los ítems producen la misma cantidad de variante.
- [ ] Un Responsable aprobó el ajuste.

Después de validar:

- [ ] La sesión aparece como `Validated`.
- [ ] La existencia resultante coincide con el conteo físico.
- [ ] El chatter muestra el mensaje del ajuste.
- [ ] Se guardaron las evidencias requeridas.

## 17. Mensajes frecuentes

| Mensaje o situación | Causa | Solución |
|---|---|---|
| No se encontró inventario | La ubicación exacta está vacía | Revise ubicación y existencias |
| Existen líneas sin contar | Algún ítem quedó vacío | Escriba la cantidad o cero y marque contado |
| Ítems incompatibles | Los factores producen cantidades de variante distintas | Verifique el conteo físico y los factores |
| Barcode inexistente | El código no pertenece a un ítem activo | Revise configuración y estado del ítem |
| Barcode ambiguo | El producto está separado por trazabilidad | Registre manualmente sobre la línea correcta |
| No aparece Validar | El usuario no es Responsable | Asigne Inventory Count Manager |
| No aparece el menú | Faltan permisos o actualización del módulo | Revise grupos y versión instalada |
