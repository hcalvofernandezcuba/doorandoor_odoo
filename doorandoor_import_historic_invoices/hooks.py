import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Assign the requested supervisor without hard-coding a database id."""
    if not isinstance(env, api.Environment):
        env = api.Environment(env, SUPERUSER_ID, {})
    group = env.ref(
        "doorandoor_import_historic_invoices.group_legacy_delivery_ocr_supervisor"
    )
    yuliet = env["res.users"].sudo().search(
        ["|", ("name", "ilike", "Yuliet"), ("login", "ilike", "yuliet")],
        limit=1,
    )
    if yuliet:
        group.sudo().write({"users": [(4, yuliet.id)]})
        _logger.info("Legacy delivery OCR supervisor assigned to user %s", yuliet.id)
    else:
        _logger.warning("Yuliet was not found; assign the OCR supervisor group manually.")
