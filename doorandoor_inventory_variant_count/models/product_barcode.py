from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _doorandoor_ean13_check_digit(self, base):
        """Return the EAN-13 check digit for a 12-digit numeric base."""
        if len(base) != 12 or not base.isdigit():
            raise UserError(_("The product barcode base must contain exactly 12 digits."))
        weighted_sum = sum(
            int(digit) * (1 if position % 2 == 0 else 3)
            for position, digit in enumerate(base)
        )
        return str((10 - weighted_sum % 10) % 10)

    @api.model
    def _doorandoor_next_product_barcode(self):
        """Generate YYYYMMDD + daily order + EAN-13 check digit."""
        barcode_date = fields.Date.context_today(self)
        date_digits = barcode_date.strftime("%Y%m%d")
        sequence_code = f"doorandoor.product.barcode.{date_digits}"

        # Serialize creation of the sequence for this date. ir.sequence handles
        # concurrent increments after the daily sequence exists.
        lock_key = int(date_digits)
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s)", [lock_key])
        sequence = self.env["ir.sequence"].sudo().search(
            [("code", "=", sequence_code)], limit=1
        )
        if not sequence:
            sequence = self.env["ir.sequence"].sudo().create({
                "name": _("doorandoor Product Barcode %s") % date_digits,
                "code": sequence_code,
                "prefix": date_digits,
                "padding": 4,
                "number_increment": 1,
                "company_id": False,
            })

        base = sequence._next()
        if len(base) != 12 or not base.isdigit():
            raise UserError(_(
                "The daily product barcode sequence exceeded 9,999 products. "
                "Contact the system administrator before creating more products today."
            ))
        return base + self._doorandoor_ean13_check_digit(base)

    def action_generate_doorandoor_barcode(self):
        products_without_barcode = self.filtered(lambda product: not product.barcode)
        if not products_without_barcode:
            raise UserError(_("All selected product variants already have a barcode."))
        for product in products_without_barcode:
            product.barcode = product._doorandoor_next_product_barcode()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Barcodes generated"),
                "message": _("Generated barcodes for %s product variant(s).")
                % len(products_without_barcode),
                "type": "success",
                "sticky": False,
            },
        }


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ddic_shared_lot_serial = fields.Boolean(
        string="Serial compartido por lote",
        help=(
            "Genera un solo codigo para todo el lote. Cada lectura repetida suma "
            "la cantidad indicada, en lugar de rechazar el codigo como duplicado."
        ),
    )

    def action_generate_doorandoor_barcode(self):
        self.ensure_one()
        return self.product_variant_ids.action_generate_doorandoor_barcode()
