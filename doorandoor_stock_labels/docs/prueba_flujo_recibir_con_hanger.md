# Prueba De Flujo: Recibir Con Hanger

## Objetivo

Validar en Odoo 18 CE el flujo de recepcion usando el boton `Recibir con hanger`, contando una unidad por cada disparo de escaneo.

## Alcance De La Prueba

La prueba valida:

- apertura del wizard desde la recepcion
- lectura de codigo por producto
- conteo incremental por disparo
- aplicacion del conteo a la recepcion
- continuidad del flujo normal de validacion

No valida todavia:

- conteo por numero de embalaje
- conteo por lote especifico
- escaneo QR desde movil
- automatizacion con app Android

## Prerrequisitos

1. El modulo `doorandoor_stock_labels` debe estar actualizado a la version que incluye `Recibir con hanger`.
2. Debe existir una recepcion de compra en estado que muestre el boton `Recibir con hanger`.
3. Los productos de prueba deben tener alguno de estos valores identificables:
   - `barcode`
   - `default_code`
   - nombre del producto
4. El usuario de prueba debe tener permisos de inventario.

## Datos Recomendados Para La Prueba

Preparar una compra con al menos:

- Producto A con cantidad `5`
- Producto B con cantidad `3`

Recomendado:

- que ambos tengan `barcode`
- que tengan referencias internas claras

## Flujo Paso A Paso

### 1. Crear La Compra

1. Ir a `Compras`.
2. Crear una orden de compra nueva.
3. Agregar productos y cantidades.
4. Confirmar la orden.

Resultado esperado:

- se crea la recepcion asociada

### 2. Abrir La Recepcion

1. Entrar a la recepcion creada desde la compra o desde Inventario.
2. Confirmar que el boton visible diga `Recibir con hanger`.

Resultado esperado:

- el boton ya no debe mostrarse con el texto anterior

### 3. Abrir El Wizard

1. Pulsar `Recibir con hanger`.

Resultado esperado:

- se abre un wizard modal
- el wizard muestra la recepcion
- el wizard lista los productos esperados
- cada linea muestra:
  - producto
  - cantidad esperada
  - cantidad contada

### 4. Probar Conteo Manual

1. En el campo `Codigo escaneado`, escribir el `barcode` o `default_code` del Producto A.
2. Pulsar `Contar disparo`.
3. Repetir hasta sumar varias unidades.

Resultado esperado:

- cada disparo suma `1` a la columna `Contado`
- solo aumenta la linea del producto correcto

### 5. Probar Conteo Con Scanner

1. Conectar el hanger o scanner como teclado.
2. Colocar el cursor en `Codigo escaneado`.
3. Escanear varias veces el mismo producto.

Resultado esperado:

- cada lectura incrementa `1`
- no debe cambiar otra linea

### 6. Probar Codigo Invalido

1. Escribir o escanear un codigo inexistente.
2. Pulsar `Contar disparo`.

Resultado esperado:

- Odoo muestra error indicando que el codigo no coincide con ningun producto esperado

### 7. Aplicar Conteo

1. Cuando el conteo sea correcto, pulsar `Aplicar conteo`.

Resultado esperado:

- el wizard se cierra
- la recepcion queda con cantidades cargadas en las lineas de movimiento

### 8. Validar La Recepcion

1. Revisar operaciones detalladas o lineas de recepcion.
2. Validar la recepcion por el flujo normal.

Resultado esperado:

- la recepcion debe continuar su flujo normal

## Casos Minimos A Probar

### Caso 1: Conteo Exacto

- esperado `5`
- escaneado `5`

Resultado esperado:

- cantidad aplicada igual a la esperada

### Caso 2: Conteo Parcial

- esperado `5`
- escaneado `3`

Resultado esperado:

- se aplica `3`
- el usuario puede decidir si valida parcial o sigue contando

### Caso 3: Dos Productos Distintos

- escanear Producto A varias veces
- escanear Producto B varias veces

Resultado esperado:

- cada producto acumula en su propia linea

### Caso 4: Codigo No Reconocido

- usar un codigo ajeno a la recepcion

Resultado esperado:

- error controlado

## Criterio De Aprobacion

La prueba se considera correcta si:

- el wizard abre desde `Recibir con hanger`
- el conteo sube de uno en uno por disparo
- los productos correctos reciben el conteo correcto
- el conteo se aplica a la recepcion
- la recepcion puede seguir el flujo normal

## Riesgos Conocidos En Esta Primera Version

- el conteo actual identifica por `barcode`, `default_code` o nombre del producto
- todavia no distingue por embalaje ni por lote escaneado
- todavia no bloquea sobreconteo contra cantidad esperada
- todavia no hace recepcion automatica por QR de embalaje

## Siguiente Evolucion Recomendada

Cuando esta prueba base quede aprobada, el siguiente paso natural es:

1. contar por `numero de embalaje`
2. ligar conteo a productos por lote
3. impedir sobreconteo
4. soportar flujo de escaneo desde movil y desde hanger fisico
