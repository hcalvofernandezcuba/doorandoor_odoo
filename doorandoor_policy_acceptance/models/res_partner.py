from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ddpa_policy_acceptance_ids = fields.One2many(
        "doorandoor.policy.acceptance", "partner_id", string="Aceptaciones de políticas"
    )
    ddpa_policy_acceptance_count = fields.Integer(compute="_compute_ddpa_policy_status")
    ddpa_policy_status = fields.Char(compute="_compute_ddpa_policy_status", string="Estado de políticas")
    ddpa_policy_valid_until = fields.Date(compute="_compute_ddpa_policy_status", string="Vigente hasta")

    def _ddpa_get_valid_acceptance(self):
        self.ensure_one()
        policy = self.env["doorandoor.policy.document"].get_current_policy()
        if not policy:
            return self.env["doorandoor.policy.acceptance"]
        today = fields.Date.context_today(self)
        return self.env["doorandoor.policy.acceptance"].sudo().search([
            ("partner_id.commercial_partner_id", "=", self.commercial_partner_id.id),
            ("policy_id", "=", policy.id),
            ("state", "=", "accepted"),
            ("valid_until", ">=", today),
        ], order="accepted_at desc", limit=1)

    def _compute_ddpa_policy_status(self):
        Acceptance = self.env["doorandoor.policy.acceptance"].sudo()
        for partner in self:
            valid = partner._ddpa_get_valid_acceptance()
            partner.ddpa_policy_status = "Vigente" if valid else "Pendiente"
            partner.ddpa_policy_valid_until = valid.valid_until if valid else False
            partner.ddpa_policy_acceptance_count = Acceptance.search_count([
                ("partner_id.commercial_partner_id", "=", partner.commercial_partner_id.id)
            ])

    def action_ddpa_view_acceptances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Aceptaciones de políticas",
            "res_model": "doorandoor.policy.acceptance",
            "view_mode": "list,form",
            "domain": [("partner_id.commercial_partner_id", "=", self.commercial_partner_id.id)],
            "context": {"default_partner_id": self.commercial_partner_id.id},
        }
