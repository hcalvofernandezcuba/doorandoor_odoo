from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DdfcPrehungFamily(models.Model):
    _name = "ddfc.prehung.family"
    _description = "Familia de LdM configurable Prehung"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
    )
    finished_product_tmpl_id = fields.Many2one(
        "product.template", string="Familia Prehung", required=True,
        check_company=True, tracking=True,
    )
    slab_product_tmpl_id = fields.Many2one(
        "product.template", string="Familia Slab", required=True,
        check_company=True, tracking=True,
    )
    type_attribute_id = fields.Many2one(
        "product.attribute", string="Atributo tipo", required=True,
    )
    prehung_type_value_ids = fields.Many2many(
        "product.attribute.value", "ddfc_family_prehung_type_rel",
        "family_id", "value_id", string="Valores Prehung", required=True,
        domain="[('attribute_id', '=', type_attribute_id)]",
    )
    slab_type_value_id = fields.Many2one(
        "product.attribute.value", string="Valor Slab", required=True,
        domain="[('attribute_id', '=', type_attribute_id)]",
    )
    slab_ignored_attribute_ids = fields.Many2many(
        "product.attribute", "ddfc_family_slab_ignored_attribute_rel",
        "family_id", "attribute_id", string="Atributos no usados por el Slab",
        help=(
            "Atributos propios del terminado, como mano o color de bisagra, "
            "que no deben participar al buscar el Slab equivalente."
        ),
    )
    slab_qty = fields.Float(string="Slab por Prehung", default=1.0, required=True)
    slab_label_policy = fields.Selection(
        [("unique", "Label único"), ("shared", "Label compartido")],
        string="Control de labels del Slab",
        compute="_compute_slab_label_policy",
    )
    component_rule_ids = fields.One2many(
        "ddfc.prehung.component.rule", "family_id", string="Reglas de componentes",
        copy=True,
    )
    generated_bom_ids = fields.One2many(
        "mrp.bom", "ddfc_prehung_family_id", string="LdM generadas", readonly=True,
    )
    generated_bom_count = fields.Integer(
        compute="_compute_generated_bom_count", string="LdM generadas",
    )

    _sql_constraints = [
        (
            "ddfc_prehung_family_template_company_unique",
            "unique(finished_product_tmpl_id, company_id)",
            "Ya existe una configuración Prehung para esa familia y compañía.",
        ),
    ]

    @api.depends("generated_bom_ids")
    def _compute_generated_bom_count(self):
        for family in self:
            family.generated_bom_count = len(family.generated_bom_ids)

    @api.depends("slab_product_tmpl_id.ddic_shared_lot_serial")
    def _compute_slab_label_policy(self):
        for family in self:
            family.slab_label_policy = (
                "shared"
                if family.slab_product_tmpl_id.ddic_shared_lot_serial
                else "unique"
            )

    @api.constrains("slab_qty")
    def _check_slab_qty(self):
        if any(family.slab_qty <= 0 for family in self):
            raise ValidationError(_("La cantidad de Slab debe ser mayor que cero."))

    @api.constrains(
        "type_attribute_id", "prehung_type_value_ids", "slab_type_value_id"
    )
    def _check_type_values(self):
        for family in self:
            values = family.prehung_type_value_ids | family.slab_type_value_id
            if values.filtered(lambda value: value.attribute_id != family.type_attribute_id):
                raise ValidationError(
                    _("Los valores Prehung y Slab deben pertenecer al atributo tipo.")
                )
            if family.slab_type_value_id in family.prehung_type_value_ids:
                raise ValidationError(_("El valor Slab no puede ser también un valor Prehung."))

    def _ddfc_product_values(self, product):
        return product.product_template_attribute_value_ids.mapped(
            "product_attribute_value_id"
        )

    def _ddfc_resolve_slab(self, finished_product):
        self.ensure_one()
        finished_values = self._ddfc_product_values(finished_product)
        if not (finished_values & self.prehung_type_value_ids):
            raise UserError(
                _("%s no contiene un valor tipo Prehung configurado.")
                % finished_product.display_name
            )

        ignored = self.slab_ignored_attribute_ids | self.type_attribute_id
        expected = finished_values.filtered(lambda value: value.attribute_id not in ignored)
        expected |= self.slab_type_value_id
        expected_pairs = {(value.attribute_id.id, value.id) for value in expected}

        candidates = self.slab_product_tmpl_id.product_variant_ids.filtered("active")
        matches = self.env["product.product"]
        for candidate in candidates:
            candidate_values = self._ddfc_product_values(candidate)
            candidate_pairs = {
                (value.attribute_id.id, value.id) for value in candidate_values
            }
            if candidate_pairs == expected_pairs:
                matches |= candidate
        if len(matches) != 1:
            raise UserError(
                _(
                    "La familia %(family)s esperaba un único Slab para %(product)s "
                    "y encontró %(count)s. Revise atributos y duplicados."
                )
                % {
                    "family": self.display_name,
                    "product": finished_product.display_name,
                    "count": len(matches),
                }
            )
        return matches

    def _ddfc_resolve_rule_role(self, finished_product, role):
        self.ensure_one()
        finished_value_ids = set(self._ddfc_product_values(finished_product).ids)
        candidates = self.component_rule_ids.filtered(
            lambda rule: rule.active
            and rule.role == role
            and set(rule.required_value_ids.ids).issubset(finished_value_ids)
        )
        if not candidates:
            raise UserError(
                _("No existe una regla de %(role)s para %(product)s.")
                % {
                    "role": dict(
                        self.env["ddfc.prehung.component.rule"]._fields["role"].selection
                    ).get(role, role),
                    "product": finished_product.display_name,
                }
            )
        specificity = max(len(rule.required_value_ids) for rule in candidates)
        matches = candidates.filtered(
            lambda rule: len(rule.required_value_ids) == specificity
        )
        if len(matches) != 1:
            raise UserError(
                _(
                    "Existen %(count)s reglas de %(role)s con la misma prioridad "
                    "para %(product)s. La selección debe ser única."
                )
                % {
                    "count": len(matches),
                    "role": role,
                    "product": finished_product.display_name,
                }
            )
        return matches

    def _ddfc_resolve_components(self, finished_product):
        self.ensure_one()
        if finished_product.product_tmpl_id != self.finished_product_tmpl_id:
            raise UserError(
                _("%s no pertenece a la familia Prehung configurada.")
                % finished_product.display_name
            )
        components = [(self._ddfc_resolve_slab(finished_product), self.slab_qty, "slab")]
        for role in ("jamb", "hinge"):
            rule = self._ddfc_resolve_rule_role(finished_product, role)
            components.append((rule.component_product_id, rule.quantity, role))
        policies = {
            role: product.product_tmpl_id.ddic_shared_lot_serial
            for product, _quantity, role in components
        }
        if policies["slab"]:
            raise UserError(_("El Slab debe usar serial y label único, no compartido."))
        if policies["jamb"]:
            raise UserError(_("El Jamb debe usar serial y label único, no compartido."))
        if not policies["hinge"]:
            raise UserError(_("Las bisagras deben usar label compartido para contar cantidades."))
        return components

    def _ddfc_get_or_create_bom(self, finished_product):
        self.ensure_one()
        Bom = self.env["mrp.bom"].sudo()
        existing = Bom.search([
            ("product_id", "=", finished_product.id),
            ("ddfc_prehung_family_id", "=", self.id),
            ("active", "=", True),
        ], limit=1)
        if existing:
            return existing
        components = self._ddfc_resolve_components(finished_product)
        signature = ";".join(
            "%s:%s:%s" % (role, product.id, quantity)
            for product, quantity, role in components
        )
        bom = Bom.create({
            "product_tmpl_id": finished_product.product_tmpl_id.id,
            "product_id": finished_product.id,
            "product_qty": 1.0,
            "product_uom_id": finished_product.uom_id.id,
            "type": "normal",
            "company_id": self.company_id.id,
            "ddfc_prehung_family_id": self.id,
            "ddfc_resolution_signature": signature,
            "bom_line_ids": [
                Command.create({
                    "product_id": product.id,
                    "product_qty": quantity,
                    "product_uom_id": product.uom_id.id,
                    "ddfc_component_role": role,
                })
                for product, quantity, role in components
            ],
        })
        finished_product.product_tmpl_id.message_post(
            body=_(
                "LdM configurable creada desde la familia %s. Componentes: %s"
            ) % (
                self.display_name,
                ", ".join(
                    "%s x %s" % (product.display_name, quantity)
                    for product, quantity, _role in components
                ),
            )
        )
        return bom

    def action_generate_existing_variant_boms(self):
        for family in self:
            for product in family.finished_product_tmpl_id.product_variant_ids.filtered("active"):
                values = family._ddfc_product_values(product)
                if values & family.prehung_type_value_ids:
                    family._ddfc_get_or_create_bom(product)
        return self.action_open_generated_boms()

    def action_open_generated_boms(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_form_action")
        action["domain"] = [("ddfc_prehung_family_id", "=", self.id)]
        action["context"] = {"default_ddfc_prehung_family_id": self.id}
        return action


class DdfcPrehungComponentRule(models.Model):
    _name = "ddfc.prehung.component.rule"
    _description = "Regla de componente Prehung"
    _order = "role, sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    family_id = fields.Many2one(
        "ddfc.prehung.family", required=True, ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(related="family_id.company_id", store=True)
    role = fields.Selection(
        [("jamb", "Jamb / marco"), ("hinge", "Bisagras")],
        required=True,
    )
    required_value_ids = fields.Many2many(
        "product.attribute.value", "ddfc_component_rule_value_rel",
        "rule_id", "value_id", string="Valores requeridos",
        help="La regla aplica cuando la variante terminada contiene todos estos valores.",
    )
    component_product_id = fields.Many2one(
        "product.product", string="Componente", required=True,
        domain="[('is_storable', '=', True)]",
    )
    quantity = fields.Float(default=1.0, required=True)
    label_policy = fields.Selection(
        [("unique", "Label único"), ("shared", "Label compartido")],
        compute="_compute_label_policy", string="Control de labels",
    )

    @api.depends("component_product_id.product_tmpl_id.ddic_shared_lot_serial")
    def _compute_label_policy(self):
        for rule in self:
            rule.label_policy = (
                "shared"
                if rule.component_product_id.product_tmpl_id.ddic_shared_lot_serial
                else "unique"
            )

    @api.constrains("quantity")
    def _check_quantity(self):
        if any(rule.quantity <= 0 for rule in self):
            raise ValidationError(_("La cantidad del componente debe ser mayor que cero."))


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    ddfc_prehung_family_id = fields.Many2one(
        "ddfc.prehung.family", string="Familia Prehung", readonly=True,
        copy=False, index=True, ondelete="restrict",
    )
    ddfc_resolution_signature = fields.Char(
        string="Firma de resolución", readonly=True, copy=False, index=True,
    )
    ddfc_stock_production = fields.Boolean(
        string="Producción estándar para stock",
        help="Clasifica una LdM normal destinada a reposición o fabricación para inventario.",
    )
    ddfc_bom_kind = fields.Selection(
        [
            ("special", "Producto especial"),
            ("prehung", "Prehung estándar"),
            ("stock", "Estándar para stock"),
            ("other", "Otra / sin clasificar"),
        ],
        string="Tipo de LdM", compute="_compute_ddfc_bom_kind", store=True,
        index=True,
    )

    @api.depends(
        "product_tmpl_id.ddsp_is_special",
        "ddfc_prehung_family_id",
        "ddfc_stock_production",
    )
    def _compute_ddfc_bom_kind(self):
        for bom in self:
            if bom.product_tmpl_id.ddsp_is_special:
                bom.ddfc_bom_kind = "special"
            elif bom.ddfc_prehung_family_id:
                bom.ddfc_bom_kind = "prehung"
            elif bom.ddfc_stock_production:
                bom.ddfc_bom_kind = "stock"
            else:
                bom.ddfc_bom_kind = "other"


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    ddfc_component_role = fields.Selection(
        [("slab", "Slab"), ("jamb", "Jamb / marco"), ("hinge", "Bisagras")],
        string="Rol Prehung", readonly=True, copy=True,
    )
    ddfc_label_policy = fields.Selection(
        [("unique", "Label único"), ("shared", "Label compartido")],
        compute="_compute_ddfc_label_policy", string="Control de labels",
    )

    @api.depends("product_id.product_tmpl_id.ddic_shared_lot_serial")
    def _compute_ddfc_label_policy(self):
        for line in self:
            line.ddfc_label_policy = (
                "shared"
                if line.product_id.product_tmpl_id.ddic_shared_lot_serial
                else "unique"
            )


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _ddfc_ensure_configured_bom(self, company=None):
        self.ensure_one()
        company = company or self.env.company
        family = self.env["ddfc.prehung.family"].sudo().search([
            ("active", "=", True),
            ("company_id", "=", company.id),
            ("finished_product_tmpl_id", "=", self.product_tmpl_id.id),
        ], limit=1)
        if not family:
            return self.env["mrp.bom"]
        values = family._ddfc_product_values(self)
        if not (values & family.prehung_type_value_ids):
            return self.env["mrp.bom"]
        return family._ddfc_get_or_create_bom(self)
