# Módulos Odoo de DoorAndDoor

Repositorio oficial de los módulos instalados y desarrollados para la instancia
DoorAndDoor sobre Odoo 18.

## Organización

Cada directorio de primer nivel que contiene un archivo `__manifest__.py` es un
módulo de Odoo. Este repositorio no almacena bases de datos, sesiones, respaldos,
logs, configuración de la instancia ni credenciales.

## Flujo de trabajo

1. Crear una rama para cada cambio funcional o corrección.
2. Modificar y validar el módulo en la instancia local de desarrollo.
3. Incrementar la versión y actualizar el `summary` de su `__manifest__.py`.
4. Crear commits pequeños y descriptivos, separados por funcionalidad.
5. Integrar en `main` únicamente cambios revisados y verificables.
6. Etiquetar las versiones que se desplieguen en pruebas o producción.

La publicación en este repositorio no actualiza automáticamente ninguna base de
datos ni autoriza reinicios o despliegues de Odoo.

## Remoto oficial

`git@github.com:hcalvofernandezcuba/doorandoor_odoo.git`
