# Website de documentos DoorAndDoor

## Regla permanente de publicación

El website descubre y publica automáticamente todos los archivos Markdown que
cumplan este patrón:

```text
addons/doorandoor_*/docs/*.md
```

Para publicar una guía nueva:

1. Cree, si no existe, la carpeta lowercase `docs` dentro del módulo dueño del
   procedimiento.
2. Guarde el archivo con extensión `.md` directamente dentro de esa carpeta.
3. Use un nombre de archivo único entre todos los módulos para evitar rutas
   ambiguas.
4. Comience el contenido con un título Markdown de nivel uno: `# Título`.
5. Recargue el índice del website. No es necesario editar el controlador ni
   actualizar este módulo para incorporar el archivo.

Las carpetas `Docs`, `Dir`, subdirectorios de `docs/` y módulos cuyo nombre no
comience con `doorandoor_` no se publican.

## Seguridad documental

La carpeta `docs/` se considera pública. No deben guardarse allí contraseñas,
tokens, datos personales, notas internas, respaldos ni información que no deba
mostrarse en el website. Los documentos internos deben ubicarse fuera de
`docs/`.

Las dos guías operativas diarias de Inventario y Fabricación conservan la
primera posición del índice; los demás documentos se ordenan por módulo y
título.
