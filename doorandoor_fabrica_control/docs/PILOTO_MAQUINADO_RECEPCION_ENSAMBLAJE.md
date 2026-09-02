# Piloto persistente Maquinado → Recepción → Ensamblaje

## Objetivo

Validar el control nativo de Odoo entre Maquinado y Ensamblaje sin crear un
tercer centro físico ni movimientos de inventario que dupliquen el trabajo en
proceso.

## Documentos locales creados

| Etapa | Documento |
|---|---|
| Venta | `S00147` |
| Pedido técnico generado por la factura | `S00148` |
| Factura | `INV/2026/00113` |
| Pago | Pago contable ID `128` |
| Necesidad | `NEC/2026/00009` |
| Plan diario | `PLAN/2026/0005` |
| Orden de fabricación | `WH/MO/00023` |

Producto: `[DDFC-HANDOFF-DOOR] Puerta piloto Maquinado a Ensamblaje`.
Cantidad: 2 unidades. Factura pagada y vinculada como documento origen.

La personalización comercial existente genera además `S00148` como pedido
técnico enlazado desde la factura. No es una venta duplicada manualmente: la
venta demostrativa original y que debe abrirse primero es `S00147`.

## Centros y operaciones

Solo existen dos centros de trabajo:

1. **Maquinado** (`DDFC-MAQ`).
2. **Ensamblaje** (`DDFC-ENS`).

La LdM contiene tres operaciones dependientes:

1. **Maquinado**, ejecutada en Maquinado.
2. **Recepción desde Maquinado**, ejecutada en Ensamblaje y bloqueada por
   Maquinado.
3. **Ensamblaje**, ejecutada en Ensamblaje y bloqueada por la recepción.

Finalizar Maquinado representa la salida del primer punto. Validar Recepción
desde Maquinado representa la entrada y aceptación por Ensamblaje. La operación
Ensamblaje no queda disponible antes de completar esa recepción.

## Recorrido para revisar

1. Abrir **Ventas → Pedidos → Pedidos** y localizar `S00147`.
2. Desde la venta abrir la factura `INV/2026/00113` y comprobar estado pagado.
3. Abrir **Fabricación → Reportes DoorAndDoor → Necesidades por almacén** y
   localizar `NEC/2026/00009`.
4. Abrir **Fabricación → Reportes DoorAndDoor → Plan general diario** y localizar
   `PLAN/2026/0005`.
5. Desde el plan abrir la OF `WH/MO/00023`.
6. Revisar la pestaña **Órdenes de trabajo**:
   - Maquinado;
   - Recepción desde Maquinado;
   - Ensamblaje.
7. Comprobar que Recepción y Ensamblaje se muestran bloqueadas por sus
   operaciones anteriores.

La OF se deja sin completar para poder realizar la demostración desde Shop
Floor. Maquinado aparece esperando disponibilidad de componentes; no se han
consumido materiales ni validado movimientos físicos automáticamente.

## Vale de entrega de Maquinado a Ensamblaje

Desde la OF se utiliza el botón inteligente **Maquinado → Ensamblaje** para
crear uno o varios vales parciales. Cada vale sigue este recorrido:

1. Seleccionar las operaciones **Maquinado** y **Recepción desde Maquinado**.
2. Detallar las partes o productos, cantidades entregadas y rechazos detectados
   antes de la salida.
3. Pulsar **Confirmar salida de Maquinado**. El sistema registra usuario, fecha
   y hora y no permite continuar si falta el documento origen de la OF.
4. Ensamblaje registra por cada línea la cantidad aceptada y la rechazada. La
   suma debe coincidir exactamente con lo entregado por Maquinado.
5. Pulsar **Confirmar recepción en Ensamblaje** para registrar al receptor,
   fecha y hora.
6. Imprimir el **Vale Maquinado a Ensamblaje**, que incluye firmas y toda la
   trazabilidad.

El origen se muestra obligatoriamente como uno de estos dos casos:

- **Factura de venta:** imprime la factura vinculada a la necesidad y a la OF.
- **OF por reposición de stock:** imprime la propia OF como documento de
  fabricación para reposición y, adicionalmente, la solicitud o transferencia
  que justificó reponer el inventario.

El vale es un control operativo y no crea movimientos de inventario entre dos
ubicaciones ficticias. Las entregas parciales quedan como registros separados
y auditables dentro de la misma OF.

## Repetibilidad

El script `scripts/create_persistent_sale_handoff_flow.py` usa la referencia
`DDFC-FLUJO-COMPLETO-MAQ-ENS-20260830`. Si se ejecuta nuevamente, muestra los
documentos ya existentes y no duplica la operación.
