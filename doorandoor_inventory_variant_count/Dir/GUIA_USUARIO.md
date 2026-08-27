# Guía de usuario — Conteo físico por variantes e ítems

## 1. Objetivo

El módulo permite realizar inventarios físicos sobre una ubicación interna exacta. Para un recorrido operativo completo consulte también la [Guía paso a paso](GUIA_PASO_A_PASO.md). Puede contar:

- variantes de producto directamente;
- componentes o atributos asociados a una variante;
- existencias separadas por lote, paquete y propietario.

Cuando una variante tiene ítems configurados, Odoo calcula la cantidad física de la variante a partir de las cantidades contadas de esos ítems. Al validar, aplica el ajuste sobre las existencias de la ubicación.

## 2. Perfiles de acceso

En **Ajustes → Usuarios y compañías → Usuarios**, asigne uno de estos permisos:

- **Inventory Counter**: crea sesiones, inicia y registra conteos, revisa y cancela. No valida ajustes.
- **Inventory Count Manager**: incluye los permisos anteriores y permite validar ajustes y reiniciar sesiones canceladas.

Las sesiones y líneas están limitadas a las compañías permitidas para el usuario.

## 3. Conceptos

### Variante

Producto almacenable que aparece en las existencias de Odoo. Cada combinación de atributos del producto es una variante distinta.

### Ítem de conteo

Componente o atributo personalizado utilizado para determinar cuántas unidades completas de una variante existen.

Ejemplo: una puerta utiliza tres bisagras y una cerradura.

| Variante | Ítem | Cantidad por variante |
|---|---|---:|
| Puerta A | Bisagra A | 3 |
| Puerta A | Cerradura B | 1 |

Si se cuentan 12 bisagras y 4 cerraduras, el resultado es 4 puertas. Si se cuentan 12 bisagras y 3 cerraduras, el sistema bloquea la validación porque los resultados son incompatibles.

### Sesión

Documento que congela la existencia esperada de una ubicación en el momento de iniciarse y conduce el proceso por estos estados:

`Borrador → Contando → Revisión → Validado`

Una sesión también puede pasar a `Cancelado` antes de validarse.

## 4. Generar el código de barras del producto

El formulario muestra siempre el campo estándar **Barcode**, para que el usuario pueda consultar o escribir el código asignado al producto. Cuando una variante no tiene código, pulse **Generate Barcode** junto al campo. El módulo completa únicamente las variantes cuyo campo está vacío y nunca reemplaza un código existente. Después de generarlo, el valor queda visible y el botón se oculta.

El formato es `AAAAMMDD + orden diario de 4 dígitos + verificador EAN-13`.

Ejemplo: la primera variante creada el 7 de agosto de 2026 utiliza la base `202608070001`; el sistema calcula y agrega el último dígito de control.

- El código contiene solamente números y tiene 13 dígitos.
- El correlativo comienza en `0001` cada día.
- Cada variante recibe un código único.
- Si el usuario introduce un barcode manual, se conserva sin reemplazarlo.
- Modificar posteriormente el barcode también es una operación manual; el módulo no lo regenera.
- El límite operativo es 9.999 variantes nuevas por día.

## 5. Imprimir labels del producto y sus variantes

El botón **Labels de productos**, aportado por `doorandoor_stock_labels`, abre un asistente ampliado por este módulo. En **Labels a imprimir** seleccione:

- **Producto**: imprime únicamente el label general del producto.
- **Variantes**: imprime labels de las variantes seleccionadas.
- **Producto y variantes**: imprime ambos tipos en el mismo PDF.

Cuando elija variantes, **Variantes asociadas** muestra y preselecciona automáticamente todas las variantes activas del producto. La tabla presenta nombre, referencia interna, barcode y atributos. Use **Marcar todas**, **Desmarcar todas** o elimine filas individuales de la selección. Después indique almacén y cantidad. La cantidad se aplica a cada variante seleccionada. El label usa primero el barcode de la variante y, si está vacío, su referencia interna.

Para proteger la generación del PDF, el asistente limita cada archivo a 50 labels y calcula automáticamente el **Total de lotes**. Seleccione el **Lote a imprimir** y pulse **Print**. Para 882 variantes con una copia, se generan 18 lotes: imprima el 1, luego cambie el campo a 2 y continúe hasta el 18. Cada PDF contiene solamente el tramo correspondiente.

El rollo físico Zebra mide `4 pulgadas de ancho × 6 pulgadas de alto`. El contenido se imprime verticalmente, de arriba hacia abajo, y ocupa un label completo por hoja. Cada barcode queda dentro de su propio rectángulo y utiliza tamaño ampliado, al igual que el número legible y los datos principales, para facilitar su lectura. Los atributos se muestran una sola vez como `nombre: valor`. En una plantilla con varias variantes, el label general se marca **PRODUCT TEMPLATE - NOT FOR INVENTORY COUNT**; para conteo utilice los labels individuales de variantes.

Una **variante** es una combinación comercial del producto, por ejemplo modelo, diseño, tamaño, apertura y bisagra. Un **ítem de conteo** es un componente como bisagra o cerradura utilizado para calcular existencias. El asistente de labels de producto imprime variantes; no busca ítems de conteo.

## 6. Configurar ítems de una variante

Ruta: **Physical Counts → Configuration → Variant Count Items**.

También puede abrir una variante de producto y usar el botón inteligente **Count Items**.

Complete:

- **Product**: variante almacenable.
- **Name**: nombre comprensible del componente o atributo.
- **Item Type**: componente o atributo personalizado.
- **Code**: identificador interno útil para importaciones; debe ser único dentro de la variante.
- **Barcode**: código utilizado por el lector; debe ser único en todo el sistema.
- **Quantity per Product**: cantidad del ítem necesaria para una unidad de la variante; debe ser mayor que cero.
- **Unit of Measure**: unidad del ítem.
- **Active**: solo los ítems activos se cargan en nuevas sesiones.

Configure los ítems antes de iniciar la sesión. La sesión toma una copia de la configuración existente en ese momento.

## 7. Crear e iniciar una sesión

1. Abra **Physical Counts → Count Sessions**.
2. Pulse **Nuevo**.
3. Seleccione la compañía, si aplica.
4. Seleccione una **ubicación interna**.
5. Opcionalmente cambie responsable, fecha o notas.
6. Guarde y pulse **Start and Load Stock**.

Al iniciar, el módulo:

- busca productos almacenables en la ubicación seleccionada;
- agrupa la cantidad por variante, lote, paquete y propietario;
- congela esa cantidad como existencia esperada;
- crea líneas para los ítems activos configurados.

La ubicación es exacta: no incluye automáticamente las sububicaciones. Para contar varios bins o sububicaciones, cree una sesión para cada una.

Si la ubicación no tiene existencias, el sistema no permite iniciar la sesión.

## 8. Registrar el conteo

### Variantes con ítems

Use la pestaña **Items to Count**. Introduzca la cantidad encontrada en cada línea. Al modificar la cantidad, la línea queda marcada como contada.

Si no encuentra un ítem, escriba explícitamente `0`. No deje la línea sin contar.

### Variantes sin ítems

Use **Variants / Adjustment**. Introduzca la cantidad física de la variante y marque **Counted**.

### Lectura de códigos de barras

Durante el estado `Counting`:

1. En **Barcode Capture**, introduzca o escanee el código.
2. Indique **Scan Quantity**; el valor habitual es `1`.
3. Pulse **Add Scan** o confirme desde el lector.

El módulo identifica dos tipos de código:

- **Barcode de producto o variante:** suma directamente la cantidad a esa variante. Un producto sin atributos tiene una única variante y se cuenta de la misma manera.
- **Barcode de ítem de conteo:** suma la cantidad del componente y posteriormente deriva cuántas variantes completas representa.

El código debe pertenecer a una variante o ítem activo incluido en la sesión. No mezcle ambos métodos sobre la misma línea: si comenzó escaneando la variante, continúe con sus labels directos; si comenzó contando componentes, complete todos sus ítems.

Si el mismo ítem aparece en más de una línea por lote, paquete o propietario, el escaneo se bloquea para evitar asignarlo al detalle equivocado. En ese caso registre manualmente la cantidad en la línea correcta.

### Importación CSV/XLSX

Ruta: **Physical Counts → Import Item Counts**.

La forma recomendada es:

1. Abrir las líneas de una sesión en estado `Counting`.
2. Exportarlas incluyendo su identificador externo o ID.
3. Modificar **Counted Quantity** y **Counted**.
4. Importarlas conservando el identificador para actualizar las líneas existentes.
5. Verificar los datos dentro de la sesión antes de pasar a revisión.

No importe como líneas nuevas sin vincular correctamente sesión, variante e ítem, porque puede generar duplicados funcionales.

## 9. Revisar y validar

1. Confirme que todos los ítems tengan cantidad, incluido cero cuando corresponda.
2. Pulse **Review**.
3. Revise **Difference** y el contador de diferencias.
4. Si necesita corregir, pulse **Back to Counting**.
5. Un usuario **Inventory Count Manager** pulsa **Validate Adjustment** y confirma.

Durante la validación:

- para variantes con ítems, el sistema divide cada cantidad contada entre su factor;
- todos los ítems deben producir la misma cantidad de variante dentro de la precisión de su unidad de medida;
- para variantes sin ítems, debe existir una cantidad directa marcada como contada;
- Odoo aplica la cantidad resultante a la existencia correspondiente;
- la sesión queda en `Validated` y registra un mensaje en el chatter.

La validación modifica inventario real. Revise cuidadosamente las diferencias antes de confirmar.

## 10. Cancelar o reiniciar

- **Cancel**: cancela una sesión que todavía no fue validada; no aplica ajustes.
- **Reset to Draft**: disponible para responsables. Elimina todas las líneas congeladas de una sesión cancelada y permite iniciarla nuevamente con existencias actuales.
- Una sesión validada no puede cancelarse desde este flujo.

## 11. Recomendaciones operativas

- Evite movimientos de inventario en la ubicación mientras se realiza el conteo.
- Cree sesiones separadas por ubicación exacta.
- Configure códigos de barras únicos y factores correctos antes de iniciar.
- Escriba cero cuando un ítem no exista físicamente.
- Use notas y chatter para documentar incidencias y aprobaciones.
- Revise lotes, paquetes y propietarios antes de corregir manualmente una línea.
- Valide primero en una ubicación controlada durante la puesta en marcha.
