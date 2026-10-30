from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ddsr_refund_request_ids = fields.One2many(
        "doorandoor.stripe.refund.request", "invoice_id", string="Solicitudes de devolución"
    )
    ddsr_refund_request_count = fields.Integer(
        compute="_compute_ddsr_refund_request_count", string="Devoluciones Stripe"
    )

    def _compute_ddsr_refund_request_count(self):
        for move in self:
            move.ddsr_refund_request_count = len(move.ddsr_refund_request_ids)

    def action_ddsr_request_stripe_refund(self):
        self.ensure_one()
        if self.move_type != "out_invoice" or self.state != "posted":
            return False
        request = self.env["doorandoor.stripe.refund.request"].create_from_invoice(self)
        return request.action_open_form()

    def action_ddsr_view_stripe_refunds(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "doorandoor_stripe_refund.action_stripe_refund_requests"
        )
        action["domain"] = [("invoice_id", "=", self.id)]
        action["context"] = {"default_invoice_id": self.id}
        return action

