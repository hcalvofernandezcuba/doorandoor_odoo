from odoo import _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_open_ddsl_document_label_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Labels de factura"),
            "res_model": "ddsl.document.label.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_id": self.id,
            },
        }
