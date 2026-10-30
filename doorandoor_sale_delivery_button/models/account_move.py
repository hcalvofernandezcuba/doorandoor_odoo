# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_ddsn_open_po_delivery(self):
        raise UserError(_(
            "Las entregas no se gestionan desde prefacturas. "
            "Utilice la factura autorizada y las operaciones de Inventario."
        ))
