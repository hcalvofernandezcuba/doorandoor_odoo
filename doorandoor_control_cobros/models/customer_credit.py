from odoo import _, fields, models


class DoorAndDoorCustomerCredit(models.Model):
    _name = "doorandoor.customer.credit"
    _description = "Credito disponible de clientes"
    _auto = False
    _order = "available_amount desc, payment_date desc"

    payment_id = fields.Many2one("account.payment", string="Pago origen", readonly=True)
    accounting_move_id = fields.Many2one("account.move", string="Asiento contable", readonly=True)
    origin_control_id = fields.Many2one(
        "doorandoor.cobro.control", string="Control de origen", readonly=True
    )
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    journal_id = fields.Many2one("account.journal", string="Diario", readonly=True)
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    payment_date = fields.Date(string="Fecha del pago", readonly=True)
    original_amount = fields.Monetary(
        string="Credito original", currency_field="currency_id", readonly=True
    )
    applied_amount = fields.Monetary(
        string="Total aplicado", currency_field="currency_id", readonly=True
    )
    available_amount = fields.Monetary(
        string="Saldo disponible", currency_field="currency_id", readonly=True
    )
    application_count = fields.Integer(string="Aplicaciones", readonly=True)
    credit_state = fields.Selection(
        [("available", "Disponible"), ("partial", "Consumido parcialmente")],
        string="Estado del credito",
        readonly=True,
    )

    def init(self):
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW doorandoor_customer_credit AS (
                WITH payment_credit AS (
                    SELECT
                        p.id AS payment_id,
                        MIN(am.id) AS accounting_move_id,
                        MIN(am.ddc_credit_origin_control_id) AS origin_control_id,
                        p.partner_id,
                        p.journal_id,
                        p.company_id,
                        p.currency_id,
                        p.date AS payment_date,
                        SUM(aml.credit) AS original_amount,
                        GREATEST(-SUM(aml.amount_residual), 0.0) AS available_amount
                    FROM account_payment p
                    JOIN account_move am ON am.ddc_credit_origin_payment_id = p.id
                    JOIN account_move_line aml ON aml.move_id = am.id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE p.payment_type = 'inbound'
                      AND p.partner_type = 'customer'
                      AND am.state = 'posted'
                      AND aa.code_store ->> p.company_id::text LIKE '1200__'
                      AND aa.code_store ->> p.company_id::text != '120000'
                      AND aml.credit > 0
                    GROUP BY
                        p.id, p.partner_id, p.journal_id,
                        p.company_id, p.currency_id, p.date, p.amount
                )
                SELECT
                    pc.payment_id AS id,
                    pc.payment_id,
                    pc.accounting_move_id,
                    pc.origin_control_id,
                    pc.partner_id,
                    pc.journal_id,
                    pc.company_id,
                    pc.currency_id,
                    pc.payment_date,
                    pc.original_amount,
                    GREATEST(pc.original_amount - pc.available_amount, 0.0) AS applied_amount,
                    pc.available_amount,
                    (
                        SELECT COUNT(*)
                          FROM doorandoor_cobro_control c
                         WHERE c.payment_id = pc.payment_id
                           AND c.source_type = 'customer_credit'
                           AND c.active = TRUE
                           AND c.state != 'rejected'
                    ) AS application_count,
                    CASE
                        WHEN pc.available_amount < pc.original_amount THEN 'partial'
                        ELSE 'available'
                    END AS credit_state
                FROM payment_credit pc
                WHERE pc.available_amount > 0
            )
            """
        )

    def action_open_accounting_move(self):
        self.ensure_one()
        if not self.accounting_move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Asiento contable del credito"),
            "res_model": "account.move",
            "res_id": self.accounting_move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_credit_applications(self):
        self.ensure_one()
        action = self.env.ref("doorandoor_control_cobros.action_ddc_cobro_control").read()[0]
        action["name"] = _("Aplicaciones del credito")
        action["domain"] = [("payment_id", "=", self.payment_id.id)]
        action["context"] = {"search_default_validated": 1}
        return action
