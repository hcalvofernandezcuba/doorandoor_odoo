from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ddsl_receipt_count_ids = fields.One2many(
        "ddsl.stock.receipt.count",
        "picking_id",
        string="Conteos fisicos de recepcion",
        copy=False,
    )

    def action_open_ddsl_serial_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Register Receipt Lots / Serials"),
            "res_model": "ddsl.stock.serial.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_picking_id": self.id,
            },
        }

    def action_open_ddsl_label_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Print Receipt Labels"),
            "res_model": "ddsl.stock.label.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_picking_id": self.id,
            },
        }

    def action_open_ddsl_receipt_scan_wizard(self):
        self.ensure_one()
        wizard = self.env["ddsl.stock.receipt.scan.wizard"].ddsl_create_for_picking(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Recibir con hanger"),
            "res_model": "ddsl.stock.receipt.scan.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_assign(self):
        incoming_pickings = self.filtered(lambda picking: picking.picking_type_code == "incoming")
        other_pickings = self - incoming_pickings
        result = False
        if other_pickings:
            result = super(StockPicking, other_pickings).action_assign()
        if len(incoming_pickings) == 1:
            return incoming_pickings.action_open_ddsl_receipt_scan_wizard()
        if incoming_pickings:
            return incoming_pickings[0].action_open_ddsl_receipt_scan_wizard()
        return result


class StockMove(models.Model):
    _inherit = "stock.move"

    ddsl_receipt_scan_generated = fields.Boolean(
        string="Creado por conteo de recepcion",
        copy=False,
        help="Identifica movimientos no previstos creados al aplicar un conteo fisico.",
    )
