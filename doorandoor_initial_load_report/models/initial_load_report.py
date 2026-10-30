from odoo import fields, models, tools


class InventoryInitialLoadReport(models.Model):
    _name = "inventory.initial.load.report"
    _description = "Analisis de carga inicial de inventario"
    _auto = False
    _rec_name = "reference"
    _order = "date desc, id desc"

    move_id = fields.Many2one("stock.move", string="Movimiento", readonly=True)
    session_id = fields.Many2one("inventory.count.session", string="Sesion de conteo", readonly=True)
    date = fields.Datetime(string="Fecha", readonly=True)
    reference = fields.Char(string="Referencia", readonly=True)
    load_reference = fields.Char(string="Lote", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacen", readonly=True)
    location_id = fields.Many2one("stock.location", string="Desde", readonly=True)
    location_dest_id = fields.Many2one("stock.location", string="A", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    product_uom = fields.Many2one("uom.uom", string="Unidad", readonly=True)
    user_id = fields.Many2one("res.users", string="Registrado por", readonly=True)
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)
    category = fields.Selection(
        [
            ("initial_load", "Carga inicial oficial"),
            ("correction", "Correccion de carga inicial"),
            ("test_cleanup", "Prueba / limpieza"),
            ("other", "Otro ajuste"),
        ],
        string="Clasificacion",
        readonly=True,
    )
    direction = fields.Selection(
        [("in", "Carga inicial"), ("out", "Reduccion tecnica")],
        string="Tipo de movimiento",
        readonly=True,
    )
    quantity_in = fields.Float(string="Cargado", readonly=True)
    quantity_out = fields.Float(string="Correccion tecnica (-)", readonly=True)
    net_quantity = fields.Float(string="Cantidad neta", readonly=True)
    move_count = fields.Integer(string="Numero de movimientos", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
                CREATE OR REPLACE VIEW {self._table} AS (
                    SELECT
                        sm.id AS id,
                        sm.id AS move_id,
                        ics.id AS session_id,
                        sm.date AS date,
                        sm.reference AS reference,
                        ics.load_reference AS load_reference,
                        COALESCE(src.warehouse_id, dst.warehouse_id) AS warehouse_id,
                        sm.location_id AS location_id,
                        sm.location_dest_id AS location_dest_id,
                        sm.product_id AS product_id,
                        sm.product_uom AS product_uom,
                        sm.create_uid AS user_id,
                        sm.company_id AS company_id,
                        CASE
                            WHEN sm.reference IN (
                                'Corrección Doral - cargas iniciales acumulativas',
                                'IC/2026/00070'
                            ) THEN 'correction'
                            WHEN ics.count_mode = 'additive' THEN 'initial_load'
                            WHEN ics.name IN ('IC/2026/00010', 'IC/2026/00095')
                                THEN 'initial_load'
                            WHEN sm.reference IN (
                                'IC/2026/00001', 'IC/2026/00002', 'IC/2026/00003',
                                'IC/2026/00004', 'IC/2026/00005',
                                'Cantidad de producto actualizada',
                                'Inicializacion controlada DTP - limpieza previa'
                            ) THEN 'test_cleanup'
                            ELSE 'other'
                        END AS category,
                        CASE WHEN src.usage = 'inventory' THEN 'in' ELSE 'out' END AS direction,
                        CASE WHEN src.usage = 'inventory' THEN sm.quantity ELSE 0.0 END AS quantity_in,
                        CASE WHEN src.usage = 'internal' THEN sm.quantity ELSE 0.0 END AS quantity_out,
                        CASE WHEN src.usage = 'inventory' THEN sm.quantity ELSE -sm.quantity END AS net_quantity,
                        1 AS move_count
                    FROM stock_move sm
                    JOIN stock_location src ON src.id = sm.location_id
                    JOIN stock_location dst ON dst.id = sm.location_dest_id
                    LEFT JOIN inventory_count_session ics
                        ON sm.reference = ics.name
                        OR sm.reference LIKE ics.name || ' - Lote %'
                    WHERE sm.state = 'done'
                      AND ((src.usage = 'inventory' AND dst.usage = 'internal')
                           OR (src.usage = 'internal' AND dst.usage = 'inventory'))
                )
            """
        )
