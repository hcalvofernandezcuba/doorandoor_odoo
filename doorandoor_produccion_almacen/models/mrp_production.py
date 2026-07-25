from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    ddpa_origin_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse Origin",
        domain="[('company_id', '=', company_id)]",
        copy=False,
    )
    ddpa_delivery_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse Delivery",
        domain="[('company_id', '=', company_id)]",
        copy=False,
    )
    ddpa_internal_picking_id = fields.Many2one(
        "stock.picking",
        string="Internal Transfer",
        readonly=True,
        copy=False,
    )

    @api.onchange("ddpa_origin_warehouse_id")
    def _onchange_ddpa_origin_warehouse_id(self):
        for production in self.filtered("ddpa_origin_warehouse_id"):
            if not production.ddpa_delivery_warehouse_id:
                production.ddpa_delivery_warehouse_id = production.ddpa_origin_warehouse_id

    @api.onchange("ddpa_delivery_warehouse_id")
    def _onchange_ddpa_delivery_warehouse_id(self):
        for production in self.filtered("ddpa_delivery_warehouse_id"):
            production._ddpa_apply_delivery_warehouse_defaults()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            origin_warehouse_id = vals.get("ddpa_origin_warehouse_id") or False
            if not vals.get("ddpa_delivery_warehouse_id") and origin_warehouse_id:
                vals["ddpa_delivery_warehouse_id"] = origin_warehouse_id
        return super().create(vals_list)

    def _ddpa_apply_delivery_warehouse_defaults(self):
        for production in self.filtered("ddpa_delivery_warehouse_id"):
            warehouse = production.ddpa_delivery_warehouse_id
            if warehouse.lot_stock_id:
                production.location_dest_id = warehouse.lot_stock_id

    def _ddpa_get_delivery_warehouse(self):
        self.ensure_one()
        return self.ddpa_delivery_warehouse_id or self.ddpa_origin_warehouse_id

    def _ddpa_get_internal_picking_type(self, warehouse):
        self.ensure_one()
        if not warehouse:
            return False
        for field_name in ("int_type_id", "internal_type_id"):
            if field_name in warehouse._fields and warehouse[field_name]:
                return warehouse[field_name]
        return self.env["stock.picking.type"].search(
            [
                ("warehouse_id", "=", warehouse.id),
                ("code", "=", "internal"),
            ],
            limit=1,
        )

    def _ddpa_create_internal_transfer_to_delivery_warehouse(self):
        self.ensure_one()
        warehouse = self._ddpa_get_delivery_warehouse()
        if not warehouse or not warehouse.lot_stock_id:
            return False
        if self.ddpa_internal_picking_id and self.ddpa_internal_picking_id.state not in ("cancel",):
            return self.ddpa_internal_picking_id
        if self.location_dest_id == warehouse.lot_stock_id:
            return False

        picking_type = self._ddpa_get_internal_picking_type(warehouse)
        if not picking_type:
            return False

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.location_dest_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "origin": f"{self.name} | Internal Transfer",
                "company_id": self.company_id.id,
                "move_type": "direct",
            }
        )
        self.env["stock.move"].create(
            {
                "name": self.product_id.display_name,
                "picking_id": picking.id,
                "company_id": self.company_id.id,
                "product_id": self.product_id.id,
                "product_uom_qty": self.product_qty,
                "product_uom": self.product_uom_id.id,
                "location_id": self.location_dest_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "origin": picking.origin,
            }
        )
        if picking.state == "draft":
            picking.action_confirm()
        if picking.state in ("confirmed", "waiting", "assigned"):
            picking.action_assign()
        self.ddpa_internal_picking_id = picking
        return picking

    def _ddsn_sync_invoice_fulfillment_after_done(self):
        for production in self:
            production._ddpa_create_internal_transfer_to_delivery_warehouse()
        return super()._ddsn_sync_invoice_fulfillment_after_done()
