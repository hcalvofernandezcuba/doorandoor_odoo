from odoo import models


class StockLabelWizard(models.TransientModel):
    _inherit = "ddsl.stock.label.wizard"

    def default_get(self, field_list):
        values = super().default_get(field_list)
        picking = self.env["stock.picking"].browse(
            values.get("picking_id") or self.env.context.get("default_picking_id")
        )
        if picking.purchase_id and "only_flagged_products" in field_list:
            # A purchase receipt must be printable even when the product master
            # has not yet been explicitly marked for automatic receipt labels.
            values["only_flagged_products"] = False
        return values

    def _ddpfw_origin_buckets_by_product(self):
        self.ensure_one()
        buckets = {}
        purchase = self.picking_id.purchase_id
        for line in purchase.order_line.filtered(
            lambda item: item.product_id and not item.display_type
        ):
            product_buckets = buckets.setdefault(line.product_id.id, [])
            allocations = line.ddpfw_supply_allocation_ids
            for allocation in allocations:
                product_buckets.extend(
                    [
                        {
                            "purchase_order": purchase.name,
                            "origin_type": allocation.origin_type,
                            "origin_document": allocation.origin_document,
                            "customer_name": allocation.invoice_id.partner_id.name or "",
                        }
                    ]
                    * max(int(round(allocation.quantity)), 0)
                )
            remainder = max(line.product_qty - sum(allocations.mapped("quantity")), 0.0)
            product_buckets.extend(
                [
                    {
                        "purchase_order": purchase.name,
                        "origin_type": "replenishment",
                        "origin_document": "Reposición",
                        "customer_name": "",
                    }
                ]
                * max(int(round(remainder)), 0)
            )
        return buckets

    def _ddpfw_enrich_received_payloads(self, payloads):
        """Attach purchase origin to the labels for the quantity actually received."""
        buckets = self._ddpfw_origin_buckets_by_product()
        offsets = {}
        for payload in payloads:
            product_id = payload.get("product_id")
            offset = offsets.get(product_id, 0)
            product_buckets = buckets.get(product_id, [])
            origin = product_buckets[offset] if offset < len(product_buckets) else {
                "purchase_order": self.picking_id.purchase_id.name,
                "origin_type": "replenishment",
                "origin_document": "Reposición",
                "customer_name": "",
            }
            payload.update(origin)
            offsets[product_id] = offset + 1
        return payloads

    def _iter_label_payloads(self):
        self.ensure_one()
        if not self.picking_id.purchase_id or self.print_mode == "product_code":
            return super()._iter_label_payloads()
        payloads, missing_tracked_products = super()._iter_label_payloads()
        return self._ddpfw_enrich_received_payloads(payloads), missing_tracked_products

    def _ddpfw_purchase_label_payloads(self):
        self.ensure_one()
        purchase = self.picking_id.purchase_id
        payloads = []
        for line in purchase.order_line.filtered(lambda item: item.product_id and not item.display_type):
            product = line.product_id
            reference = (
                product.barcode
                if product.product_tmpl_id.ddsl_label_use_barcode and product.barcode
                else product.default_code or product.barcode or product.display_name
            )
            allocations = line.ddpfw_supply_allocation_ids
            buckets = [
                (allocation.origin_type, allocation.origin_document, allocation.invoice_id.partner_id.name, allocation.quantity)
                for allocation in allocations
            ]
            remainder = max(line.product_qty - sum(allocations.mapped("quantity")), 0.0)
            if remainder:
                buckets.append(("replenishment", "Reposición", "", remainder))
            for origin_type, origin_document, customer_name, quantity in buckets:
                for _index in range(max(int(round(quantity)), 0)):
                    mobile_url = product.ddsl_get_mobile_url()
                    payloads.append(
                        {
                            "product_id": product.id,
                            "product_name": product.ddsl_get_label_title(),
                            "default_code": product.default_code or "",
                            "product_barcode": product.barcode or "",
                            "label_reference": reference or "",
                            "barcode_value": reference or "",
                            "lot_name": "",
                            "mobile_url": mobile_url,
                            "mobile_qr_src": product.ddsl_get_mobile_qr_src(mobile_url),
                            "barcode_src": product.ddsl_get_label_barcode_src(reference),
                            "purchase_order": purchase.name,
                            "origin_type": origin_type,
                            "origin_document": origin_document,
                            "customer_name": customer_name or "",
                        }
                    )
        return payloads

    def _iter_product_code_payloads(self):
        self.ensure_one()
        if self.picking_id.purchase_id:
            return self._ddpfw_purchase_label_payloads()
        return super()._iter_product_code_payloads()
