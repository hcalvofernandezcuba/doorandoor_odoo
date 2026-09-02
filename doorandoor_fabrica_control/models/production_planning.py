from collections import defaultdict
from datetime import datetime, time

import pytz

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DdfcProductionNeed(models.Model):
    _name = "ddfc.production.need"
    _description = "Necesidad de producción por almacén"
    _order = "required_date, priority desc, id"
    _check_company_auto = True

    name = fields.Char(default=lambda self: _("Nueva"), required=True, copy=False)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén solicitante", required=True, check_company=True)
    product_id = fields.Many2one("product.product", string="Producto", required=True, domain="[('is_storable', '=', True)]", check_company=True)
    product_uom_id = fields.Many2one(related="product_id.uom_id", string="UdM", store=True)
    requested_qty = fields.Float(string="Cantidad solicitada", required=True, default=1.0)
    planned_qty = fields.Float(string="Cantidad incorporada", compute="_compute_planned_qty", store=True)
    pending_qty = fields.Float(string="Cantidad pendiente", compute="_compute_planned_qty", store=True)
    required_date = fields.Date(string="Fecha requerida", default=fields.Date.context_today, required=True)
    eligible_at = fields.Datetime(
        string="Elegible para producción", default=fields.Datetime.now, required=True, index=True,
        help="Momento en que el pago o la reposición liberó esta necesidad para el próximo corte.",
    )
    priority = fields.Selection([("0", "Normal"), ("1", "Urgente")], default="0", required=True)
    source_type = fields.Selection(
        [("sale", "Venta"), ("replenishment", "Reposición"), ("manual", "Manual")],
        string="Origen",
        default="manual",
        required=True,
    )
    origin = fields.Char(string="Documento origen")
    source_invoice_id = fields.Many2one(
        "account.move", string="Factura origen", copy=False, index=True, check_company=True, ondelete="set null"
    )
    source_picking_id = fields.Many2one(
        "stock.picking", string="Transferencia origen", copy=False, index=True, check_company=True, ondelete="set null"
    )
    source_document = fields.Char(string="Documento vinculado", compute="_compute_source_document", store=True)
    notes = fields.Text(string="Observaciones")
    state = fields.Selection(
        [("pending", "Pendiente"), ("planned", "Planificada"), ("done", "Completada"), ("cancel", "Cancelada")],
        default="pending",
        required=True,
    )
    plan_line_ids = fields.Many2many("ddfc.daily.plan.line", "ddfc_need_plan_line_rel", "need_id", "line_id", string="Planes")
    fulfillment_line_id = fields.Many2one(
        "doorandoor.fulfillment.line", string="Línea de cumplimiento", copy=False, index=True, ondelete="set null"
    )

    @api.depends("source_type", "source_invoice_id.name", "source_picking_id.name", "origin", "name")
    def _compute_source_document(self):
        labels = dict(self._fields["source_type"].selection)
        for need in self:
            reference = need.source_invoice_id.name or need.source_picking_id.name or need.origin or need.name
            need.source_document = "%s: %s" % (labels.get(need.source_type, _("Origen")), reference)

    @api.depends("requested_qty", "plan_line_ids", "plan_line_ids.approved_qty", "plan_line_ids.plan_id.state")
    def _compute_planned_qty(self):
        for need in self:
            active_lines = need.plan_line_ids.filtered(lambda line: line.plan_id.state != "cancel")
            need.planned_qty = sum(active_lines.mapped("approved_qty"))
            need.pending_qty = max(need.requested_qty - need.planned_qty, 0.0)

    @api.constrains("requested_qty")
    def _check_requested_qty(self):
        if any(need.requested_qty <= 0 for need in self):
            raise ValidationError(_("La cantidad solicitada debe ser mayor que cero."))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nueva")) == _("Nueva"):
                vals["name"] = sequence.next_by_code("ddfc.production.need") or _("Nueva")
        return super().create(vals_list)


class DdfcDailyPlan(models.Model):
    _name = "ddfc.daily.plan"
    _description = "Plan diario de producción"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "plan_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(default=lambda self: _("Nuevo"), required=True, copy=False, tracking=True)
    plan_date = fields.Date(string="Fecha del plan", default=fields.Date.context_today, required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    production_warehouse_id = fields.Many2one("stock.warehouse", string="Centro de producción", required=True, check_company=True)
    material_destination_location_id = fields.Many2one(
        "stock.location", string="Destino de materiales", required=True,
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [False, company_id])]",
        help="Ubicación de Maquinado o Producción que recibirá físicamente los materiales.",
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("approved", "Aprobado"), ("materials", "Materiales solicitados"), ("cancel", "Cancelado")],
        default="draft", required=True, tracking=True,
    )
    line_ids = fields.One2many("ddfc.daily.plan.line", "plan_id", string="Producciones planificadas", copy=True)
    component_line_ids = fields.One2many("ddfc.daily.plan.component", "plan_id", string="Partes y piezas", copy=False)
    order_component_line_ids = fields.One2many(
        "ddfc.daily.plan.order.component", "plan_id", string="Partes y piezas por OF", copy=False
    )
    material_picking_id = fields.Many2one("stock.picking", string="Pedido de salida", readonly=True, copy=False)
    production_ids = fields.One2many("mrp.production", "ddfc_daily_plan_id", string="Órdenes de fabricación", readonly=True)
    notes = fields.Text(string="Observaciones")
    snapshot_at = fields.Datetime(string="Corte de solicitudes", readonly=True, copy=False, tracking=True)
    snapshot_user_id = fields.Many2one("res.users", string="Corte ejecutado por", readonly=True, copy=False)
    snapshot_locked = fields.Boolean(string="Corte cerrado", readonly=True, copy=False, tracking=True)

    _sql_constraints = [
        ("ddfc_daily_plan_unique", "unique(company_id, plan_date, production_warehouse_id)", "Ya existe un plan diario para esa fecha y centro de producción."),
    ]

    def init(self):
        """Lock historical plans that already captured request lines."""
        self.env.cr.execute("SELECT to_regclass(%s)", ["ddfc_daily_plan_line"])
        if not self.env.cr.fetchone()[0]:
            # During a clean installation Odoo may initialize this model before
            # creating the table of its line model. There are no historical
            # plans to migrate in that case.
            return
        self.env.cr.execute(
            """
            UPDATE ddfc_daily_plan AS plan
               SET snapshot_locked = TRUE,
                   snapshot_at = COALESCE(plan.snapshot_at, plan.create_date),
                   snapshot_user_id = COALESCE(plan.snapshot_user_id, plan.create_uid)
             WHERE plan.snapshot_locked IS NOT TRUE
               AND EXISTS (
                   SELECT 1 FROM ddfc_daily_plan_line AS line
                    WHERE line.plan_id = plan.id
               )
            """
        )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("ddfc.daily.plan") or _("Nuevo")
        return super().create(vals_list)

    def action_load_pending_needs(self):
        self.ensure_one()
        if self.state != "draft" or self.snapshot_locked:
            raise UserError(_("El corte de este plan ya fue ejecutado y no admite nuevas peticiones."))
        cutoff = self.snapshot_at or fields.Datetime.now()
        needs = self.env["ddfc.production.need"].search([
            ("company_id", "=", self.company_id.id), ("state", "=", "pending"),
            ("eligible_at", "<", cutoff), ("pending_qty", ">", 0),
        ])
        for need in needs:
            bom = self.env["mrp.bom"]._bom_find(need.product_id, company_id=self.company_id.id).get(need.product_id)
            self.env["ddfc.daily.plan.line"].with_context(ddfc_snapshot_loading=True).create({
                "plan_id": self.id, "warehouse_id": need.warehouse_id.id,
                "product_id": need.product_id.id, "bom_id": bom.id if bom else False,
                "requested_qty": need.pending_qty, "approved_qty": need.pending_qty,
                "need_ids": [Command.set(need.ids)],
            })
        self.write({"snapshot_at": cutoff, "snapshot_user_id": self.env.user.id, "snapshot_locked": True})
        return True

    @api.model
    def _cron_generate_daily_plans(self):
        timezone = pytz.timezone("America/Havana")
        now_utc = fields.Datetime.now()
        aware_now = pytz.UTC.localize(now_utc).astimezone(timezone)
        local_midnight = timezone.localize(datetime.combine(aware_now.date(), time.min))
        cutoff_utc = local_midnight.astimezone(pytz.UTC).replace(tzinfo=None)
        for company in self.env["res.company"].sudo().search([]):
            warehouse = self.env["stock.warehouse"].sudo().search([
                ("company_id", "=", company.id), ("name", "ilike", "Tampa Produccion")
            ], limit=1)
            if not warehouse:
                continue
            existing = self.sudo().search([
                ("company_id", "=", company.id), ("plan_date", "=", aware_now.date()),
                ("production_warehouse_id", "=", warehouse.id),
            ], limit=1)
            if existing:
                continue
            destination = warehouse.manu_type_id.default_location_src_id
            if not destination:
                continue
            plan = self.sudo().create({
                "plan_date": aware_now.date(), "company_id": company.id,
                "production_warehouse_id": warehouse.id,
                "material_destination_location_id": destination.id,
                "snapshot_at": cutoff_utc,
            })
            plan.action_load_pending_needs()
        return True

    def _prepare_components(self):
        self.ensure_one()
        totals = defaultdict(lambda: {"qty": 0.0, "uom": False})
        self.component_line_ids.unlink()
        self.order_component_line_ids.unlink()
        for line in self.line_ids.filtered(lambda item: item.approved_qty > 0):
            if not line.bom_id:
                raise UserError(_("El producto %s no tiene LdM.") % line.product_id.display_name)
            factor = line.product_uom_id._compute_quantity(line.approved_qty, line.bom_id.product_uom_id) / line.bom_id.product_qty
            _boms, components = line.bom_id.explode(line.product_id, factor, picking_type=line.bom_id.picking_type_id)
            for bom_line, data in components:
                if bom_line.product_id.type != "consu":
                    continue
                quantity = bom_line.product_uom_id._compute_quantity(data["qty"], bom_line.product_id.uom_id, round=False)
                totals[bom_line.product_id]["qty"] += quantity
                totals[bom_line.product_id]["uom"] = bom_line.product_id.uom_id
                self.env["ddfc.daily.plan.order.component"].create({
                    "plan_id": self.id,
                    "plan_line_id": line.id,
                    "product_id": bom_line.product_id.id,
                    "required_qty": quantity,
                    "product_uom_id": bom_line.product_id.uom_id.id,
                })
        self.component_line_ids = [Command.create({"product_id": product.id, "required_qty": values["qty"], "product_uom_id": values["uom"].id}) for product, values in totals.items()]

    def action_approve(self):
        self.ensure_one()
        if self.state != "draft" or not self.line_ids.filtered(lambda line: line.approved_qty > 0):
            raise UserError(_("El plan debe estar en borrador y contener cantidades aprobadas."))
        self._prepare_components()
        for line in self.line_ids.filtered(lambda item: item.approved_qty > 0):
            if not line.production_id:
                production = self.env["mrp.production"].create({
                    "product_id": line.product_id.id, "product_qty": line.approved_qty,
                    "product_uom_id": line.product_uom_id.id, "bom_id": line.bom_id.id,
                    "picking_type_id": self.production_warehouse_id.manu_type_id.id,
                    "location_src_id": self.production_warehouse_id.manu_type_id.default_location_src_id.id,
                    "location_dest_id": self.production_warehouse_id.manu_type_id.default_location_dest_id.id,
                    "ddpa_origin_warehouse_id": self.production_warehouse_id.id,
                    "ddpa_delivery_warehouse_id": line.warehouse_id.id,
                    "ddfc_daily_plan_id": self.id,
                    "ddfc_source_need_id": line.need_ids[:1].id,
                    "ddfc_source_invoice_id": line.need_ids[:1].source_invoice_id.id,
                    "origin": line.source_document or self.name,
                    "date_start": fields.Datetime.to_datetime(self.plan_date),
                })
                production.action_confirm()
                line.production_id = production
            for need in line.need_ids:
                need.state = "planned" if line.approved_qty >= line.requested_qty else "pending"
            for need in line.need_ids.filtered("fulfillment_line_id"):
                fulfillment = need.fulfillment_line_id
                fulfillment.write({
                    "mrp_production_id": production.id,
                    "qty_sent_mrp": fulfillment.qty_sent_mrp + line.approved_qty,
                    "state": "in_process",
                })
        self.state = "approved"

    def action_request_materials(self):
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("Primero debe aprobarse el plan diario."))
        if self.material_picking_id:
            return self.action_open_material_picking()
        picking_type = self.production_warehouse_id.int_type_id
        if not picking_type:
            raise UserError(_("El centro de producción no tiene operación interna."))
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": self.production_warehouse_id.lot_stock_id.id,
            "location_dest_id": self.material_destination_location_id.id,
            "origin": self.name, "company_id": self.company_id.id,
        })
        moves = []
        for component in self.component_line_ids.filtered(lambda item: item.required_qty > 0):
            moves.append(Command.create({
                "name": component.product_id.display_name, "product_id": component.product_id.id,
                "product_uom_qty": component.required_qty, "product_uom": component.product_uom_id.id,
                "location_id": picking.location_id.id, "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company_id.id,
            }))
        picking.move_ids = moves
        picking.action_confirm()
        self.write({"material_picking_id": picking.id, "state": "materials"})
        return self.action_open_material_picking()

    def action_open_material_picking(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "stock.picking", "res_id": self.material_picking_id.id, "view_mode": "form"}

    def action_print_daily_plan(self):
        self.ensure_one()
        return self.env.ref("doorandoor_fabrica_control.action_report_ddfc_daily_plan").report_action(self)

    def action_print_material_request(self):
        self.ensure_one()
        if not self.component_line_ids:
            raise UserError(_("Aprueba el plan para calcular primero las partes y piezas."))
        return self.env.ref("doorandoor_fabrica_control.action_report_ddfc_material_request").report_action(self)

    def action_print_material_delivery(self):
        self.ensure_one()
        if not self.material_picking_id:
            raise UserError(_("Primero debe solicitarse la salida de materiales."))
        return self.env.ref("doorandoor_fabrica_control.action_report_ddfc_material_delivery").report_action(self)

    def action_print_order_labels(self):
        self.ensure_one()
        if not self.line_ids.filtered("production_id"):
            raise UserError(_("Primero debe aprobar el plan y crear las órdenes de fabricación."))
        return self.env.ref("doorandoor_fabrica_control.action_report_ddfc_order_labels").report_action(self)

    def action_cancel(self):
        for plan in self:
            if plan.material_picking_id and plan.material_picking_id.state != "cancel":
                raise UserError(_("Cancela primero el pedido de materiales."))
            plan.state = "cancel"


class DdfcDailyPlanLine(models.Model):
    _name = "ddfc.daily.plan.line"
    _description = "Línea del plan diario"
    _order = "warehouse_id, product_id"

    plan_id = fields.Many2one("ddfc.daily.plan", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén solicitante", required=True)
    product_id = fields.Many2one("product.product", string="Producto", required=True)
    product_uom_id = fields.Many2one(related="product_id.uom_id", store=True)
    bom_id = fields.Many2one("mrp.bom", string="LdM", domain="[('product_tmpl_id', '=', product_id.product_tmpl_id)]")
    requested_qty = fields.Float(string="Solicitado", required=True)
    approved_qty = fields.Float(string="Aprobado", required=True)
    need_ids = fields.Many2many("ddfc.production.need", "ddfc_need_plan_line_rel", "line_id", "need_id", string="Necesidades origen")
    production_id = fields.Many2one("mrp.production", string="OF", readonly=True, copy=False)
    source_document = fields.Char(string="Documento origen", compute="_compute_source_document")
    source_type = fields.Selection(
        [("sale", "Venta"), ("replenishment", "Reposición"), ("manual", "Manual")],
        string="Tipo de origen", compute="_compute_source_document",
    )
    order_component_line_ids = fields.One2many(
        "ddfc.daily.plan.order.component", "plan_line_id", string="Materiales de esta OF", readonly=True
    )
    label_copies = fields.Integer(string="Etiquetas", compute="_compute_label_copies")

    @api.depends("need_ids.source_document", "plan_id.name")
    def _compute_source_document(self):
        for line in self:
            line.source_document = line.need_ids[:1].source_document or line.plan_id.name
            line.source_type = line.need_ids[:1].source_type or "manual"

    @api.depends("approved_qty")
    def _compute_label_copies(self):
        for line in self:
            line.label_copies = max(1, int(round(line.approved_qty))) if line.approved_qty > 0 else 0

    @api.constrains("requested_qty", "approved_qty")
    def _check_quantities(self):
        if any(line.requested_qty < 0 or line.approved_qty < 0 for line in self):
            raise ValidationError(_("Las cantidades no pueden ser negativas."))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("ddfc_snapshot_loading"):
            plans = self.env["ddfc.daily.plan"].browse([vals.get("plan_id") for vals in vals_list if vals.get("plan_id")])
            if any(plan.snapshot_locked for plan in plans):
                raise UserError(_("No se pueden agregar peticiones después del corte del plan."))
        return super().create(vals_list)

    def write(self, vals):
        if any(line.plan_id.snapshot_locked for line in self):
            forbidden = set(vals) - {"approved_qty", "production_id"}
            if forbidden:
                raise UserError(_("El corte está cerrado; solo puede cambiarse la cantidad aprobada."))
        return super().write(vals)

    def unlink(self):
        if any(line.plan_id.snapshot_locked for line in self):
            raise UserError(_("No se pueden eliminar peticiones después del corte del plan."))
        return super().unlink()


class DdfcDailyPlanComponent(models.Model):
    _name = "ddfc.daily.plan.component"
    _description = "Componente requerido por el plan diario"
    _order = "product_id"

    plan_id = fields.Many2one("ddfc.daily.plan", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    product_id = fields.Many2one("product.product", string="Parte o pieza", required=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", required=True)
    required_qty = fields.Float(string="Cantidad requerida", required=True)
    available_qty = fields.Float(string="Disponible en Tampa", compute="_compute_availability")
    shortage_qty = fields.Float(string="Faltante", compute="_compute_availability")

    @api.depends("product_id", "required_qty", "plan_id.production_warehouse_id")
    def _compute_availability(self):
        for line in self:
            location = line.plan_id.production_warehouse_id.lot_stock_id
            available = line.product_id.with_context(location=location.id).free_qty if location else 0.0
            line.available_qty = available
            line.shortage_qty = max(line.required_qty - available, 0.0)


class DdfcDailyPlanOrderComponent(models.Model):
    _name = "ddfc.daily.plan.order.component"
    _description = "Componente requerido por orden de fabricación"
    _order = "plan_line_id, product_id"

    plan_id = fields.Many2one("ddfc.daily.plan", required=True, ondelete="cascade", index=True)
    plan_line_id = fields.Many2one("ddfc.daily.plan.line", required=True, ondelete="cascade", index=True)
    production_id = fields.Many2one(related="plan_line_id.production_id", string="OF", store=True)
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    warehouse_id = fields.Many2one(related="plan_line_id.warehouse_id", string="Almacén solicitante", store=True)
    source_document = fields.Char(related="plan_line_id.source_document", string="Documento origen")
    product_id = fields.Many2one("product.product", string="Parte o pieza", required=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", required=True)
    required_qty = fields.Float(string="Cantidad requerida", required=True)
