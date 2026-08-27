# Conteo de inventario por variantes e ítems — Odoo 18 CE

Sesiones de inventario físico para variantes de producto con componentes o
atributos personalizados configurables. Admite captura manual, lectores de
código de barras que emulan teclado, importación nativa CSV/XLSX de Odoo y
vistas adaptables a móvil o tableta.

Cuando una variante no tiene código de barras, el botón **Generate Barcode**
asigna al campo estándar `Barcode` un EAN-13 único compuesto por fecha, orden
diario y dígito verificador. Los códigos existentes no se reemplazan. El botón
**Labels de productos** permite imprimir el label general, los labels de sus
variantes o ambos.

## Instalación

1. Copie `doorandoor_inventory_variant_count` en una ruta de addons de Odoo.
2. Reinicie Odoo y actualice la lista de aplicaciones.
3. Instale **Inventory Count by Variant and Items**.
4. Asigne a cada usuario **Inventory Counter** o **Inventory Count Manager**.

Dependencias: módulos estándar `stock`, `barcodes` y `mail` de Odoo 18 CE.

## Configuración

Abra **Physical Counts → Configuration → Variant Count Items**. Para cada
variante almacenable, defina sus ítems:

- nombre del componente o atributo personalizado;
- código interno y código de barras únicos;
- cantidad del ítem contenida en una unidad completa de la variante;
- unidad de medida.

Ejemplo: una puerta usa tres bisagras y una cerradura. Defina `BISAGRA-A` con
factor 3 y `CERRADURA-B` con factor 1.

## Flujo de trabajo

1. Cree una sesión y seleccione una ubicación interna.
2. Iníciela para congelar la existencia esperada.
3. Registre los ítems manualmente, con lector o mediante CSV/XLSX.
4. Cuando no encuentre unidades, escriba cero y marque la línea como contada.
5. Revise diferencias. Todos los factores deben producir la misma cantidad de
   la variante.
6. Un responsable valida y aplica el ajuste mediante `stock.quant`.

Si una variante no tiene ítems configurados, introduzca directamente la
cantidad contada en la pestaña de variantes.

## Importación CSV/XLSX

Use la lista **Import Item Counts** y relacione las columnas `Session`,
`Product`, `Item`, `Counted Quantity` y `Counted`.

El método más seguro es exportar primero las líneas de la sesión abierta,
modificar `Counted Quantity` y `Counted`, y reimportarlas conservando los IDs.
Así Odoo actualiza las líneas existentes en lugar de duplicarlas.

## Comportamiento importante

- Cada sesión cuenta una ubicación interna exacta. Cree sesiones separadas para
  las sububicaciones o bins.
- Los lotes, paquetes y propietarios permanecen en líneas independientes.
- Solo un responsable puede validar el ajuste.
- Se bloquea la validación si los ítems producen totales incompatibles para la
  variante.
