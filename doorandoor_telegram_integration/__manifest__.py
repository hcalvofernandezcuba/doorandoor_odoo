{
    "name": "DoorAndDoor Telegram Integration",
    "version": "18.0.1.4.0",
    "category": "Productivity/Discuss",
    "summary": "18.0.1.4.0 - Conecta el canal Dirección y soporte con Telegram",
    "description": """
DoorAndDoor Telegram Integration
================================

18.0.1.4.0 - Bandeja compartida Dirección y soporte
------------------------------------------------

- Asocia un canal de Conversaciones al bot de desarrollo.
- Envía desde el canal con `/tg Usuario: mensaje`.
- Publica las respuestas Telegram en el canal y en el historial individual.
- Mantiene fuera del canal colectivo los comandos y enlaces de activación.

18.0.1.3.1 - Historial Telegram aislado
------------------------------------------------

- Evita la colisión entre la conversación Telegram y los mensajes del chatter.
- Garantiza el registro independiente de mensajes entrantes y salientes.

18.0.1.3.0 - Conversaciones Odoo-Telegram
------------------------------------------------

- Permite escribir desde la ficha del usuario vinculado y recibir su respuesta.
- Conserva el historial entrante y saliente con identidad y fecha.
- Añade recepción manual inmediata además de la consulta automática local.

18.0.1.2.0 - Encuestas visuales de aprobación
------------------------------------------------

- Crea propuestas con varias imágenes y votantes autorizados.
- Envía variantes y botones de aprobación al Telegram vinculado.
- Registra cambios de voto, participación y resultado dentro de Odoo.
- Restringe la fase inicial al bot de desarrollo local.

18.0.1.1.1 - Guía operativa del bot de Pruebas
------------------------------------------------

- Documenta BotFather, getMe, getUpdates y la confirmación segura de chats.
- Define el paso a paso de instalación, webhook y validadores iniciales.
- Separa el vínculo interno actual del futuro flujo para clientes portal.

18.0.1.1.0 - Habilitación para instalación
------------------------------------------------

- Habilita la instalación del módulo en Odoo 18.
- Mantiene bots y webhooks separados para Local, Pruebas y Producción.
- Permite preparar la instancia sin incorporar tokens al código fuente.

18.0.1.0.0 - Fundación de la integración
------------------------------------------------

- Configura un bot exclusivo de DoorAndDoor sin incluir secretos en el código.
- Registra un webhook HTTPS protegido mediante clave de ruta y secret token.
- Vincula voluntariamente usuarios internos de Odoo con chats privados de
  Telegram usando enlaces temporales, de un solo uso y almacenados como hash.
- Permite consultar, desvincular y reactivar la cuenta conservando auditoría.
- Añade preferencias individuales para fabricación, almacén, tareas y avisos
  generales.
- Incorpora una cola de notificaciones con reintentos, historial de mensajes y
  protección contra actualizaciones duplicadas de Telegram.
- Incluye guías para crear el bot, reunir los datos y ejecutar el primer enlace
  de prueba desde la instancia local.
    """,
    "author": "Hanoi Calvo",
    "maintainer": "DoorAndDoor",
    "website": "https://doorandoor.com",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/telegram_security.xml",
        "security/ir.model.access.csv",
        "data/telegram_cron.xml",
        "views/telegram_user_link_views.xml",
        "views/telegram_notification_views.xml",
        "views/telegram_poll_views.xml",
        "views/telegram_bot_views.xml",
        "wizard/telegram_link_wizard_views.xml",
        "views/telegram_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
