from odoo import api, fields, models
from odoo.exceptions import ValidationError


SUPPLY_ROUTES = [
    ("stock", "Inventario disponible"),
    ("internal", "Fabricación interna"),
    ("external", "Fabricación externa"),
    ("subcontract", "Subcontratación con materiales propios"),
]

LOGISTIC_ROUTES = [
    ("warehouse", "Recibir en almacén"),
    ("predispatch", "Recibir en predespacho"),
    ("direct", "Entrega directa al cliente"),
    ("pickup", "Recoger en proveedor"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ddem_supply_route = fields.Selection(
        SUPPLY_ROUTES,
        string="Tipo de abastecimiento",
        default="stock",
        required=True,
        tracking=True,
    )
    ddem_primary_vendor_id = fields.Many2one(
        "res.partner",
        string="Proveedor principal",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
    )
    ddem_alternative_vendor_ids = fields.Many2many(
        "res.partner",
        "ddem_product_template_vendor_rel",
        "product_tmpl_id",
        "partner_id",
        string="Proveedores alternativos",
        domain="[('supplier_rank', '>', 0)]",
    )
    ddem_logistic_route = fields.Selection(
        LOGISTIC_ROUTES,
        string="Modalidad logística",
        default="warehouse",
        required=True,
        tracking=True,
    )
    ddem_receipt_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén de recepción",
        check_company=True,
    )
    ddem_manufacturing_days = fields.Integer(
        string="Días de fabricación",
        default=0,
    )
    ddem_transport_days = fields.Integer(
        string="Días de transporte",
        default=0,
    )
    ddem_min_payment_percent = fields.Float(
        string="Pago mínimo para ordenar (%)",
        default=100.0,
    )
    ddem_min_margin_percent = fields.Float(
        string="Margen mínimo (%)",
        default=0.0,
    )
    ddem_requires_manager_approval = fields.Boolean(
        string="Requiere aprobación de Gerencia",
        default=False,
    )
    ddem_auto_prepare_purchase = fields.Boolean(
        string="Permitir generar compra",
        default=True,
        help="Permite preparar una orden de compra en borrador cuando se cumplan los controles.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        for template, values in zip(templates, vals_list):
            base = template.ddsp_base_product_tmpl_id
            if not template.ddsp_is_special or not base:
                continue
            inherited = {}
            for field_name in (
                "ddem_supply_route",
                "ddem_primary_vendor_id",
                "ddem_logistic_route",
                "ddem_receipt_warehouse_id",
                "ddem_manufacturing_days",
                "ddem_transport_days",
                "ddem_min_payment_percent",
                "ddem_min_margin_percent",
                "ddem_requires_manager_approval",
                "ddem_auto_prepare_purchase",
            ):
                if field_name not in values:
                    value = base[field_name]
                    inherited[field_name] = value.id if hasattr(value, "id") else value
            if "ddem_alternative_vendor_ids" not in values:
                inherited["ddem_alternative_vendor_ids"] = [(6, 0, base.ddem_alternative_vendor_ids.ids)]
            if inherited:
                template.write(inherited)
        return templates

    @api.constrains(
        "ddem_supply_route",
        "ddem_primary_vendor_id",
        "ddem_receipt_warehouse_id",
        "ddem_min_payment_percent",
        "ddem_min_margin_percent",
        "ddem_manufacturing_days",
        "ddem_transport_days",
    )
    def _check_ddem_supply_configuration(self):
        for template in self:
            if template.ddem_supply_route in ("external", "subcontract") and not template.ddem_primary_vendor_id:
                continue
            if not 0 <= template.ddem_min_payment_percent <= 100:
                raise ValidationError("El pago mínimo debe estar entre 0 y 100 por ciento.")
            if not 0 <= template.ddem_min_margin_percent <= 100:
                raise ValidationError("El margen mínimo debe estar entre 0 y 100 por ciento.")
            if template.ddem_manufacturing_days < 0 or template.ddem_transport_days < 0:
                raise ValidationError("Los plazos no pueden ser negativos.")
