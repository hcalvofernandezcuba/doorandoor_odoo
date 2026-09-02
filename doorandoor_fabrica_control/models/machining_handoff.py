from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class DdfcMachiningHandoff(models.Model):
    _name = "ddfc.machining.handoff"
    _description = "Entrega de Maquinado a Ensamblaje"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(string="Vale", default=lambda self: _("Nuevo"), required=True, copy=False, readonly=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    production_id = fields.Many2one(
        "mrp.production", string="Orden de fabricación", required=True, index=True,
        check_company=True, ondelete="restrict", tracking=True,
    )
    product_id = fields.Many2one(related="production_id.product_id", string="Producto de la OF", store=True)
    product_qty = fields.Float(related="production_id.product_qty", string="Cantidad de la OF")
    product_uom_id = fields.Many2one(related="production_id.product_uom_id", string="UdM de la OF")
    machining_workorder_id = fields.Many2one(
        "mrp.workorder", string="Operación de Maquinado", check_company=True,
        domain="[('production_id', '=', production_id)]", ondelete="restrict",
    )
    reception_workorder_id = fields.Many2one(
        "mrp.workorder", string="Recepción en Ensamblaje", check_company=True,
        domain="[('production_id', '=', production_id)]", ondelete="restrict",
    )
    origin_type = fields.Selection(
        [("sale", "Factura de venta"), ("replenishment", "OF por reposición de stock")],
        string="Tipo de documento origen", compute="_compute_origin", store=True,
    )
    origin_document = fields.Char(string="Documento origen de la OF", compute="_compute_origin", store=True)
    source_invoice_id = fields.Many2one(related="production_id.ddfc_source_invoice_id", string="Factura de venta", store=True)
    replenishment_reference = fields.Char(
        string="Referencia de reposición", compute="_compute_origin", store=True,
        help="Solicitud, transferencia o referencia que justificó la fabricación para reponer stock.",
    )
    line_ids = fields.One2many(
        "ddfc.machining.handoff.line", "handoff_id", string="Partes o productos entregados", copy=True,
    )
    delivered_by_id = fields.Many2one("res.users", string="Entregado por Maquinado", readonly=True, tracking=True)
    delivered_at = fields.Datetime(string="Fecha y hora de salida", readonly=True, tracking=True)
    received_by_id = fields.Many2one("res.users", string="Recibido por Ensamblaje", readonly=True, tracking=True)
    received_at = fields.Datetime(string="Fecha y hora de recepción", readonly=True, tracking=True)
    notes = fields.Text(string="Observaciones")
    state = fields.Selection(
        [("draft", "Borrador"), ("dispatched", "Entregado por Maquinado"),
         ("received", "Recibido por Ensamblaje"), ("cancel", "Cancelado")],
        default="draft", required=True, tracking=True,
    )

    _sql_constraints = [
        ("ddfc_handoff_name_unique", "unique(name, company_id)", "El número del vale debe ser único por compañía."),
    ]

    @api.depends(
        "production_id.name", "production_id.ddfc_source_invoice_id.name",
        "production_id.ddfc_source_need_id.source_type",
        "production_id.ddfc_source_need_id.source_document",
    )
    def _compute_origin(self):
        for handoff in self:
            production = handoff.production_id
            need = production.ddfc_source_need_id
            if production.ddfc_source_invoice_id or need.source_type == "sale":
                handoff.origin_type = "sale"
                handoff.origin_document = production.ddfc_source_invoice_id.name or need.source_document
                handoff.replenishment_reference = False
            elif need.source_type == "replenishment":
                handoff.origin_type = "replenishment"
                handoff.origin_document = production.name
                handoff.replenishment_reference = need.source_document
            else:
                handoff.origin_type = False
                handoff.origin_document = False
                handoff.replenishment_reference = False

    @api.onchange("production_id")
    def _onchange_production_id(self):
        for handoff in self:
            workorders = handoff.production_id.workorder_ids
            handoff.machining_workorder_id = workorders.filtered(
                lambda wo: "maquin" in (wo.name or "").lower()
            )[:1]
            handoff.reception_workorder_id = workorders.filtered(
                lambda wo: "recep" in (wo.name or "").lower()
            )[:1]
            if handoff.production_id and not handoff.line_ids:
                handoff.line_ids = [Command.create({
                    "product_id": handoff.production_id.product_id.id,
                    "delivered_qty": handoff.production_id.product_qty,
                    "product_uom_id": handoff.production_id.product_uom_id.id,
                })]

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("ddfc.machining.handoff") or _("Nuevo")
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        production = self.env["mrp.production"].browse(values.get("production_id")).exists()
        if not production:
            return values
        workorders = production.workorder_ids
        values.setdefault("machining_workorder_id", workorders.filtered(
            lambda wo: "maquin" in (wo.name or "").lower()
        )[:1].id)
        values.setdefault("reception_workorder_id", workorders.filtered(
            lambda wo: "recep" in (wo.name or "").lower()
        )[:1].id)
        if "line_ids" in fields_list and not values.get("line_ids"):
            values["line_ids"] = [Command.create({
                "product_id": production.product_id.id,
                "delivered_qty": production.product_qty,
                "product_uom_id": production.product_uom_id.id,
            })]
        return values

    def _check_required_origin(self):
        for handoff in self:
            if not handoff.origin_type or not handoff.origin_document:
                raise UserError(_(
                    "La OF %s no tiene un origen válido. Debe proceder de una factura de venta "
                    "o de una necesidad de reposición de stock."
                ) % handoff.production_id.display_name)

    def action_dispatch(self):
        for handoff in self:
            if handoff.state != "draft":
                continue
            handoff._check_required_origin()
            if not handoff.line_ids:
                raise UserError(_("Agregue al menos una parte o producto antes de confirmar la salida."))
            if not any(line.delivered_qty > 0 or line.rejected_qty > 0 for line in handoff.line_ids):
                raise UserError(_("Registre alguna cantidad entregada o rechazada."))
            handoff.write({
                "state": "dispatched", "delivered_by_id": self.env.user.id,
                "delivered_at": fields.Datetime.now(),
            })
        return True

    def action_receive(self):
        for handoff in self:
            if handoff.state != "dispatched":
                raise UserError(_("Primero Maquinado debe confirmar la entrega."))
            for line in handoff.line_ids:
                accounted_qty = line.received_qty + line.receipt_rejected_qty
                if float_compare(
                    accounted_qty, line.delivered_qty,
                    precision_rounding=line.product_uom_id.rounding,
                ) != 0:
                    raise UserError(_(
                        "En %s, la cantidad aceptada más la rechazada por Ensamblaje debe ser "
                        "igual a la cantidad entregada por Maquinado."
                    ) % line.product_id.display_name)
            handoff.write({
                "state": "received", "received_by_id": self.env.user.id,
                "received_at": fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        self.filtered(lambda record: record.state != "received").write({"state": "cancel"})
        return True

    def action_print_handoff(self):
        self.ensure_one()
        return self.env.ref("doorandoor_fabrica_control.action_report_ddfc_machining_handoff").report_action(self)


class DdfcMachiningHandoffLine(models.Model):
    _name = "ddfc.machining.handoff.line"
    _description = "Línea de entrega de Maquinado a Ensamblaje"
    _order = "id"
    _check_company_auto = True

    handoff_id = fields.Many2one("ddfc.machining.handoff", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="handoff_id.company_id", store=True)
    product_id = fields.Many2one(
        "product.product", string="Parte o producto", required=True, check_company=True,
        domain="[('is_storable', '=', True)]",
    )
    description = fields.Char(string="Descripción")
    delivered_qty = fields.Float(string="Cantidad entregada", required=True)
    rejected_qty = fields.Float(string="Rechazada en Maquinado")
    received_qty = fields.Float(string="Cantidad aceptada")
    receipt_rejected_qty = fields.Float(string="Rechazada por Ensamblaje")
    product_uom_id = fields.Many2one("uom.uom", string="UdM", required=True)
    notes = fields.Char(string="Observaciones")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id

    @api.constrains("delivered_qty", "rejected_qty", "received_qty", "receipt_rejected_qty")
    def _check_nonnegative_quantities(self):
        for line in self:
            if min(line.delivered_qty, line.rejected_qty, line.received_qty, line.receipt_rejected_qty) < 0:
                raise ValidationError(_("Las cantidades del vale no pueden ser negativas."))
