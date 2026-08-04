# Tablero Base de Pagos

Fecha: 2026-08-02
Modulo: `doorandoor_tableros`

## Objetivo

Crear un modulo propio para concentrar los tableros de DoorAndDoor sin
seguir cargando esta logica en modulos operativos.

## Primera entrega

El modulo arranca con un tablero base de pagos alimentado desde
`doorandoor_control_cobros`.

### Filtros incluidos

- tipo de fecha a analizar
- desde
- hasta
- diarios
- clientes
- vendedores

### KPIs iniciales

- cantidad de controles
- cantidad de pagos enlazados
- pendientes
- validados
- rechazados
- pagos por identificar
- monto reportado
- monto validado
- monto rechazado

### Rankings iniciales

- cliente con mas pagos
- cliente con mayor monto
- diario con mas pagos
- diario con mayor monto

### Detalle embebido en el tablero

- lista de controles filtrados
- lista de pagos enlazados
- lista de facturas vinculadas

Con esto el tablero ya no funciona solo como resumen, sino tambien como
pantalla base de consulta para cobros y pagos.

## Evolucion prevista

En futuras versiones este mismo modulo debe concentrar:

- tableros ejecutivos
- tableros por ventas
- tableros por contabilidad
- graficos avanzados
- widgets por estado
- filtros rapidos adicionales
- exportacion o PDF de tableros
