# Ficha de cliente con constructor asociado

## Objetivo

Separar el comprador del actor que realmente instala o ejecuta la obra.
Con esto DoorAndDoor gana una referencia cruzada util para marketing,
garantias, postventa y seguimiento comercial.

## Logica inicial aplicada

- Se crea un catalogo propio de `constructores / instaladores`.
- Cada contacto cliente puede apuntar a un `constructor asociado`.
- El constructor no necesita ser quien compra.
- Un mismo constructor puede quedar vinculado a varios clientes.
- La relacion inicial es `muchos clientes -> un constructor`.

## Beneficios operativos

- Permite identificar que clientes llegaron o trabajan con un mismo
  constructor.
- Facilita futuras campanas de marketing por instalador o aliado.
- Ayuda a rastrear garantias comerciales por red de instalacion.
- Deja la base lista para despues asociar ventas, facturas o proyectos al
  mismo constructor si el negocio lo pide.

## Entrega tecnica inicial

- Modelo nuevo `ddfc.builder.profile`
- Campo `ddfc_builder_id` en `res.partner`
- Menu en `Contactos / Constructores`
- Reporte base `Clientes por constructor`
- Vista grafica de barras y vista pivote para analisis

## Evolucion prevista

Si mas adelante el negocio lo necesita, esta base puede crecer hacia:

- varios constructores por cliente
- constructor principal y secundarios por proyecto
- asociacion directa del constructor en ventas o facturas
- indicadores por constructor dentro de tableros
