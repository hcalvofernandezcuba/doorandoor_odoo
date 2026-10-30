# Configuración Clover Sandbox

## Alcance

Esta configuración corresponde exclusivamente a desarrollo local y Pruebas. No se
copian tokens sandbox a Gestión ni se reutilizan credenciales de producción.

## Clover

1. Crear o abrir una aplicación en Clover Global Developer Dashboard con el selector
   **Sandbox** activo.
2. En `Requested Permissions`, habilitar solo `Payments: Read` y `Enable online payments`.
3. En `REST Configuration`, registrar:
   - Site URL: `https://pruebas.doorandoor.com`
   - Alternate Launch Path: `/payment/clover/oauth/callback`
   - CORS Domain: `https://pruebas.doorandoor.com`
   - OAuth response: `Code`
4. Abrir `Test Merchants` y seleccionar el merchant sandbox de DoorAndDoor.
5. En el Merchant Dashboard abrir `Settings > View all settings > Ecommerce API tokens`.
6. Crear el token de tipo **Hosted iFrame + API/SDK**.
7. Conservar de forma segura Merchant ID, clave pública Ecommerce y clave privada
   Ecommerce. Nunca enviarlos por chat, correo no cifrado, repositorio ni documentación.

## Odoo local

En `Facturación > Configuración > Proveedores de pago > Clover`:

- Estado: `Modo de prueba`.
- Entorno: `Sandbox`.
- Integración: `Formulario seguro integrado`.
- Merchant ID y claves Ecommerce: introducir directamente en Odoo.
- Simulador local: desmarcado para probar el iframe real.
- Diario: `Clover / CLVR`, nunca un diario bancario genérico.

El diario CLVR usa una cuenta transitoria conciliable `Clover - Fondos por liquidar`.
Los depósitos netos y comisiones del procesador se concilian posteriormente; no se
vuelven a confirmar los pagos de clientes al importar una liquidación.
