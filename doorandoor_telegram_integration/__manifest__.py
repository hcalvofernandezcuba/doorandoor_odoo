{
    "name": "DoorAndDoor Telegram Integration",
    "version": "18.0.1.0.0",
    "category": "Productivity/Discuss",
    "summary": "18.0.1.0.0 - Vinculación segura de usuarios Odoo con Telegram",
    "description": """
DoorAndDoor Telegram Integration
================================

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
        "views/telegram_bot_views.xml",
        "wizard/telegram_link_wizard_views.xml",
        "views/telegram_menus.xml",
    ],
    "installable": False,
    "application": True,
    "auto_install": False,
}
