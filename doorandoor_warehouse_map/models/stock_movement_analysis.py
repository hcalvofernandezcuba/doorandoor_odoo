from odoo import fields, models, tools


class DoorandoorStockMovementAnalysis(models.Model):
    _name = "doorandoor.stock.movement.analysis"
    _description = "Análisis de movimientos de almacén por ITEM"
    _auto = False
    _order = "movement_datetime desc, id desc"
    _rec_name = "picking_id"

    movement_date = fields.Date(string="Día", readonly=True, index=True)
    movement_datetime = fields.Datetime(string="Fecha y hora", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Almacén", readonly=True, index=True)
    aisle = fields.Char(string="Pasillo", readonly=True, index=True)
    positions = fields.Char(string="Lotes/posiciones", readonly=True)
    product_id = fields.Many2one("product.product", string="ITEM", readonly=True, index=True)
    product_category_id = fields.Many2one("product.category", string="Categoría", readonly=True)
    stock_move_id = fields.Many2one("stock.move", string="Movimiento de inventario", readonly=True)
    picking_id = fields.Many2one("stock.picking", string="Operación", readonly=True, index=True)
    picking_type_id = fields.Many2one("stock.picking.type", string="Tipo de operación", readonly=True)
    source_location_id = fields.Many2one("stock.location", string="Ubicación origen", readonly=True)
    destination_location_id = fields.Many2one("stock.location", string="Ubicación destino", readonly=True)
    operator_id = fields.Many2one("res.users", string="Operador/validador", readonly=True)
    origin = fields.Char(string="Documento de origen", readonly=True)
    quantity_in = fields.Float(string="Entradas", readonly=True)
    quantity_out = fields.Float(string="Salidas", readonly=True)
    net_quantity = fields.Float(string="Movimiento neto", readonly=True)
    current_stock = fields.Float(
        string="Existencia actual",
        readonly=True,
        group_operator="max",
        help="Labels activos y cargados actualmente en el almacén para este ITEM.",
    )
    movement_kind = fields.Selection(
        [("in", "Entrada"), ("out", "Salida")],
        string="Movimiento", readonly=True, index=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW doorandoor_stock_movement_analysis AS (
                WITH warehouse_locations AS (
                    SELECT
                        location.id AS location_id,
                        warehouse.id AS warehouse_id
                    FROM stock_location location
                    JOIN stock_warehouse warehouse
                      ON location.id = warehouse.view_location_id
                      OR location.parent_path LIKE ('%%/' || warehouse.view_location_id::text || '/%%')
                ),
                scan_meta AS (
                    SELECT
                        scan.picking_id,
                        scan.product_id,
                        string_agg(DISTINCT COALESCE(position.aisle, 'Sin pasillo identificado'), ', '
                                   ORDER BY COALESCE(position.aisle, 'Sin pasillo identificado')) AS aisle,
                        string_agg(DISTINCT batch.name, ', ' ORDER BY batch.name) AS positions
                    FROM ddmh_picking_serial_scan scan
                    JOIN inventory_unit_serial serial ON serial.id = scan.serial_id
                    JOIN inventory_serial_label_batch batch ON batch.id = serial.batch_id
                    LEFT JOIN doorandoor_warehouse_map_position position
                      ON position.warehouse_id = batch.warehouse_id
                     AND upper(position.name) = upper(batch.name)
                    GROUP BY scan.picking_id, scan.product_id
                ),
                current_balance AS (
                    SELECT
                        warehouse_location.warehouse_id,
                        quant.product_id,
                        sum(quant.quantity)::numeric AS current_stock
                    FROM stock_quant quant
                    JOIN stock_location location ON location.id = quant.location_id
                    JOIN warehouse_locations warehouse_location
                      ON warehouse_location.location_id = quant.location_id
                    WHERE location.usage = 'internal'
                    GROUP BY warehouse_location.warehouse_id, quant.product_id
                ),
                movement_base AS (
                    SELECT
                        move_line.id AS move_line_id,
                        move_line.company_id,
                        move_line.product_id,
                        product.product_tmpl_id,
                        move.id AS stock_move_id,
                        move_line.picking_id,
                        move_line.location_id AS source_location_id,
                        move_line.location_dest_id AS destination_location_id,
                        move_line.quantity,
                        COALESCE(picking.date_done, move.date, move_line.write_date) AS movement_datetime,
                        picking.picking_type_id,
                        COALESCE(picking.origin, move.reference) AS origin,
                        COALESCE(picking.ddmh_validated_by_id, picking.write_uid) AS operator_id,
                        source_warehouse.warehouse_id AS source_warehouse_id,
                        destination_warehouse.warehouse_id AS destination_warehouse_id,
                        COALESCE(scan_meta.aisle, 'Sin pasillo identificado') AS aisle,
                        scan_meta.positions
                    FROM stock_move_line move_line
                    JOIN stock_move move ON move.id = move_line.move_id
                    LEFT JOIN stock_picking picking ON picking.id = move_line.picking_id
                    JOIN product_product product ON product.id = move_line.product_id
                    LEFT JOIN warehouse_locations source_warehouse
                           ON source_warehouse.location_id = move_line.location_id
                    LEFT JOIN warehouse_locations destination_warehouse
                           ON destination_warehouse.location_id = move_line.location_dest_id
                    LEFT JOIN scan_meta
                           ON scan_meta.picking_id = move_line.picking_id
                          AND scan_meta.product_id = move_line.product_id
                    WHERE move.state = 'done'
                      AND (picking.id IS NULL OR picking.state = 'done')
                      AND move_line.quantity != 0
                      AND (source_warehouse.warehouse_id IS NOT NULL
                           OR destination_warehouse.warehouse_id IS NOT NULL)
                ),
                warehouse_perspective AS (
                    SELECT
                        (movement.move_line_id * 2)::bigint AS id,
                        movement.*,
                        movement.source_warehouse_id AS warehouse_id,
                        'out'::varchar AS movement_kind,
                        0::numeric AS quantity_in,
                        movement.quantity::numeric AS quantity_out,
                        (-movement.quantity)::numeric AS net_quantity
                    FROM movement_base movement
                    WHERE movement.source_warehouse_id IS NOT NULL

                    UNION ALL

                    SELECT
                        (movement.move_line_id * 2 + 1)::bigint AS id,
                        movement.*,
                        movement.destination_warehouse_id AS warehouse_id,
                        'in'::varchar AS movement_kind,
                        movement.quantity::numeric AS quantity_in,
                        0::numeric AS quantity_out,
                        movement.quantity::numeric AS net_quantity
                    FROM movement_base movement
                    WHERE movement.destination_warehouse_id IS NOT NULL
                )
                SELECT
                    perspective.id,
                    perspective.movement_datetime::date AS movement_date,
                    perspective.movement_datetime,
                    perspective.company_id,
                    perspective.warehouse_id,
                    perspective.aisle,
                    perspective.positions,
                    perspective.product_id,
                    template.categ_id AS product_category_id,
                    perspective.stock_move_id,
                    perspective.picking_id,
                    perspective.picking_type_id,
                    perspective.source_location_id,
                    perspective.destination_location_id,
                    perspective.operator_id,
                    perspective.origin,
                    perspective.quantity_in,
                    perspective.quantity_out,
                    perspective.net_quantity,
                    COALESCE(balance.current_stock, 0)::numeric AS current_stock,
                    perspective.movement_kind
                FROM warehouse_perspective perspective
                JOIN product_product product ON product.id = perspective.product_id
                JOIN product_template template ON template.id = product.product_tmpl_id
                LEFT JOIN current_balance balance
                       ON balance.warehouse_id = perspective.warehouse_id
                      AND balance.product_id = perspective.product_id
            )
        """)
