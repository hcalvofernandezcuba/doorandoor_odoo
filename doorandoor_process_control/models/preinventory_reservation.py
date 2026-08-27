from odoo import fields, models, tools


class DoorAndDoorWarehousePrereservation(models.Model):
    _name = "doorandoor.warehouse.prereservation"
    _description = "Prereserva operativa por almacen"
    _auto = False
    _order = "reservation_expires_at asc, warehouse_id, product_id"

    preinvoice_id = fields.Many2one("account.move", string="Prefactura", readonly=True)
    preinvoice_number = fields.Char(string="Numero de prefactura", readonly=True)
    sale_order_id = fields.Many2one("sale.order", string="Cotizacion", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacen", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    salesperson_id = fields.Many2one("res.users", string="Vendedor", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto / variante", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    reserved_qty = fields.Float(string="Cantidad prereservada", readonly=True)
    reservation_expires_at = fields.Datetime(string="Vencimiento", readonly=True)
    hours_remaining = fields.Float(string="Horas restantes", readonly=True)
    reservation_state = fields.Selection(
        [("active", "Activa"), ("expiring", "Proxima a vencer"), ("expired", "Vencida")],
        string="Estado",
        readonly=True,
    )
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
                CREATE OR REPLACE VIEW {self._table} AS (
                    SELECT
                        aml.id AS id,
                        am.id AS preinvoice_id,
                        COALESCE(am.ddsn_preinvoice_number, am.name, '/') AS preinvoice_number,
                        am.sale_order_id AS sale_order_id,
                        COALESCE(aml.ddsn_supply_warehouse_id, so.warehouse_id) AS warehouse_id,
                        am.partner_id AS partner_id,
                        so.user_id AS salesperson_id,
                        aml.product_id AS product_id,
                        aml.product_uom_id AS product_uom_id,
                        aml.quantity AS reserved_qty,
                        am.ddsn_reservation_expires_at AS reservation_expires_at,
                        GREATEST(
                            EXTRACT(EPOCH FROM (am.ddsn_reservation_expires_at - NOW())) / 3600.0,
                            0.0
                        ) AS hours_remaining,
                        CASE
                            WHEN am.ddsn_reservation_expires_at <= NOW() THEN 'expired'
                            WHEN am.ddsn_reservation_expires_at <= NOW() + INTERVAL '4 hours' THEN 'expiring'
                            ELSE 'active'
                        END AS reservation_state,
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
                )
            """
        )
