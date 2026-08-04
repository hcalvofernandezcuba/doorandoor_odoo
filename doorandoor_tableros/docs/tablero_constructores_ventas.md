# Tablero de constructores y ventas

## Objetivo

Llevar a `Tableros / Ventas` una lectura rapida de la relacion entre:

- clientes asociados a constructores
- constructores o instaladores activos
- ventas reales vinculadas a esos constructores
- vendedores que mas facturan dentro de esa red comercial

## Base tecnica

- El dato maestro vive en `doorandoor_ficha_cliente`
- `res.partner` guarda el `constructor asociado`
- `sale.order` recibe el mismo dato como campo relacionado almacenado
- `doorandoor_tableros` consume ambas fuentes en un dashboard nativo

## Primera entrega visual

- `Clientes por constructor`
- `Ventas por constructor`
- `Monto vendido por fecha`
- `Vendedores por monto vendido`
- `Constructores por estado`
- `Cantidad de ventas por constructor`

## Filtros superiores

- periodo manual desde / hasta
- constructor
- vendedor
- estado

## Evolucion natural

Luego podemos crecer este tablero con:

- ventas por ciudad o mercado del constructor
- tickets promedio por constructor
- garantias o incidencias por constructor
- conversion de cotizacion a venta por red de instaladores
