# Seguridad y Despliegue

## Datos de tarjeta

- Los campos sensibles pertenecen al iframe de Clover.
- No registrar en logs, chatter, adjuntos ni base de datos: PAN, CVC, fecha de
  vencimiento o token de tarjeta.
- La clave pública puede llegar al navegador para inicializar el iframe; la clave
  privada permanece exclusivamente en el servidor Odoo.
- Las operaciones financieras usan una clave de idempotencia única.

## Sandbox y producción

| Entorno | Credenciales | Estado Odoo | Uso |
| --- | --- | --- | --- |
| Local | Sandbox | Modo de prueba | Desarrollo y validación técnica. |
| Pruebas | Sandbox | Modo de prueba | QA con Gerencia. |
| Gestión | Producción | Activado | Solo tras aprobación escrita y ventana de mantenimiento. |

Nunca sincronizar parámetros, tokens, filestore, PostgreSQL ni secretos entre estos
entornos. El código se despliega selectivamente y las credenciales se cargan de forma
manual en cada instancia.

## Orden de despliegue

1. Validar localmente la matriz de pruebas.
2. Crear respaldo de addons en Pruebas.
3. Sincronizar solo `doorandoor_clover_payment` y sus dependencias modificadas.
4. Verificar hashes, actualizar el módulo y pedir a SRE el reinicio del servicio web
   de Pruebas si es necesario.
5. Cargar solo las credenciales sandbox de Pruebas y ejecutar QA con Gerencia.
6. Desplegar en Gestión únicamente tras aprobación explícita, con ventana de
   mantenimiento confirmada, respaldo y credenciales de producción distintas.
7. Confirmar HTTP, logs, proveedor, diario CLVR y una transacción controlada antes de
   declarar el flujo operativo.
