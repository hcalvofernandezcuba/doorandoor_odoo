from odoo import _, fields, models, tools
from odoo.exceptions import UserError


class DoorAndDoorPendingDelivery(models.Model):
    _name = "doorandoor.pending.delivery"
    _description = "Entrega pagada pendiente por almacen"
    _auto = False
    _order = "warehouse_id, invoice_date asc, invoice_id, product_id"

    fulfillment_line_id = fields.Many2one(
        "doorandoor.fulfillment.line", string="Seguimiento", readonly=True
    )
    invoice_id = fields.Many2one("account.move", string="Factura", readonly=True)
    invoice_date = fields.Date(string="Fecha de factura", readonly=True)
    sale_order_id = fields.Many2one("sale.order", string="Cotizacion", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacen", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    salesperson_id = fields.Many2one("res.users", string="Vendedor", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto / variante", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    qty_invoiced = fields.Float(string="Cantidad facturada", readonly=True)
    qty_delivered = fields.Float(string="Cantidad entregada", readonly=True)
    qty_pending_delivery = fields.Float(string="Pendiente de entregar", readonly=True)
    picking_id = fields.Many2one("stock.picking", string="Entrega", readonly=True)
    picking_state = fields.Selection(related="picking_id.state", string="Estado picking", readonly=True)
    delivery_date = fields.Datetime(string="Fecha de entrega", readonly=True)
    mrp_production_id = fields.Many2one("mrp.production", string="Orden de fabricacion", readonly=True)
    operational_state = fields.Selection(
        [
            ("waiting_production", "Esperando produccion"),
            ("pending_preparation", "Pendiente de preparar"),
            ("in_preparation", "En preparacion"),
            ("ready_delivery", "Lista para entregar"),
            ("delivered", "Entregado"),
        ],
        string="Estado operativo",
        readonly=True,
    )
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)

    def action_open_picking(self):
        """Open the released native delivery without creating parallel pickings."""
        self.ensure_one()
        if not self.picking_id:
            raise UserError(
                _(
                    "Esta entrega todavía no tiene una orden de despacho liberada. "
                    "Revise su estado operativo o la producción pendiente."
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Procesar entrega"),
            "res_model": "stock.picking",
            "res_id": self.picking_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
                CREATE OR REPLACE VIEW {self._table} AS (
                    SELECT
                        fl.id AS id,
                        fl.id AS fulfillment_line_id,
                        am.id AS invoice_id,
                        am.invoice_date AS invoice_date,
                        fl.sale_order_id AS sale_order_id,
                        COALESCE(spt.warehouse_id, so.warehouse_id) AS warehouse_id,
                        am.partner_id AS partner_id,
                        so.user_id AS salesperson_id,
                        fl.product_id AS product_id,
                        aml.product_uom_id AS product_uom_id,
                        fl.qty_invoiced AS qty_invoiced,
                        fl.qty_delivered AS qty_delivered,
                        GREATEST(fl.qty_pending_delivery, fl.qty_invoiced - fl.qty_delivered, 0.0)
                            AS qty_pending_delivery,
                        fl.picking_id AS picking_id,
                        sp.date_done AS delivery_date,
                        fl.mrp_production_id AS mrp_production_id,
                        CASE
                            WHEN GREATEST(
                                fl.qty_pending_delivery,
                                fl.qty_invoiced - fl.qty_delivered,
                                0.0
                            ) <= 0.00001
                                THEN 'delivered'
                            WHEN fl.mrp_production_id IS NOT NULL
                                 AND COALESCE(mp.state, 'draft') NOT IN ('done', 'cancel')
                                THEN 'waiting_production'
                            WHEN fl.picking_id IS NULL
                                THEN 'pending_preparation'
                            WHEN sp.state = 'assigned'
                                THEN 'ready_delivery'
                            ELSE 'in_preparation'
                        END AS operational_state,
                        am.company_id AS company_id
                    FROM doorandoor_fulfillment_line fl
                    JOIN account_move am ON am.id = fl.move_id
                    JOIN account_move_line aml ON aml.id = fl.move_line_id
                    LEFT JOIN sale_order so ON so.id = fl.sale_order_id
                    LEFT JOIN stock_picking sp ON sp.id = fl.picking_id
                    LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                    LEFT JOIN mrp_production mp ON mp.id = fl.mrp_production_id
                    WHERE am.move_type = 'out_invoice'
                      AND am.state = 'posted'
                      AND am.ddsn_is_preinvoice IS NOT TRUE
                      AND am.payment_state = 'paid'
                      AND ABS(am.amount_residual) < 0.00001
                      AND COALESCE(sp.state, '') != 'cancel'
                )
            """
        )
