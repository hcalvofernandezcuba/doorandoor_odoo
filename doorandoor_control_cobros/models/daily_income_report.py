from odoo import fields, models, tools


class DoorAndDoorDailyIncomeReport(models.Model):
    _name = "doorandoor.daily.income.report"
    _description = "Ingresos diarios por método y unidad"
    _auto = False
    _order = "payment_date desc, id desc"

    payment_id = fields.Many2one("account.payment", string="Pago", readonly=True)
    payment_date = fields.Date(string="Fecha", readonly=True)
    journal_id = fields.Many2one(
        "account.journal", string="Método de pago", readonly=True
    )
    office_id = fields.Many2one(
        "doorandoor.commercial.office", string="Unidad", readonly=True
    )
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    commercial_user_id = fields.Many2one(
        "res.users", string="Comercial de la venta", readonly=True
    )
    move_id = fields.Many2one("account.move", string="Factura", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    company_currency_id = fields.Many2one(
        "res.currency", string="Moneda de la compañía", readonly=True
    )
    income_amount_company = fields.Monetary(
        string="Ingreso validado",
        currency_field="company_currency_id",
        readonly=True,
        aggregator="sum",
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    payment.id AS id,
                    payment.id AS payment_id,
                    payment.date AS payment_date,
                    payment.journal_id AS journal_id,
                    invoice.ddco_office_id AS office_id,
                    payment.partner_id AS partner_id,
                    invoice.invoice_user_id AS commercial_user_id,
                    invoice.id AS move_id,
                    payment.company_id AS company_id,
                    company.currency_id AS company_currency_id,
                    payment.amount_company_currency_signed AS income_amount_company
                FROM account_payment payment
                JOIN res_company company ON company.id = payment.company_id
                LEFT JOIN LATERAL (
                    SELECT control.id AS control_id, control.move_id
                    FROM doorandoor_cobro_control control
                    WHERE control.payment_id = payment.id
                      AND control.active IS TRUE
                      AND control.state = 'validated'
                    ORDER BY
                        CASE WHEN control.move_id = payment.ddc_invoice_id THEN 0 ELSE 1 END,
                        control.id
                    LIMIT 1
                ) validated_control ON TRUE
                LEFT JOIN account_move invoice
                    ON invoice.id = COALESCE(payment.ddc_invoice_id, validated_control.move_id)
                WHERE payment.payment_type = 'inbound'
                  AND payment.partner_type = 'customer'
                  AND validated_control.control_id IS NOT NULL
            )
            """
        )
