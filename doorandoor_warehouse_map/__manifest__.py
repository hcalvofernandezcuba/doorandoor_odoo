{
    "name": "DoorAndDoor Warehouse Visual Map",
    "version": "18.0.1.15.0",
    "category": "Inventory/Inventory",
    "summary": "18.0.1.15.0 - Trazabilidad documental de entradas y salidas por lote",
    "description": """
Version 18.0.1.15.0
-------------------
Relaciona cada label leído o reservado con su lote físico y documento de
inventario. El mapa muestra las salidas completadas y pendientes por lote,
permite abrir sus documentos y agrega una vista de control por almacén, lote,
label, operación, estado, operador y destino sin alterar las existencias.

Version 18.0.1.14.1
-------------------
El buscador del mapa reconoce el nombre completo seleccionado por el
autocompletado de productos, incluyendo todos los valores de la variante. La
coincidencia sigue limitada al almacén autorizado y a labels activos.

Version 18.0.1.14.0
-------------------
Muestra en los albaranes de entregas y traslados dónde recoger cada ITEM: lote,
posición física, ubicación operativa, almacén y labels disponibles o reservados.
En recepciones propone el lote exacto con capacidad, luego un lote mixto y por
último una posición vacía. La información aparece en pantalla y PDF sin mover
ni reservar inventario automáticamente.

Version 18.0.1.13.0
-------------------
Agrega un localizador global para consultar uno o varios labels y mostrar ITEM,
estado, almacén, lote, posición física, ubicación operativa y documentos
reservados. El mapa reconoce directamente el número de label, abre el almacén
correcto y resalta su lote sin modificar inventario ni movimientos.

Version 18.0.1.12.3
-------------------
Las recepciones recomiendan primero un lote con el mismo ITEM y capacidad; si
no existe, utilizan un lote mixto. La pantalla distingue ambos casos y el
chatter y el albarán conservan lote, posición física, cantidad y labels para
auditoría, sin alterar documentos históricos ya validados.

Version 18.0.1.12.2
-------------------
Corrige la construcción del mapa cuando un almacén contiene lotes mixtos. La
etiqueta traducible Mixto (N ITEM) ahora se genera correctamente y evita que la
respuesta completa del almacén quede vacía por un NameError, sin modificar
seriales, sesiones, existencias ni la composición de los lotes.

Version 18.0.1.12.1
-------------------
Mantiene disponible la sesión IC aditiva asociada a un lote mixto para recibir
productos y labels sucesivos sin límite de cantidad ni de ITEM. Si la sesión
está contando o en revisión se reutiliza conservando las lecturas anteriores;
si ya fue validada se reabre y crea la línea del producto nuevo cuando haga
falta, sin duplicar el inventario histórico.

Version 18.0.1.8.0
------------------
Permite seleccionar una posición vacía desde las líneas preparadas de una
recepción y materializa el lote al generar los labels, sin cargar inventario
antes de validar el documento.

Version 18.0.1.8.1
------------------
Elimina una dependencia calculada no buscable y permite validar inmediatamente
el lote creado desde una posición vacía.

Version 18.0.1.8.2
------------------
Impide el alta rápida de lotes sin almacén desde las recepciones. El operador
selecciona un lote compatible existente o una posición vacía para que el sistema
cree el lote con almacén, ITEM y cantidad completos.

Version 18.0.1.9.0
------------------
Permite identificar cada lote nuevo como posición fija, paleta móvil o contenedor
de carga. Exige una ubicación disponible o una referencia física única y conserva
el almacén, ITEM, cantidad y tipo de almacenamiento para auditoría.

Version 18.0.1.9.1
------------------
Hereda del mapa la capacidad y ocupación de cada posición. Recomienda completar
el lote del mismo ITEM cuando existe espacio suficiente y evita exceder la
capacidad física; solo entonces propone abrir una nueva ubicación.

Version 18.0.1.9.2
------------------
Reserva para el mismo ITEM toda posición física que ya contenga más de cinco
unidades. Impide mezclar allí productos diferentes y obliga a seleccionar otro
espacio, manteniendo ordenado el mapa y la trazabilidad del lote.

Version 18.0.1.9.3
------------------
Excluye de las posiciones disponibles los espacios reservados por la regla de
más de cinco unidades, evitando que el operador seleccione una opción que luego
sería rechazada.

Version 18.0.1.9.4
------------------
La recepción muestra únicamente posiciones disponibles ya configuradas en el
mapa del almacén destino. Deshabilita Crear, Crear y editar y abrir desde el
selector, evitando que el operador confunda una posición física con la creación
de un almacén o una ubicación maestra.

Version 18.0.1.9.5
------------------
Restaura Crear y editar para registrar una posición física nueva desde la
recepción. Hereda y bloquea el almacén destino ya definido; el operador puede
crear el lote/posición necesario, pero nunca un almacén maestro desde ese flujo.

Version 18.0.1.9.6
------------------
Al crear una posición física desde un lote serializado, hereda y bloquea el
almacén ya seleccionado en el lote. Si aún no existe selección, el campo muestra
únicamente los almacenes operativos autorizados para el usuario, evitando el
selector vacío observado por responsables multialmacén.

Version 18.0.1.9.7
------------------
Muestra siempre la ubicación física del lote seleccionado al agregar mercancía,
aunque el operador elija un lote distinto del recomendado. Para posiciones
fijas presenta la posición del mapa; para paletas o contenedores conserva su
tipo y referencia física. La ubicación también aparece en las líneas de la
recepción por ITEM.

Version 18.0.1.10.0
-------------------
Convierte el ingreso a lote en un flujo guiado: primero almacén; después una
recepción existente o la creación de una recepción oficial; ITEM limitado a
las líneas del documento; cantidad; y finalmente lote. Recomienda completar
un lote del mismo ITEM sin superar la capacidad operativa de 33 unidades o,
cuando no cabe, la posición vacía más cercana dentro del almacén elegido.
Las recepciones ya existentes conservan y escanean los labels del documento de
origen sin imprimir códigos nuevos. Solo una recepción creada automáticamente
genera labels DoorAndDoor y muestra al operador la alerta de impresión.

Version 18.0.1.10.1
-------------------
El almacén de destino se selecciona exclusivamente entre los almacenes
DoorAndDoor autorizados para el usuario. El selector ya no permite crear,
editar ni abrir almacenes maestros desde el ingreso de mercancía a lote.

Version 18.0.1.10.2
-------------------
Obtiene la lista del almacén de destino directamente mediante la búsqueda
autorizada del servidor, evitando que un dominio cliente todavía vacío muestre
“No hay registros” al abrir una recepción nueva.

Version 18.0.1.10.3
-------------------
Evita comparar identificadores temporales NewId durante el onchange de una
recepción nueva. Los lotes con igual capacidad se ordenan por su referencia
estable, sin provocar RPC_ERROR antes de mostrar el selector de almacén.

Version 18.0.1.11.0
-------------------
Fija en 33 la capacidad obligatoria de todas las posiciones DoorAndDoor. Al
agregar mercancía del mismo ITEM a un lote existente con espacio, crea solo
los labels nuevos, conserva las lecturas históricas y reabre la última sesión
aditiva validada del lote para escanear exclusivamente las unidades nuevas.

Version 18.0.1.11.1
-------------------
Excluye del mapa operativo y de la ocupación los ciclos marcados como Posición
liberada. La ubicación física queda disponible para una carga nueva sin tratar
la sesión histórica ni la campaña como anuladas o cerradas.

Version 18.0.1.12.0
-------------------
Reconoce lotes marcados como mixtos al recomendar posiciones y permite recibir
distintos ITEM sin aplicar la reserva monoproducto ni el máximo normal de 33.
Cada unidad mantiene su label, ITEM, ubicación e historial individual.
""",
    "author": "Hanoi Calvo",
    "maintainer": "doorandoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["web", "doorandoor_inventory_variant_count", "doorandoor_mobile_hanger"],
    "data": [
        "security/warehouse_map_security.xml",
        "security/ir.model.access.csv",
        "views/warehouse_map_views.xml",
        "views/inventory_serial_receipt_views.xml",
        "views/report_receipt_destination.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "doorandoor_warehouse_map/static/src/js/warehouse_map.js",
            "doorandoor_warehouse_map/static/src/xml/warehouse_map.xml",
            "doorandoor_warehouse_map/static/src/scss/warehouse_map.scss",
        ],
    },
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_hook",
}
