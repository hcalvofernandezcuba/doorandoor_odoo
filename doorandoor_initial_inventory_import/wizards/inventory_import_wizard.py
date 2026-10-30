# -*- coding: utf-8 -*-
from odoo import fields, models


class DoorAndDoorInventoryImportWizard(models.TransientModel):
    _name = "ddii.inventory.import.wizard"
    _description = "Start Initial Inventory Import"

    source_format = fields.Selection([
        ("tampa_warehouse_pdf", "Tampa Warehouse PDF"),
        ("tampa_store_pdf", "Tampa Store PDF"),
    ], required=True, default="tampa_warehouse_pdf")
    location_id = fields.Many2one("stock.location", required=True, domain="[('usage', '=', 'internal')]")
    inventory_date = fields.Date(required=True, default=fields.Date.context_today)
    source_file = fields.Binary(required=True)
    source_filename = fields.Char()

    def action_create_and_analyze(self):
        self.ensure_one()
        batch = self.env["ddii.inventory.import"].create({
            "source_format": self.source_format, "location_id": self.location_id.id,
            "inventory_date": self.inventory_date, "source_file": self.source_file,
            "source_filename": self.source_filename,
        })
        batch.action_analyze()
        return {
            "type": "ir.actions.act_window", "res_model": "ddii.inventory.import",
            "res_id": batch.id, "view_mode": "form", "target": "current",
        }
