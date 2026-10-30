# Clover Ecommerce para DoorAndDoor

Este módulo integra cobros con tarjeta mediante **Clover Ecommerce Hosted iFrame + API**.
El vendedor inicia el cobro desde la factura de Odoo; Clover muestra los campos seguros
de tarjeta y Odoo recibe solamente un token de un uso. Odoo nunca debe almacenar PAN,
fecha de vencimiento ni CVC.

Documentos:

- [Configuración Sandbox](CONFIGURACION_SANDBOX.md)
- [Flujo Operativo](FLUJO_OPERATIVO.md)
- [Guía de Pruebas](GUIA_PRUEBAS.md)
- [Seguridad y Despliegue](SEGURIDAD_Y_DESPLIEGUE.md)

Referencias oficiales:

- https://docs.clover.com/dev/docs/using-the-clover-hosted-iframe
- https://docs.clover.com/dev/docs/ecommerce-api-payments-flow
- https://docs.clover.com/dev/docs/create-a-charge
