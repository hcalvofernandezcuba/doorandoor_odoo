# Permisos de Operaciones y Roles Requeridos

Fecha de corte: 2026-07-26

Este documento resume los permisos necesarios para usar correctamente el modulo `doorandoor_process_control` y sus accesos operativos en `Ventas`, `Facturacion`, `Manufactura` e `Inventario`.

## 1. Grupos propios del modulo `doorandoor_process_control`

Actualmente el modulo define estos grupos:

- `DoorAndDoor Process User`
  - XML ID: `doorandoor_process_control.group_ddpc_user`
  - Da acceso a:
    - menu raiz `Operaciones`
    - `Process Flows`
    - `Process Tasks`
    - accesos operativos dentro de `Ventas`, `Facturacion`, `Manufactura` e `Inventario`
    - accesos rapidos a `Cotizaciones`, `Prefacturas` y `Facturas`
  - Permisos sobre modelos:
    - `doorandoor.process.flow`: leer, crear, escribir
    - `doorandoor.process.task`: leer, crear, escribir
    - no puede borrar

- `DoorAndDoor Process Manager`
  - XML ID: `doorandoor_process_control.group_ddpc_manager`
  - Implica automaticamente `DoorAndDoor Process User`
  - Da acceso adicional a:
    - `Cargar historicos`
    - borrado de `Process Flows`
    - borrado de `Process Tasks`
    - uso del wizard de carga historica

## 2. Permisos base de Odoo que siguen siendo necesarios

El grupo de `Operaciones` no reemplaza los permisos funcionales de Odoo. Solo agrega la capa de control de procesos.

Por tanto, cada usuario tambien necesita los grupos base del modulo donde va a trabajar.

### Ventas

Para ver y operar desde:

- `Ventas -> Operaciones`
- `Cotizaciones`
- `Prefacturas`
- `Facturas` desde contexto comercial

el usuario necesita, ademas de `DoorAndDoor Process User`:

- un grupo funcional de `Ventas`
  - ejemplo: usuario de ventas / vendedor

### Facturacion

Para ver y operar desde:

- `Facturacion -> Operaciones`
- abrir facturas
- trabajar con prefacturas y facturas

el usuario necesita, ademas de `DoorAndDoor Process User`:

- un grupo funcional de `Contabilidad / Facturacion`
  - ejemplo: usuario de facturacion o accountant segun el caso

### Manufactura

Para ver y operar desde:

- `Manufactura -> Operaciones`
- abrir MOs
- imprimir labels de fabricacion

el usuario necesita, ademas de `DoorAndDoor Process User`:

- un grupo funcional de `Manufactura`

### Inventario

Para ver y operar desde:

- `Inventario -> Operaciones`
- abrir pickings
- operar tareas logisticas

el usuario necesita, ademas de `DoorAndDoor Process User`:

- un grupo funcional de `Inventario / Stock`

## 3. Perfiles recomendados

### 3.1. Usuario operativo comercial

Debe tener:

- `DoorAndDoor Process User`
- permisos de `Ventas`
- permisos de `Facturacion` si va a entrar a prefacturas/facturas

Usa:

- `Ventas -> Operaciones`
- `Facturacion -> Operaciones`
- `Cotizaciones`
- `Prefacturas`
- `Facturas`

### 3.2. Usuario de manufactura

Debe tener:

- `DoorAndDoor Process User`
- permisos de `Manufactura`

Opcionalmente:

- permisos de `Inventario` si tambien valida transferencias o pickings

Usa:

- `Manufactura -> Operaciones`
- labels de fabricacion
- procesos de manufactura

### 3.3. Usuario de almacen / inventario

Debe tener:

- `DoorAndDoor Process User`
- permisos de `Inventario`

Usa:

- `Inventario -> Operaciones`
- pickings
- tareas logisticas
- entregas / rutas del proceso

### 3.4. Gerencia / control de procesos

Debe tener:

- `DoorAndDoor Process User`

Y, segun el alcance que quiera revisar:

- `Ventas`
- `Facturacion`
- `Manufactura`
- `Inventario`

Si ademas va a:

- borrar procesos
- cargar historicos
- hacer ajustes de administracion del modulo

entonces debe tener:

- `DoorAndDoor Process Manager`

## 4. Riesgo detectado actualmente

Aunque los menus principales del modulo si estan protegidos por grupo, hay un punto a vigilar:

- algunos botones tipo `Processes` en formularios de `sale.order`, `account.move`, `mrp.production` y `stock.picking` no tienen el atributo `groups` en todos los casos

Esto puede provocar que un usuario vea el boton por herencia de vista, pero al abrir la accion o el modelo relacionado termine en error si no tiene permisos suficientes.

## 5. Recomendacion tecnica

Para estabilizar la seguridad del modulo, conviene hacer una segunda pasada tecnica sobre `doorandoor_process_control` para:

- poner `groups="doorandoor_process_control.group_ddpc_user"` en todos los botones de acceso a procesos
- revisar botones `Crear proceso`
- revisar smart buttons `Processes`
- revisar acciones que abren `Cotizaciones`, `Prefacturas` y `Facturas`
- confirmar que ningun usuario vea accesos a objetos para los que no tenga permisos reales

## 6. Regla operativa recomendada

No asignar `DoorAndDoor Process User` solo.

Siempre asignarlo junto con el grupo funcional real del area:

- ventas
- facturacion
- manufactura
- inventario

Porque `Operaciones` solo orquesta y muestra trazabilidad; no sustituye la seguridad base de los documentos del negocio.

## 7. Lista rapida de asignacion

### Si el usuario trabaja en ventas

Asignar:

- `DoorAndDoor Process User`
- grupo de `Ventas`

### Si el usuario trabaja en facturacion

Asignar:

- `DoorAndDoor Process User`
- grupo de `Facturacion / Accounting`

### Si el usuario trabaja en manufactura

Asignar:

- `DoorAndDoor Process User`
- grupo de `Manufactura`

### Si el usuario trabaja en inventario

Asignar:

- `DoorAndDoor Process User`
- grupo de `Inventario`

### Si el usuario es gerente o controlador total

Asignar:

- `DoorAndDoor Process Manager`
- y los grupos base de las areas que necesita supervisar

## 8. Siguiente paso recomendado

Hacer una revision tecnica final de seguridad sobre:

- menus
- acciones
- botones visibles en formularios
- accesos a reportes y labels

para alinear completamente `lo que el usuario ve` con `lo que realmente puede abrir y ejecutar`.
