# Flujo Operativo Completo - Pagos Detectados, por Identificar y Conciliacion Posterior

Fecha: 2026-08-02
Modulo: `doorandoor_control_cobros`

## Objetivo

Documentar el flujo operativo real para los casos en que:

- contabilidad o control de cobros detecta un pago antes de conocer la factura correcta
- el pago puede haberse hecho por varias vias
- el pagante no informa bien la referencia
- la identificacion correcta llega despues por canales manuales
- el pago debe registrarse primero y conciliarse despues

## Escenario real del negocio

La controladora de pagos puede ver entrar un pago en:

- Zelle
- transferencia
- banco
- pasarela
- efectivo

Y en ese momento puede no saber:

- de que factura es
- quien pago exactamente
- si corresponde a un cliente con varias facturas abiertas
- si es pago total o parcial

Ese pago no debe perderse por falta de informacion inicial.

## Regla funcional

Si el pago se detecta, debe poder registrarse aunque no tenga factura identificada aun.

## Flujo completo recomendado

### Etapa 1. Pago detectado

La controladora ve un ingreso real en la plataforma o en el banco.

Accion esperada:

- crear un control de cobro
- registrar monto
- registrar diario o via
- registrar referencia observada
- registrar notas de identificacion

Opcionalmente:

- crear tambien el `account.payment` desde ese momento

Resultado:

- el dinero queda capturado operativamente
- aun no afecta una factura especifica

### Etapa 2. Pago por identificar

El control queda en bandeja de identificacion.

Caracteristicas:

- puede no tener factura
- puede no tener cliente confirmado
- puede ya tener `payment_id` contable
- no debe cerrar ninguna factura
- no debe conciliarse todavia

Resultado:

- contabilidad no pierde el rastro del dinero recibido

### Etapa 3. Pago identificado

Por llamadas, WhatsApp, ventas, correo o revision manual se identifica:

- el cliente
- la factura
- o ambas cosas

Accion esperada:

- asociar el control a la factura correcta
- si el pago contable ya existe, enlazarlo
- si no existe, crearlo o ubicarlo

Resultado:

- el control ya queda listo para revision final

### Etapa 4. Revision contable

La controladora revisa:

- monto
- referencia
- diario
- cliente
- coincidencia con la factura

Si cuadra:

- pasa a validacion

Si no cuadra:

- permanece en revision
- o pasa a rechazado

### Etapa 5. Conciliacion

Cuando ya existe:

- factura correcta
- pago contable correcto

Accion esperada:

- conciliar el pago contra la factura

Resultado:

- el residual de la factura baja
- los totales pendientes se actualizan
- contabilidad ve el movimiento correcto en LM

### Etapa 6. Cierre parcial o total

Si el pago cubre todo:

- factura pagada

Si cubre solo una parte:

- factura pagada parcialmente

Si quedan otros pagos pendientes:

- la factura sigue en revision o parcial segun corresponda

## Casos que este flujo cubre

### Caso A. Pago visto antes que la factura

- se crea control sin factura
- se crea o enlaza pago contable
- luego se identifica factura
- despues se concilia

### Caso B. Cliente pago mal identificado

- el cliente no puso numero de factura
- el pago entra
- la controladora lo retiene en `Por identificar`
- luego lo asocia por comunicacion manual

### Caso C. Factura pagada por varias vias

- un control por cada evidencia de pago
- cada tramo se revisa separado
- la factura cierra por suma conciliada

### Caso D. Pago parcial detectado primero

- se registra el pago parcial
- se identifica factura despues
- se concilia parcialmente
- la factura queda parcial

## Regla contable clave

Registrar el pago y conciliarlo son dos momentos diferentes.

Se puede:

- crear el `account.payment` primero
- y aplicarlo a la factura despues

Eso es correcto cuando el dinero ya entro, pero aun no se ha identificado completamente su destino.

## Estados operativos sugeridos

Para el control:

- `Detectado`
- `Por identificar`
- `Identificado`
- `En revision`
- `Validado`
- `Rechazado`

Si no se quieren tantos estados, la implementacion minima puede usar:

- control sin factura
- estado de asociacion
- filtros operativos

## Botones operativos sugeridos

- `Crear pago`
- `Marcar por identificar`
- `Asociar cliente`
- `Asociar factura`
- `Asociar pago contable`
- `Conciliar`
- `Validar`
- `Rechazar`

## Regla final

El sistema debe permitir:

- detectar el pago primero
- registrar el pago despues o al mismo tiempo
- identificar la factura despues
- conciliar despues

Ese es el flujo correcto para la operacion real.
