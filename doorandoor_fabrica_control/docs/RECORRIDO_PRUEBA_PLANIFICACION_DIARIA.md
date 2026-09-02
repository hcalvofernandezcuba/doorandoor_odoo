# Recorrido de prueba: planificación diaria de fabricación

## 1. Objetivo

Comprobar en DoorAndDoor local que las necesidades de diferentes almacenes
pueden consolidarse en un plan diario, convertirse en órdenes de fabricación y
generar una solicitud de partes y piezas sin descontar inventario antes de la
entrega física del almacén.

Base local: `pruebas`  
Módulo: `doorandoor_fabrica_control`  
Escenario preparado: `PLAN/2026/0001`

## 2. Condiciones de seguridad

- La prueba se realiza solamente en la instancia local.
- Los productos usan códigos `DDFC-*` y son exclusivos para pruebas.
- Consultar e imprimir no modifica existencias.
- Aprobar el plan crea OF confirmadas, pero no consume componentes.
- Solicitar materiales crea un traslado interno, pero no lo valida.
- No pulsar **Validar** en la transferencia hasta revisar físicamente el
  documento y acordar continuar con la prueba de inventario.

## 3. Acceso

1. Abrir el Odoo local.
2. Recargar completamente el navegador si el menú nuevo no aparece.
3. Entrar en **Fabricación → Reportes DoorAndDoor**.

El submenú debe mostrar:

- **Necesidades por almacén**.
- **Plan general diario**.

## 4. Revisar las necesidades por almacén

1. Abrir **Necesidades por almacén**.
2. Localizar las tres necesidades `NEC/2026/*` cuyo documento origen comienza
   con `DDFC-PLAN-`.
3. Comprobar:

| Almacén solicitante | Producto | Cantidad | Origen |
|---|---|---:|---|
| Orlando | `DDFC-VENTA-1L-3680` | 3 | Venta |
| Orlando | `DDFC-REPO-SOL-3680-ORL` | 4 | Reposición |
| Tampa Producción | `DDFC-VENTA-1L-3680` | 2 | Venta |

4. Verificar que las necesidades estén **Pendientes** antes de aprobar el plan.

## 5. Corte automático de medianoche

El plan normal no se genera manualmente durante el día. Una tarea revisa cada
quince minutos el cambio de fecha en `America/Havana` y crea, después de las
12:00 a. m., una fotografía de todas las necesidades elegibles antes del corte.

- El corte se ejecuta una sola vez por fecha y centro productor.
- Las necesidades posteriores quedan para el próximo día.
- El plan muestra fecha/hora del corte y usuario técnico.
- No se pueden agregar, eliminar ni cambiar peticiones después del corte.
- Producción solo puede modificar **Cantidad aprobada** y observaciones.

La acción manual **Generar corte de solicitudes** queda únicamente como
recuperación controlada si el plan no se creó automáticamente. Solo puede
ejecutarse una vez y produce el mismo bloqueo.

## 6. Revisar el plan diario

1. Abrir **Plan general diario**.
2. Entrar en `PLAN/2026/0001`.
3. Confirmar:

- Estado: **Borrador**.
- Centro de producción: **Tampa Producción**.
- Destino de materiales: **Preproducción**.
- Tres líneas en **Producciones por almacén**.

El producto `DDFC-VENTA-1L-3680` debe sumar cinco unidades entre Tampa y
Orlando. El producto `DDFC-REPO-SOL-3680-ORL` debe sumar cuatro unidades para
Orlando.

## 7. Validar la decisión del equipo de producción

Antes de aprobar, el equipo puede modificar **Cantidad aprobada** sin cambiar
la petición original.

Para reproducir la prueba técnica, conservar:

| Almacén | Producto | Solicitado | Aprobado |
|---|---|---:|---:|
| Tampa | Puerta 1 Lite 36×80 | 2 | 2 |
| Orlando | Puerta 1 Lite 36×80 | 3 | 3 |
| Orlando | Puerta sólida 36×80 | 4 | 4 |

1. Pulsar **Imprimir plan**.
2. Confirmar que el PDF separa las solicitudes por almacén.
3. Confirmar que el consolidado general muestra:
   - Puerta 1 Lite 36×80: 5 unidades.
   - Puerta sólida 36×80: 4 unidades.

## 8. Aprobar el plan y crear las OF

1. Pulsar **Aprobar plan y crear OF**.
2. El plan debe cambiar a **Aprobado**.
3. Deben aparecer tres OF, una por combinación de almacén y producto.
4. Las OF deben quedar **Confirmadas**, no terminadas.
5. Cada OF debe conservar:
   - plan diario de origen;
   - almacén solicitante;
   - producto y cantidad aprobada;
   - LdM y componentes correspondientes.

Pulsar nuevamente no debe crear OF duplicadas.

## 9. Revisar partes y piezas consolidadas

Abrir la pestaña **Partes y piezas**. Deben existir nueve componentes
consolidados:

| Parte o pieza | Cantidad esperada |
|---|---:|
| Perfil vertical de marco | 18 |
| Perfil horizontal de marco | 18 |
| Panel sólido | 9 |
| Vidrio de impacto | 5 |
| Bisagras | 27 |
| Cerraduras y manijas | 9 |
| Juegos de tornillos | 9 |
| Sellos perimetrales | 9 |
| Juegos de acabado | 9 |

El sistema debe mostrar también la disponibilidad en Tampa y cualquier
faltante. Los cálculos proceden de las LdM y admiten subconjuntos o LdM
anidadas.

## 10. Imprimir el requerimiento

1. Pulsar **Imprimir requerimiento**.
2. Verificar que el PDF muestre:
   - plan y fecha;
   - almacén de salida;
   - ubicación de producción receptora;
   - cantidades requeridas, disponibles y faltantes;
   - **Solicitar desde:** almacén y ubicación que preparan las piezas;
   - **Entregar a fábrica:** equipo de Producción y ubicación receptora;
   - usuario que imprime el documento;
   - espacios de firma para Producción y Almacén.

Imprimir el reporte no debe crear movimientos ni modificar inventario.

## 11. Solicitar la salida de materiales

1. Pulsar **Solicitar salida de materiales**.
2. Debe abrirse una transferencia interna con nueve movimientos.
3. Origen: existencias de Tampa.
4. Destino: Preproducción.
5. El traslado puede quedar confirmado o asignado según disponibilidad.
6. Comprobar que todavía no esté **Hecho**.

Pulsar nuevamente desde el plan debe abrir el mismo traslado y nunca crear un
duplicado.

Después de crear el traslado, usar **Imprimir vale de salida** desde el plan.
Este documento sustituye para la operación de fábrica al albarán genérico y
muestra origen, destinatario Fábrica/Producción, solicitante, usuario que
imprime, código de barras, partes y piezas y firmas de entrega/recepción.

## 12. Punto de detención obligatorio

Detener la prueba antes de validar la transferencia. En este momento deben
existir:

- tres necesidades trazables;
- un plan aprobado;
- tres OF confirmadas;
- nueve componentes consolidados;
- un único pedido de salida de materiales;
- ninguna reducción de existencias por entrega física.

La validación del traslado se hará en una segunda prueba controlada para
comprobar entrega parcial, faltantes y backorders.

## 13. Criterios para considerar viable el proceso

- Las cantidades por almacén coinciden con las solicitudes.
- El consolidado coincide con la suma de todos los almacenes.
- La explosión de LdM coincide con el cálculo manual.
- Producción puede modificar cantidades aprobadas antes de crear documentos.
- No aparecen OF ni solicitudes duplicadas.
- Consultar, aprobar e imprimir no consume inventario.
- La solicitud de materiales genera un solo traslado sin validarlo.
- Los responsables comprenden el recorrido sin pasos ambiguos.

## 14. Registro de observaciones

| Punto revisado | Resultado | Observaciones |
|---|---|---|
| Necesidades por almacén | Pendiente | |
| Consolidado diario | Pendiente | |
| Decisión de cantidades | Pendiente | |
| Creación de OF | Pendiente | |
| Cálculo de LdM | Pendiente | |
| PDF del plan | Pendiente | |
| PDF de materiales | Pendiente | |
| Pedido de salida | Pendiente | |
| Control de duplicados | Pendiente | |
| Inventario sin consumo anticipado | Pendiente | |

## 15. Decisión posterior

Solo después de completar esta tabla se decidirá:

1. ajustar el proceso local;
2. realizar la prueba de entrega física y backorder;
3. preparar respaldo y subida selectiva a pruebas.
