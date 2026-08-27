# Plantillas maestras de fabricación

## Objetivo

Las plantillas maestras permiten que un producto transformado reciba una LDM
completa de WINDOWS o DOORS sin codificar componentes ni operaciones en Python.

## Crear una plantilla maestra

1. Crear un producto técnico, por ejemplo `MASTER WINDOW SINGLE HUNG`.
2. Desactivar `Puede ser vendido` para que no aparezca comercialmente.
3. En la pestaña `Plantilla de fabricación`, marcar
   `Plantilla maestra de fabricación`.
4. Seleccionar la familia `WINDOWS` o `DOORS`.
5. Crear su LDM con los componentes, cantidades, operaciones y centros de
   trabajo nativos de Odoo.
6. En `Reglas de transformacion`, asociar cada componente con el atributo que
   modifica su cantidad, indicando cantidad base, factor y merma.

## Uso correcto

La LDM maestra no se asocia a un producto comercial existente. Se selecciona
directamente al usar `Agregar producto especial` desde una venta.

- Un **Transformado** parte de un producto comercial terminado y su LDM consume
  una unidad de ese producto base.
- Un **Especial** parte de la plantilla maestra y copia sus materias primas,
  operaciones y reglas; no consume ningún producto terminado existente.

## Flujo resultante

Al confirmar un especial, el sistema crea el producto almacenable y copia la
LDM maestra con componentes, operaciones y cantidades calculadas.

La MO no se crea en la cotización: queda preparada y se libera mediante las
reglas de pago ya existentes. El documento impreso informa si está pendiente
de liberación o muestra la MO generada.

## Fórmula dimensional

Cada regla utiliza:

`Cantidad = Cantidad base + (valor numérico del atributo × factor) + merma`

Ejemplo: para un perfil vertical, atributo `Alto`, cantidad base `0`, factor
`2` y Alto `81`, la cantidad calculada será `162` antes de aplicar la merma.
