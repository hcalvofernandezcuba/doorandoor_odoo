# DoorAndDoor Sales New - Diseno Tecnico Base para Control de Procesos

Fecha de corte documental: 2026-07-26

## Objetivo

Definir la base tecnica y funcional de un futuro modulo de `control de procesos` que permita visualizar y operar en una sola capa la trazabilidad de:

- ventas
- facturas
- pagos
- manufactura
- movimientos internos
- despachos
- entregas

La meta es que cada actor vea sus tareas del dia, que gerencia vea el flujo completo con tiempos de cambio de estado y que el sistema pueda disparar acciones, labels y notificaciones desde una vista operativa central.

## Problema que se quiere resolver

Actualmente el flujo existe en varios documentos y modulos:

- `sale.order`
- `account.move`
- `mrp.production`
- `stock.picking`
- ordenes de recogida o entrega

Pero no existe una vista unificada para responder rapidamente estas preguntas:

- que venta disparo el proceso
- que factura esta ligada
- si existe pago parcial o total
- si ya se creo la `MO`
- si la `MO` esta pendiente, iniciada o terminada
- si ya existe movimiento interno
- si ya existe orden de despacho
- quien tiene la responsabilidad actual
- que tarea falta por ejecutar
- cuanto tiempo lleva cada fase

## Resultado esperado del futuro modulo

El futuro modulo, propuesto como `doorandoor_process_control`, debe permitir:

- ver el estado general de cada proceso en una sola vista
- crear una lista de tareas por rol y por dia
- abrir desde cada tarea el documento operativo correcto
- imprimir labels asociados a la tarea
- registrar la hora de cada cambio de estado
- notificar cuando una tarea se termina
- dar visibilidad gerencial completa del flujo

## Actores operativos

### 1. Ventas

Responsabilidades principales:

- crear la venta
- definir direccion de entrega
- confirmar datos comerciales del pedido
- dar seguimiento a pedidos del cliente

Necesita ver:

- ventas pendientes de pago
- ventas liberadas para fabricacion
- ventas listas para despacho
- cambios o incidencias del cliente

### 2. Facturacion / Caja

Responsabilidades principales:

- emitir prefactura o factura
- registrar pagos
- liberar el proceso segun las reglas de pago

Necesita ver:

- facturas pendientes de pago
- facturas con pago parcial
- facturas con pago total
- documentos listos para activar fabricacion o despacho

### 3. Manufactura

Responsabilidades principales:

- revisar ordenes de manufactura creadas
- iniciar produccion
- imprimir labels de produccion
- terminar produccion
- reportar incidencias de fabricacion

Necesita ver:

- `MO` por iniciar
- `MO` en proceso
- `MO` terminadas pendientes de traslado
- labels asociados a la produccion

### 4. Almacen / Inventario

Responsabilidades principales:

- controlar movimientos internos
- preparar despacho
- validar salida al cliente
- controlar entrega o recogida

Necesita ver:

- transferencias internas pendientes
- pickings pendientes de preparar
- pickings listos para validar
- entregas pendientes de cierre

### 5. Control de procesos

Responsabilidades principales:

- monitorear el flujo punta a punta
- detectar cuellos de botella
- reasignar o escalar tareas
- verificar que no existan documentos trabados

Necesita ver:

- todos los procesos activos
- responsable actual
- tiempo transcurrido por estado
- alertas o bloqueos

### 6. Gerencia

Responsabilidades principales:

- revisar trazabilidad
- medir tiempos de respuesta
- controlar cumplimiento de flujo
- detectar demoras o procesos incompletos

Necesita ver:

- tablero completo
- tareas por area
- fecha y hora de cada cambio de estado
- usuario responsable de cada accion

## Concepto tecnico central

Se propone crear una capa nueva de seguimiento operativo por encima de los documentos actuales.

En lugar de depender solo de vistas separadas por modulo, el sistema debe manejar una entidad central del proceso.

Modelo sugerido:

- `ddpc.process.flow`
  - representa el proceso completo de una venta o necesidad operativa

- `ddpc.process.task`
  - representa cada tarea operativa concreta dentro del proceso

## Estructura sugerida del proceso

Cada `process.flow` debe poder referenciar:

- `sale.order`
- `account.move`
- `mrp.production`
- `stock.picking`
- orden de recogida o entrega
- cliente
- usuario responsable actual
- estado global
- prioridad

Cada `process.task` debe poder referenciar:

- proceso padre
- tipo de tarea
- documento operativo asociado
- area responsable
- usuario asignado
- estado de la tarea
- fecha y hora de creacion
- fecha y hora de inicio
- fecha y hora de cierre
- observaciones o incidencias

## Tipos de tareas iniciales

Lista inicial propuesta:

- revisar venta
- confirmar direccion de entrega
- revisar pago
- liberar fabricacion
- liberar despacho
- iniciar manufactura
- imprimir label de produccion
- terminar manufactura
- crear transferencia interna
- validar transferencia interna
- preparar picking
- imprimir label documental
- validar despacho
- registrar entrega
- cerrar proceso

## Estados sugeridos para cada tarea

Estados base:

- `draft`
- `pending`
- `ready`
- `in_progress`
- `waiting_dependency`
- `done`
- `cancelled`
- `blocked`

## Estados sugeridos del flujo general

Estados base del `process.flow`:

- `new`
- `awaiting_payment`
- `released_for_mrp`
- `in_manufacturing`
- `awaiting_internal_transfer`
- `awaiting_dispatch`
- `out_for_delivery`
- `delivered`
- `closed`
- `blocked`

## Reglas de generacion de tareas

### Caso base: venta que termina en fabricacion y despacho

1. Se crea la venta.
2. Se crea o publica la factura.
3. Se registra el pago.
4. Si el producto requiere fabricacion, se crea la tarea `iniciar manufactura`.
5. Si aplica label de produccion, se crea o habilita la tarea `imprimir label de produccion`.
6. Al terminar la `MO`, se crea la tarea de `transferencia interna` si aplica.
7. Al quedar disponible el producto, se crea la tarea `preparar picking`.
8. Luego se crea o habilita la tarea `validar despacho`.
9. Finalmente se crea la tarea `registrar entrega` o `confirmar recogida`.
10. Al completarse todas las tareas, el proceso se cierra.

## Dependencias entre tareas

Debe existir control de dependencias para evitar acciones fuera de secuencia.

Ejemplos:

- no se puede `iniciar manufactura` si la venta no fue liberada por pago
- no se puede `validar despacho` si la fabricacion no esta terminada
- no se puede `cerrar proceso` si hay picking pendiente

## Vistas necesarias

### 1. Vista central de procesos

Objetivo:

- ver todos los procesos activos y su estado general

Campos visibles sugeridos:

- referencia del proceso
- venta
- factura
- cliente
- estado general
- responsable actual
- documento actual
- prioridad
- fecha de creacion
- tiempo en estado actual

### 2. Vista de tareas del dia por rol

Objetivo:

- que cada actor vea solo las tareas accionables de hoy

Campos visibles sugeridos:

- tarea
- proceso
- documento asociado
- cliente
- prioridad
- estado
- hora de creacion
- tiempo pendiente

### 3. Vista gerencial

Objetivo:

- mostrar trazabilidad completa y tiempos por cambio de estado

Campos visibles sugeridos:

- proceso
- estado actual
- usuario actual
- fecha/hora de creacion
- fecha/hora de inicio por etapa
- fecha/hora de cierre por etapa
- duracion por etapa
- alertas

## Acciones requeridas dentro de cada tarea

Cada tarea debe tener botones o accesos directos a:

- abrir venta
- abrir factura
- abrir `MO`
- abrir picking
- abrir orden de entrega o recogida
- imprimir labels asociados
- marcar tarea iniciada
- marcar tarea terminada
- registrar incidencia

## Labels asociados al proceso

El modulo debe integrarse con los labels ya construidos, sin duplicar logica.

Escenarios iniciales:

- label de producto
- label de factura
- label de fabricacion

Regla funcional:

- el usuario debe poder imprimir el label correspondiente desde la tarea adecuada
- en manufactura, el label puede imprimirse al iniciar o al terminar la tarea segun necesidad operativa

## Notificaciones

Al completar una tarea, el sistema debe poder notificar:

- por mensaje interno de Odoo
- y opcionalmente por email

La notificacion debe incluir:

- proceso relacionado
- documento asociado
- tarea completada
- usuario que la completo
- fecha y hora
- resumen corto del resultado

## Registro de tiempos y auditoria

Cada cambio de estado debe guardar como minimo:

- estado anterior
- estado nuevo
- usuario que hizo el cambio
- fecha y hora exacta
- observacion opcional

Esto es obligatorio para la vista gerencial.

## Reglas de visibilidad por rol

Principio general:

- cada usuario operativo ve sus tareas
- control de procesos ve todos los procesos activos
- gerencia ve todos los procesos y todos los tiempos

La visibilidad debe basarse en:

- grupos de seguridad
- rol operativo
- compania
- area responsable

## Primera fase recomendada

Para reducir riesgo, la primera fase del modulo deberia cubrir solo:

- vista central de procesos
- tareas basicas por rol
- vinculacion con venta, factura, `MO` y picking
- botones de apertura de documentos
- impresion de labels ya existentes
- timestamps de cambio de estado

No es recomendable en la primera fase incluir:

- automatizaciones complejas de email
- reasignaciones avanzadas
- SLA automaticos
- tablero grafico complejo

## Riesgos y puntos a definir despues

Quedan pendientes de definicion funcional:

- que evento exacto crea cada tarea
- si una tarea puede reasignarse manualmente
- si habra prioridades automaticas
- si las notificaciones por email seran siempre o solo en algunos cierres
- si gerencia vera una sola vista transversal o vistas por modulo con extension gerencial

## Siguiente paso recomendado

A partir de este documento, el siguiente nivel de definicion debe cerrar:

1. listado final de actores
2. listado final de tareas
3. disparadores por tarea
4. estados permitidos por tarea
5. acciones visibles por rol
6. puntos de notificacion
7. campos exactos de la vista gerencial

## Fase 2 - Actores, tareas y disparadores base

Esta seccion consolida la primera capa operativa real del futuro modulo `doorandoor_process_control`.

## Actores definitivos propuestos

### 1. Ventas

Rol principal:

- crear la venta
- definir o confirmar direccion de entrega
- dar seguimiento comercial al pedido

### 2. Facturacion / Caja

Rol principal:

- emitir prefactura o factura
- registrar pagos
- liberar fabricacion o despacho segun reglas de negocio

### 3. Manufactura

Rol principal:

- iniciar produccion
- imprimir labels de produccion
- cerrar ordenes de manufactura

### 4. Almacen / Inventario

Rol principal:

- validar transferencias internas
- preparar pickings
- validar despacho
- registrar entrega o recogida

### 5. Control de procesos

Rol principal:

- monitorear el flujo completo
- detectar cuellos de botella
- verificar que las tareas caigan en la cola correcta

### 6. Gerencia

Rol principal:

- consultar la trazabilidad total
- revisar tiempos por etapa
- supervisar desempeno operativo y bloqueos

## Tareas iniciales del sistema

Se propone que la primera fase del modulo trabaje con este conjunto inicial de tareas:

- `revisar_venta`
- `confirmar_direccion_entrega`
- `emitir_prefactura_o_factura`
- `registrar_pago`
- `liberar_fabricacion`
- `liberar_despacho`
- `iniciar_manufactura`
- `imprimir_label_produccion`
- `cerrar_manufactura`
- `crear_transferencia_interna`
- `validar_transferencia_interna`
- `preparar_picking`
- `imprimir_label_factura`
- `validar_despacho`
- `registrar_entrega`
- `cerrar_proceso`

## Disparadores iniciales por tarea

### `revisar_venta`

Se crea cuando nace una nueva venta que entra al flujo operativo.

### `confirmar_direccion_entrega`

Se activa cuando la venta requiere confirmar o ajustar la direccion final de entrega.

### `emitir_prefactura_o_factura`

Se activa cuando la venta pasa a su fase documental.

### `registrar_pago`

Se activa cuando existe factura o prefactura pendiente de pago o de validacion de pago.

### `liberar_fabricacion`

Se activa cuando:

- el pago cumple la regla de liberacion para fabricar
- existe al menos un producto fabricable en el documento

### `liberar_despacho`

Se activa cuando el pago cumple la regla definida para permitir despacho.

### `iniciar_manufactura`

Se activa cuando ya existe una `MO` creada y pendiente de inicio.

### `imprimir_label_produccion`

Se activa cuando la operacion de manufactura requiere imprimir labels de produccion.

Regla inicial sugerida:

- puede ejecutarse al inicio de la tarea de manufactura
- o al cierre de la `MO`
- segun la necesidad operativa final del cliente

### `cerrar_manufactura`

Se activa cuando la orden de manufactura ya fue iniciada y necesita cierre operativo.

### `crear_transferencia_interna`

Se activa cuando la produccion termina y el producto debe moverse a otro almacen antes del despacho.

### `validar_transferencia_interna`

Se activa cuando la transferencia interna ya existe y esta pendiente de validacion.

### `preparar_picking`

Se activa cuando el producto ya esta disponible para salida y debe prepararse el despacho.

### `imprimir_label_factura`

Se activa cuando el flujo documental o de despacho requiere labels asociados a la factura.

### `validar_despacho`

Se activa cuando el picking de salida esta listo para validarse.

### `registrar_entrega`

Se activa cuando el producto ya salio y falta cerrar la entrega o recogida.

### `cerrar_proceso`

Se activa cuando todas las tareas previas obligatorias estan completas y el flujo puede cerrarse.

## Regla operativa general

Cada proceso no tiene por que usar todas las tareas.

La generacion de tareas debe depender de:

- si el producto es fabricable o no
- si requiere traslado interno o no
- si requiere despacho o recogida
- si requiere labels o no
- si la etapa de pago ya habilito fabricacion, despacho o ambas

## Resultado esperado de esta fase

Al cerrar esta fase del diseno debe quedar claro:

- quienes participan en el flujo
- que tareas existen
- cuando nace cada tarea
- que tareas son opcionales y cuales obligatorias

## Fase 3 - Estados simplificados y acciones por rol

Para esta primera version del modulo se define una logica de estados simple y comun para facilitar operacion, supervision y entrenamiento del personal.

## Estados operativos definitivos

Se trabajara con estos cinco estados base:

- `iniciado`
- `en_proceso`
- `entregado`
- `en_ruta`
- `cerrado`

Tambien puede entenderse `cerrado` como `terminado` a nivel funcional, pero tecnicamente conviene manejar un solo valor final para evitar duplicidad de criterio.

## Significado de cada estado

### `iniciado`

La tarea o proceso ya existe y fue activado formalmente dentro del sistema, pero aun no ha avanzado a ejecucion operativa real.

Ejemplos:

- una `MO` fue creada pero aun no comenzo
- un picking fue generado pero aun no se esta preparando
- una tarea de control fue asignada pero aun no la estan trabajando

### `en_proceso`

La tarea o proceso ya esta siendo ejecutado por el area responsable.

Ejemplos:

- manufactura ya comenzo la orden
- almacen ya esta preparando el picking
- control de procesos ya esta gestionando una incidencia

### `entregado`

La tarea fue completada por el actor responsable y pasa a la siguiente etapa o area.

Este estado no significa necesariamente entrega al cliente en todos los casos.
Significa que la etapa actual fue entregada al siguiente actor del flujo.

Ejemplos:

- manufactura termina la produccion y entrega el producto a almacen
- control de inventario valida una transferencia y la deja disponible para despacho
- picking queda listo para que delivery ejecute la salida final

### `cerrado`

Es el estado final del proceso.

Solo debe usarse cuando el proceso completo ya fue concluido, lo cual en la mayoria de los casos ocurre cuando:

- el producto fue despachado
- se registro la entrega al cliente
- o se cerro formalmente la recogida / delivery

Regla clave:

- `cerrado` no lo debe marcar manufactura
- `cerrado` no lo debe marcar almacen interno en una etapa intermedia
- `cerrado` lo marca el cierre real del flujo hacia el cliente

### `en_ruta`

Este estado se usara especificamente para delivery o despacho final cuando la mercancia ya salio del punto de entrega y esta camino al cliente.

Objetivo de este estado:

- evitar que `entregado` signifique dos cosas distintas
- dar visibilidad real de que el producto ya salio, pero aun no fue recibido por el cliente
- permitir a gerencia y control de procesos distinguir entre `listo para entrega` y `entrega efectivamente cerrada`

Interpretacion:

- `entregado` en etapas intermedias significa que una area ya entrego su parte a la siguiente
- `en_ruta` significa que delivery ya salio con la mercancia
- `cerrado` significa que el cliente ya recibio o se cerro formalmente la entrega

## Regla de transicion general

La secuencia base esperada es:

- `iniciado -> en_proceso -> entregado -> en_ruta -> cerrado`

No todas las tareas necesitan llegar individualmente a `cerrado`.

En muchas tareas intermedias, el flujo natural sera:

- `iniciado -> en_proceso -> entregado`

Y el estado `cerrado` quedara reservado principalmente para:

- el proceso general
- la tarea final de entrega
- o tareas administrativas que concluyen el ciclo completo

El estado `en_ruta` solo debe aparecer en tareas o procesos donde exista entrega fisica al cliente.

## Ejemplo operativo por actor

### Manufactura

Comportamiento esperado:

- recibe la tarea en `iniciado`
- cuando comienza a trabajarla, la cambia a `en_proceso`
- cuando termina la fabricacion, la cambia a `entregado`

Interpretacion:

- manufactura no cierra el proceso total
- manufactura entrega el resultado a la siguiente area

### Almacen / Inventario

Comportamiento esperado:

- recibe transferencia, picking o preparacion en `iniciado`
- cuando comienza a preparar o validar, cambia a `en_proceso`
- cuando deja lista la salida o el despacho, cambia a `entregado`

### Delivery / Despacho final

Comportamiento esperado:

- recibe la salida pendiente en `iniciado`
- al comenzar la operacion la pasa a `en_proceso`
- cuando la mercancia sale hacia el cliente, la pasa a `en_ruta`
- cuando se confirma la entrega al cliente, la pasa a `cerrado`

Este es el punto donde normalmente se cierra el proceso general.

## Acciones permitidas por rol

Las acciones no deben ser identicas para todos los usuarios.
Cada rol debe ver solo las acciones logicas segun su parte del flujo.

## Ventas

Acciones sugeridas:

- abrir venta
- confirmar direccion de entrega
- revisar estado del proceso
- consultar incidencia

No deberia poder:

- cerrar manufactura
- validar picking
- cerrar entrega final

## Facturacion / Caja

Acciones sugeridas:

- abrir prefactura o factura
- registrar pago
- revisar liberacion de fabricacion
- revisar liberacion de despacho
- imprimir labels documentales si aplica

## Manufactura

Acciones sugeridas:

- abrir `MO`
- cambiar estado a `en_proceso`
- imprimir label de produccion
- marcar la produccion como `entregado`
- registrar observaciones de fabricacion

## Almacen / Inventario

Acciones sugeridas:

- abrir transferencia interna
- validar transferencia
- abrir picking
- preparar picking
- validar despacho
- imprimir labels asociados si aplica

## Control de procesos

Acciones sugeridas:

- ver todos los procesos
- abrir cualquier documento relacionado
- revisar tareas detenidas
- registrar incidencia
- reasignar seguimiento si en una fase futura se habilita esa opcion

## Gerencia

Acciones sugeridas:

- ver todas las vistas
- revisar tiempos de cambio de estado
- revisar historial por usuario
- consultar procesos cerrados, en proceso o demorados

Regla recomendada:

- gerencia debe tener visibilidad completa
- pero no necesariamente debe ejecutar acciones operativas del dia a dia

## Regla especial para labels

Los botones de labels deben aparecer solo donde tengan sentido operativo.

Ejemplos:

- manufactura puede imprimir labels de produccion al iniciar o al terminar
- facturacion puede imprimir labels documentales asociados a la factura
- almacen puede reimprimir labels si la operacion lo requiere

## Regla especial de cierre

El estado final del proceso no debe depender de que manufactura termine ni de que el picking exista.

El proceso solo debe considerarse `cerrado` cuando:

- la mercancia fue entregada al cliente
- o el delivery / despacho final fue formalmente concluido

## Nomenclatura legible recomendada en pantalla

Para que el usuario lo entienda rapido, se recomienda mostrar estos labels visibles:

- `Iniciado`
- `En proceso`
- `Entregado a siguiente área`
- `En camino al cliente`
- `Cerrado`

Si se quiere una version mas corta para badges o kanban:

- `Iniciado`
- `En proceso`
- `Entregado`
- `En ruta`
- `Cerrado`

Recomendacion practica:

- usar la version corta en listas y badges
- usar la version larga en tooltips, formularios o ayuda contextual

## Colores por estado

Se recomienda que cada estado tenga representacion visual por color para facilitar lectura rapida en listas, kanban y vistas gerenciales.

Estados visibles:

- `Iniciado`
- `En proceso`
- `Entregado`
- `En ruta`
- `Cerrado`

## Regla visual propuesta

La interfaz debe trabajar con una paleta compacta de tres colores base:

- `Rojo`
  - tarea atrasada
  - proceso bloqueado o fuera de tiempo esperado
- `Naranja`
  - tarea activa
  - proceso en curso
- `Verde`
  - tarea terminada
  - proceso completado en esa etapa

## Regla funcional importante

El color no debe depender solo del estado textual.
Debe depender tambien de la condicion real de la tarea:

- una tarea puede estar `Iniciada` y verse `Naranja`
- una tarea puede estar `En proceso` y verse `Roja` si ya va atrasada
- una tarea `Entregada` o `Cerrada` normalmente se vera `Verde`

Esto permite que la lectura sea simple y util para supervision real.

## Configuracion editable por gerencia

Se propone que la gerencia pueda modificar estos colores sin tocar codigo.

Eso implica una configuracion funcional dentro del modulo, por ejemplo:

- color para `Iniciado`
- color para `En proceso`
- color para `Entregado`
- color para `En ruta`
- color para `Cerrado`

## Alcance recomendado para la primera fase

Para no complicar la primera entrega, se recomienda:

- dejar colores por defecto definidos por el sistema
- permitir que gerencia los cambie desde configuracion
- aplicar esos colores en:
  - lista de tareas
  - vista central de procesos
  - vista gerencial

## Beneficio operativo

Esto ayuda a que:

- el usuario identifique rapido que debe atender
- control de procesos vea cuellos de botella visualmente
- gerencia detecte en segundos que esta arrancado, en trabajo, entregado o cerrado

## Tipo de vista por perfil

No todos los usuarios necesitan la misma experiencia visual.

## Vista gerencial

La vista principal de gerencia debe ser una `lista`.

Objetivo:

- leer muchos procesos rapidamente
- comparar estados, tiempos y responsables
- ordenar y filtrar por demoras, area o usuario

La lista gerencial debe mostrar como minimo:

- proceso
- cliente
- documento principal
- estado actual
- color semaforo
- responsable actual
- fecha y hora del ultimo cambio
- tiempo en estado actual

## Vistas operativas por rol

Para los equipos operativos se recomienda combinar:

- vista `kanban`
- vista `lista`

## Vista kanban operativa

La vista `kanban` debe ser la vista principal de trabajo para:

- manufactura
- almacen / inventario
- control de procesos
- delivery / despacho si aplica

Motivo:

- permite ver tareas por columna segun estado
- permite identificar acumulaciones rapidamente
- permite operar visualmente el flujo diario

## Transicion por arrastre

En las vistas `kanban` se propone permitir que el usuario pueda arrastrar tareas entre estados.

Ejemplo:

- de `Iniciado` a `En proceso`
- de `En proceso` a `Entregado`
- de `Entregado` a `En ruta`
- de `En ruta` a `Cerrado`

## Regla tecnica importante para drag and drop

El arrastre no debe ser libre sin validacion.

Cada cambio de columna debe:

- validar que el rol puede hacer esa transicion
- validar que la tarea tiene sus dependencias completas
- registrar usuario, fecha y hora
- disparar notificaciones si aplica

O sea:

- el `kanban` mueve visualmente la tarea
- pero el backend decide si el cambio es valido o no

## Vista lista operativa

Cada actor tambien debe tener una `vista lista` complementaria para:

- buscar rapido por cliente o documento
- ordenar por tiempo pendiente
- filtrar por prioridad
- revisar tareas vencidas

## Decision de diseno recomendada

Se propone entonces este esquema:

- `Gerencia`
  - vista principal: `lista`
- `Operativos`
  - vista principal: `kanban`
  - vista secundaria: `lista`

Esto deja el sistema legible para supervision y practico para ejecucion.

## Resultado esperado de esta fase

Con esta definicion debe quedar claro:

- que estados se usaran
- quien puede mover cada estado
- que significa `entregado` en una etapa intermedia
- que `en_ruta` representa la salida real hacia el cliente
- que el verdadero cierre ocurre al final del flujo hacia el cliente
