from odoo import _, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def action_open_ddsl_document_label_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Labels de fabricacion"),
            "res_model": "ddsl.document.label.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_production_id": self.id,
            },
        }
