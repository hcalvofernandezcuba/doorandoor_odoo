# Cierre diario de caja

1. Contabilidad crea un diario de tipo **Caja/Efectivo** contra la cuenta
   `101501 Efectivo` y crea una **Caja de ventas** que lo use.
2. El cajero abre la caja y declara el fondo de cambio por denominación.
3. Los cobros en efectivo deben registrarse exclusivamente en ese diario.
4. Al cierre, el cajero cuenta cada denominación. El sistema compara el total
   con fondo inicial + ventas de efectivo - salidas de efectivo.
5. Si hay diferencia, el cierre no se confirma. Si coincide, genera el reporte
   diario y la planilla de depósito sin crear asiento bancario automático.
