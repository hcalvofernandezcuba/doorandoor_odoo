# Guía de recepción guiada y ubicación en lotes

Versión validada: `doorandoor_warehouse_map 18.0.1.10.0`  
Ticket oficial: `TKT/2026/00101` en Gestión  
Casos de demostración: base Local, marcador `DEMO-GR-20261023`

## Qué problema resuelve

El operador no debe comenzar buscando un lote sin contexto. El proceso parte
del almacén que recibirá la mercancía, utiliza una recepción existente cuando
la hay y evita volver a escribir el ITEM. Si no existe recepción, el sistema
crea una recepción oficial para que el ingreso nunca quede sin documento.

## Orden obligatorio del formulario

1. Seleccione **Almacén de destino**.
2. Seleccione **Recepción / traslado existente** si aparece en la lista.
3. Si existe documento:
   - con un solo ITEM, el sistema lo completa automáticamente;
   - con varios ITEM, el selector muestra únicamente sus líneas.
4. Si no existe documento, deje ese campo vacío. El sistema creará una
   recepción de proveedor usando el ITEM, cantidad, proveedor y referencia.
5. Confirme el **ITEM**.
6. Escriba la **Cantidad**.
7. Revise la propuesta física:
   - completa primero un lote del mismo ITEM con capacidad disponible;
   - capacidad operativa predeterminada: **33 unidades**;
   - si no cabe, propone la posición vacía más cercana a los lotes del mismo ITEM.
8. Prepare o escanee labels según el origen del documento.

## Regla de labels

| Origen | Modo automático | Acción del operador |
|---|---|---|
| Traslado interno de DoorAndDoor | Labels existentes | Escanear con Hanger exactamente los labels despachados. Nunca generar otros. |
| Recepción de proveedor ya captada | Labels compatibles del documento | Escanear/adoptar los labels físicos de origen. No imprimir labels nuevos. |
| Recepción creada automáticamente | Generar labels DoorAndDoor | Imprimir los labels nuevos y usarlos como control oficial. |

El modo queda bloqueado por el servidor. Un traslado interno no puede cambiarse
a “Generar labels”, ni siquiera mediante una escritura técnica.

## Casos persistentes disponibles en Local

Ruta: **Conteos físicos → Ingresar mercancía a lote**. Busque el número `ISR`.

### Caso A — completar lote similar

- Control: `ISR/2026/00089`
- Documento: `CWH/IN/00001`
- ITEM: `DEMO-GR-33`
- Cantidad: `3`
- Lote actual: `90A1-L`, con 30 unidades de 33.
- Resultado esperado: propone el mismo lote `90A1-L`.

### Caso B — la cantidad no cabe

- Control: `ISR/2026/00090`
- Documento: `CWH/IN/00002`
- ITEM: `DEMO-GR-33`
- Cantidad: `32`
- Resultado esperado: ningún lote existente admite la cantidad; propone la
  posición vacía cercana `90A1-R`.

### Caso C — no existía recepción

- Control: `ISR/2026/00091`
- Recepción oficial creada: `CWH/IN/00003`
- Referencia: `DEMO-GR-20261023-C-AUTOMATICA`
- Estado: Listo para validar.
- Modo: Generar labels.
- Resultado esperado: muestra alerta de impresión y conserva dos labels nuevos.

### Caso D — recepción existente de proveedor

- Control: `ISR/2026/00092`
- Documento: `CWH/IN/00004`
- Estado: Listo para validar.
- Labels escaneados: `DEMO-VENDOR-20261023-01` y `...-02`.
- Resultado esperado: adopta los labels físicos; no habilita impresión de nuevos.

### Caso E — traslado interno DoorAndDoor

- Control: `ISR/2026/00093`
- Documento: `DT/INT/00001`
- Origen: Doorandoor - Tampa.
- Destino: Central Warehouse.
- Estado: Listo para validar.
- Resultado esperado: conserva únicamente los dos labels contados en el
  despacho de origen; no crea un serial sustituto.

## Controles de seguridad verificados

- El almacén es editable solo en borrador y se limita a los almacenes autorizados.
- El ITEM de un documento existente se limita a sus líneas.
- La cantidad no puede superar lo documentado.
- La recomendación nunca cruza almacenes ni mezcla variantes.
- Una posición reservada para otro ITEM con más de cinco unidades se descarta.
- La capacidad considera también unidades preparadas y aún pendientes de validar,
  para evitar que dos operadores sobrecarguen el mismo espacio.
- El inventario cambia solamente al validar la recepción.

## Resultado técnico Local

- Pruebas automáticas: 7 ejecutadas, 0 fallos, 0 errores.
- Casos persistentes: 5 creados y auditados.
- Respaldo previo: `backups/20261023_guided_receipt_1100/doorandoor.dump`.
- SHA-256 del respaldo:
  `ac94276bd25b483f5a9169525ed5b5a3e3c3c70eeecc20dd824590c359df3548`.

## Validación de gerencia en Pruebas

Validar en este orden: A, B, C, D y E. Gestión no debe actualizarse hasta que
gerencia confirme los cinco resultados y el equipo apruebe la capacitación.
