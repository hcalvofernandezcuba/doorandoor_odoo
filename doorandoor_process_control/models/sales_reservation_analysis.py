from odoo import fields, models, tools


class DoorAndDoorSalesReservationAnalysis(models.Model):
    _name = "doorandoor.sales.reservation.analysis"
    _description = "Analisis de reservas y prereservas de ventas"
    _auto = False
    _order = "reservation_date desc, warehouse_id, product_id"

    reservation_type = fields.Selection(
        [("pre_reservation", "Prereserva comercial"), ("stock_reservation", "Reserva fisica")],
        string="Tipo",
        readonly=True,
    )
    reservation_state = fields.Selection(
        [
            ("active", "Activa"),
            ("expiring", "Proxima a vencer"),
            ("expired", "Vencida"),
            ("reserved", "Reservada"),
            ("partial", "Reserva parcial"),
            ("waiting", "Sin existencia reservada"),
        ],
        string="Estado",
        readonly=True,
    )
    document_ref = fields.Char(string="Documento", readonly=True)
    reservation_date = fields.Datetime(string="Fecha de reserva", readonly=True)
    reservation_expires_at = fields.Datetime(string="Vencimiento", readonly=True)
    preinvoice_id = fields.Many2one("account.move", string="Prefactura", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Factura", readonly=True)
    sale_order_id = fields.Many2one("sale.order", string="Venta", readonly=True)
    picking_id = fields.Many2one("stock.picking", string="Entrega", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacen", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    salesperson_id = fields.Many2one("res.users", string="Vendedor", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto / variante", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    requested_qty = fields.Float(string="Cantidad solicitada", readonly=True)
    reserved_qty = fields.Float(string="Cantidad reservada", readonly=True)
    pending_reservation_qty = fields.Float(string="Pendiente de reservar", readonly=True)
    committed_value = fields.Monetary(
        string="Valor comprometido", currency_field="currency_id", readonly=True
    )
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
                CREATE OR REPLACE VIEW {self._table} AS (
                    SELECT
                        aml.id AS id,
                        'pre_reservation'::varchar AS reservation_type,
                        CASE
                            WHEN am.ddsn_reservation_expires_at <= NOW() THEN 'expired'
                            WHEN am.ddsn_reservation_expires_at <= NOW() + INTERVAL '4 hours' THEN 'expiring'
                            ELSE 'active'
                        END::varchar AS reservation_state,
                        COALESCE(am.ddsn_preinvoice_number, am.name, '/') AS document_ref,
                        am.write_date AS reservation_date,
                        am.ddsn_reservation_expires_at AS reservation_expires_at,
                        am.id AS preinvoice_id,
                        NULL::integer AS invoice_id,
                        am.sale_order_id AS sale_order_id,
                        NULL::integer AS picking_id,
                        COALESCE(aml.ddsn_supply_warehouse_id, so.warehouse_id) AS warehouse_id,
                        am.partner_id AS partner_id,
                        so.user_id AS salesperson_id,
                        aml.product_id AS product_id,
                        aml.product_uom_id AS product_uom_id,
                        aml.quantity AS requested_qty,
                        aml.quantity AS reserved_qty,
                        0.0::numeric AS pending_reservation_qty,
                        aml.price_subtotal AS committed_value,
                        am.currency_id AS currency_id,
                        am.company_id AS company_id
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    LEFT JOIN sale_order so ON so.id = am.sale_order_id
                    WHERE am.move_type = 'out_invoice'
                      AND am.state = 'draft'
                      AND am.ddsn_is_preinvoice IS TRUE
                      AND am.ddsn_preinvoice_state = 'confirmed'
                      AND am.ddsn_reservation_expires_at IS NOT NULL
                      AND aml.display_type = 'product'
                      AND aml.product_id IS NOT NULL

                    UNION ALL

                    SELECT
                        1000000000 + fl.id AS id,
                        'stock_reservation'::varchar AS reservation_type,
                        CASE
                            WHEN COALESCE(sm.quantity, 0.0) <= 0.00001 THEN 'waiting'
                            WHEN sm.quantity + 0.00001 < fl.qty_pending_delivery THEN 'partial'
                            ELSE 'reserved'
                        END::varchar AS reservation_state,
                        COALESCE(sp.name, am.name, '/') AS document_ref,
                        sp.create_date AS reservation_date,
                        NULL::timestamp AS reservation_expires_at,
                        NULL::integer AS preinvoice_id,
                        am.id AS invoice_id,
                        fl.sale_order_id AS sale_order_id,
                        sp.id AS picking_id,
                        COALESCE(spt.warehouse_id, so.warehouse_id) AS warehouse_id,
                        am.partner_id AS partner_id,
                        so.user_id AS salesperson_id,
                        fl.product_id AS product_id,
                        aml.product_uom_id AS product_uom_id,
                        fl.qty_pending_delivery AS requested_qty,
                        LEAST(COALESCE(sm.quantity, 0.0), fl.qty_pending_delivery) AS reserved_qty,
                        GREATEST(fl.qty_pending_delivery - COALESCE(sm.quantity, 0.0), 0.0)
                            AS pending_reservation_qty,
                        CASE
                            WHEN fl.qty_invoiced > 0
                            THEN aml.price_subtotal * fl.qty_pending_delivery / fl.qty_invoiced
                            ELSE 0.0
                        END AS committed_value,
                        am.currency_id AS currency_id,
                        am.company_id AS company_id
                    FROM doorandoor_fulfillment_line fl
                    JOIN account_move am ON am.id = fl.move_id
                    JOIN account_move_line aml ON aml.id = fl.move_line_id
                    JOIN stock_picking sp ON sp.id = fl.picking_id
                    LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                    LEFT JOIN sale_order so ON so.id = fl.sale_order_id
                    LEFT JOIN stock_move sm
                      ON sm.picking_id = sp.id
                     AND sm.product_id = fl.product_id
                     AND sm.state != 'cancel'
                     AND (fl.sale_line_id IS NULL OR sm.sale_line_id = fl.sale_line_id)
                    WHERE am.move_type = 'out_invoice'
                      AND am.state = 'posted'
                      AND am.payment_state = 'paid'
                      AND ABS(am.amount_residual) < 0.00001
                      AND sp.state NOT IN ('done', 'cancel')
                      AND fl.qty_pending_delivery > 0.00001
                )
            """
        )
