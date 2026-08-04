# Flujo de Asociacion Operativa de Controles Detectados

## Objetivo

Cerrar el caso real donde Contabilidad detecta un pago en Zelle, banco,
efectivo u otra via antes de saber con certeza a que factura pertenece.

## Flujo operativo aterrizado

1. Contabilidad crea o recibe un `Control de Cobros` sin factura.
2. Si ya conoce el cliente, lo registra.
3. Si tambien ve el pago en plataforma, puede crear o enlazar el pago
   contable.
4. Cuando logra identificar la factura correcta, usa el asistente
   `Asociar pago/factura`.
5. El asistente permite dejar enlazados:
   - cliente
   - factura
   - pago contable existente
   - nota de identificacion
6. El control puede quedar en `Pendiente` para continuar la revision.
7. Luego Contabilidad pasa a `Revisar` y finalmente `Validar`.
8. En la validacion se reconcilia el pago con la factura y la factura
   refleja pago parcial o pago total segun corresponda.

## Beneficio operativo

- Se evita obligar a conocer la factura desde el primer minuto.
- Se permite capturar dinero detectado en tiempo real.
- La asociacion posterior queda trazada dentro del mismo control.
- La UI ofrece un camino funcional, no tecnico, para completar el
  matching.
