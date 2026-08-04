from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorAndDoorCobroMatchWizard(models.TransientModel):
    _name = "doorandoor.cobro.match.wizard"
    _description = "Asistente de Asociacion de Cobros"

    control_id = fields.Many2one(
        "doorandoor.cobro.control",
        string="Control de cobro",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        domain=[("customer_rank", ">", 0)],
        required=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Factura",
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('partner_id', '=', partner_id)]",
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago contable existente",
        domain="[('partner_type', '=', 'customer'), ('partner_id', '=', partner_id)]",
    )
    journal_id = fields.Many2one(
        related="control_id.journal_id",
        string="Diario reportado",
        readonly=True,
    )
    amount_reported = fields.Monetary(
        related="control_id.amount_reported",
        string="Monto reportado",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="control_id.currency_id",
        string="Moneda",
        readonly=True,
    )
    invoice_residual = fields.Monetary(
        string="Saldo actual de la factura",
        currency_field="currency_id",
        compute="_compute_invoice_residual",
    )
    matching_note = fields.Text(
        string="Nota de asociacion",
        help="Documenta como se identifico el cliente, la factura o el pago real.",
    )
    send_to_pending = fields.Boolean(
        string="Dejar pendiente para revision",
        default=True,
        help="Si esta activo, el control se deja en pendiente luego de asociar sus referencias.",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        control = self.env["doorandoor.cobro.control"].browse(self.env.context.get("default_control_id"))
        if control:
            values.setdefault("control_id", control.id)
            values.setdefault("partner_id", control.partner_id.id)
            values.setdefault("move_id", control.move_id.id)
            values.setdefault("payment_id", control.payment_id.id)
            values.setdefault("matching_note", control.identification_notes)
        return values

    @api.depends("move_id")
    def _compute_invoice_residual(self):
        for wizard in self:
            wizard.invoice_residual = wizard.move_id.amount_residual if wizard.move_id else 0.0

    @api.onchange("move_id")
    def _onchange_move_id(self):
        if self.move_id:
            self.partner_id = self.move_id.partner_id

    @api.onchange("payment_id")
    def _onchange_payment_id(self):
        if self.payment_id and self.payment_id.partner_id:
            self.partner_id = self.payment_id.partner_id

    def action_apply(self):
        self.ensure_one()
        control = self.control_id
        same_partner = control.partner_id == self.partner_id
        same_move = control.move_id == self.move_id
        same_payment = control.payment_id == self.payment_id
        same_note = (control.identification_notes or "") == (self.matching_note or "")
        if same_partner and same_move and same_payment and same_note:
            return control._ddc_notification_action(
                _("Asociacion sin cambios"),
                _("Este control ya tiene esa misma asociacion. No se realizaron cambios."),
                "warning",
            )
        vals = {
            "partner_id": self.partner_id.id,
            "identification_notes": self.matching_note or control.identification_notes,
        }
        if self.move_id:
            if self.move_id.partner_id != self.partner_id:
                raise ValidationError(_("La factura seleccionada no pertenece al cliente indicado."))
            vals.update(
                {
                    "move_id": self.move_id.id,
                    "currency_id": self.move_id.currency_id.id,
                    "company_id": self.move_id.company_id.id,
                    "invoice_residual_snapshot": self.move_id.amount_residual,
                }
            )
        if self.payment_id:
            if self.payment_id.partner_id != self.partner_id:
                raise ValidationError(_("El pago contable seleccionado no pertenece al cliente indicado."))
            vals["payment_id"] = self.payment_id.id
            vals.setdefault("currency_id", self.payment_id.currency_id.id)
            vals.setdefault("company_id", self.payment_id.company_id.id)
        if self.send_to_pending and control.state in ("draft", "reported", "rejected"):
            vals["state"] = "pending"
        control.write(vals)
        control._ddc_notify_transition(
            _("Control asociado"),
            _(
                "Se completo la asociacion operativa del control. Ya puede continuar la revision usando el cliente, la factura y el pago contable enlazados."
            ),
            "info",
        )
        return control._ddc_notification_action(
            _("Asociacion actualizada"),
            _("El control ya quedo asociado y listo para continuar el flujo de revision."),
            "success",
        )
