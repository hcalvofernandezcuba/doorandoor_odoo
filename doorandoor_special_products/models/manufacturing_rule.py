import logging
import re

from odoo import _, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class DdspManufacturingRule(models.Model):
    _name = "ddsp.manufacturing.rule"
    _description = "Regla dimensional de LDM transformada"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade", index=True)
    component_product_id = fields.Many2one(
        "product.product", string="Componente", required=True
    )
    attribute_id = fields.Many2one(
        "product.attribute", string="Atributo numerico", required=True
    )
    condition_value = fields.Char(
        string="Valor condicion",
        help="Opcional. La regla solo aplica cuando el valor configurado coincide.",
    )
    base_quantity = fields.Float(string="Cantidad base", default=0.0)
    value_factor = fields.Float(
        string="Factor",
        help="Cantidad añadida por cada unidad numerica del atributo.",
    )
    waste_percent = fields.Float(string="Merma %", default=0.0)

    def _ddsp_numeric_value(self, configured_value):
        self.ensure_one()
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", configured_value or "")
        if not match:
            raise UserError(
                _("El valor '%s' del atributo %s no contiene una medida numerica.")
                % (configured_value, self.attribute_id.display_name)
            )
        return float(match.group(0).replace(",", "."))


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    ddsp_manufacturing_rule_ids = fields.One2many(
        "ddsp.manufacturing.rule", "bom_id", string="Reglas dimensionales", copy=True
    )

    def _ddsp_apply_manufacturing_rules(self, special_changes):
        self.ensure_one()
        changes = {
            int(change.get("attribute_id")): (change.get("value") or "").strip()
            for change in (special_changes or [])
            if change.get("attribute_id")
        }
        applicable = self.ddsp_manufacturing_rule_ids.filtered(
            lambda rule: rule.attribute_id.id in changes
            and (
                not rule.condition_value
                or rule.condition_value.strip().casefold()
                == changes[rule.attribute_id.id].casefold()
            )
        )
        for component in applicable.mapped("component_product_id"):
            rules = applicable.filtered(lambda rule: rule.component_product_id == component)
            bom_line = self.bom_line_ids.filtered(lambda line: line.product_id == component)[:1]
            if not bom_line:
                _logger.warning(
                    "DoorAndDoor omitio la regla del componente %s porque no "
                    "existe en la LDM %s.",
                    component.display_name,
                    self.display_name,
                )
                continue
            quantity = sum(rules.mapped("base_quantity"))
            quantity += sum(
                rule._ddsp_numeric_value(changes[rule.attribute_id.id]) * rule.value_factor
                for rule in rules
            )
            waste = max(rules.mapped("waste_percent") or [0.0])
            quantity *= 1.0 + (waste / 100.0)
            if quantity <= 0:
                raise UserError(
                    _("La regla de %s produjo una cantidad no valida para %s.")
                    % (rules[0].attribute_id.display_name, component.display_name)
                )
            bom_line.with_context(ddsp_keep_bom_validation=True).product_qty = quantity
        return True
