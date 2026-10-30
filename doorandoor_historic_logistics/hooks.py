import logging


_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Assign the startup supervisor role to Yuliet without system access."""
    group = env.ref(
        "doorandoor_historic_logistics.group_historic_logistics_supervisor",
        raise_if_not_found=False,
    )
    if not group:
        return
    users = env["res.users"].sudo().search([
        ("active", "=", True),
        "|",
        ("name", "ilike", "Yuliet"),
        ("login", "ilike", "yuliet"),
    ])
    if len(users) == 1:
        users.write({"groups_id": [(4, group.id)]})
        _logger.info("Assigned historical logistics supervisor to %s", users.display_name)
    elif not users:
        _logger.warning("Yuliet was not found; assign the historical logistics supervisor manually.")
    else:
        _logger.warning("Multiple Yuliet users found; supervisor assignment requires manual review.")
