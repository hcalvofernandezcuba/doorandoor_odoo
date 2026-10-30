from odoo import api, fields, models, tools


class DoorandoorPickingSerialScan(models.Model):
    _inherit = "ddmh.picking.serial.scan"

    batch_id = fields.Many2one(
        "inventory.serial.label.batch",
        string="Lote físico al leer",
        readonly=True,
        copy=False,
        index=True,
        help=(
            "Conserva el lote físico del label en el momento de la lectura. "
            "Así el documento continúa asociado a su lote aunque la unidad "
            "se entregue o cambie después de ubicación."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        Serial = self.env["inventory.unit.serial"]
        for vals in vals_list:
            if vals.get("serial_id") and not vals.get("batch_id"):
                serial = Serial.browse(vals["serial_id"]).exists()
                batch = serial.current_batch_id or serial.batch_id
                vals["batch_id"] = batch.id or False
        return super().create(vals_list)


class DoorandoorBatchDocumentMovement(models.Model):
    _name = "doorandoor.batch.document.movement"
    _description = "Trazabilidad documental por lote y label"
    _auto = False
    _order = "movement_datetime desc, id desc"
    _rec_name = "picking_id"

    movement_datetime = fields.Datetime(string="Fecha y hora", readonly=True)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén del lote", readonly=True, index=True,
    )
    batch_id = fields.Many2one(
        "inventory.serial.label.batch", string="Lote/posición", readonly=True, index=True,
    )
    serial_id = fields.Many2one(
        "inventory.unit.serial", string="Label", readonly=True, index=True,
    )
    serial_code = fields.Char(string="Número de label", readonly=True, index=True)
    product_id = fields.Many2one("product.product", string="ITEM", readonly=True, index=True)
    picking_id = fields.Many2one(
        "stock.picking", string="Documento", readonly=True, index=True,
    )
    picking_type_id = fields.Many2one(
        "stock.picking.type", string="Tipo de operación", readonly=True,
    )
    document_state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("waiting", "Esperando otra operación"),
            ("confirmed", "Esperando"),
            ("assigned", "Listo"),
            ("done", "Hecho"),
            ("cancel", "Cancelado"),
        ],
        string="Estado del documento",
        readonly=True,
        index=True,
    )
    movement_kind = fields.Selection(
        [("in", "Entrada"), ("out", "Salida")],
        string="Movimiento",
        readonly=True,
        index=True,
    )
    evidence_kind = fields.Selection(
        [("scan", "Leído con Hanger"), ("reservation", "Reservado")],
        string="Evidencia",
        readonly=True,
        index=True,
    )
    quantity = fields.Float(string="Cantidad", readonly=True)
    origin = fields.Char(string="Documento de origen", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Contacto", readonly=True)
    operator_id = fields.Many2one("res.users", string="Operador", readonly=True)
    source_location_id = fields.Many2one(
        "stock.location", string="Ubicación origen", readonly=True,
    )
    destination_location_id = fields.Many2one(
        "stock.location", string="Ubicación destino", readonly=True,
    )
    source_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén origen", readonly=True,
    )
    destination_warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén destino", readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW doorandoor_batch_document_movement AS (
                WITH warehouse_locations AS (
                    SELECT
                        location.id AS location_id,
                        warehouse.id AS warehouse_id
                    FROM stock_location location
                    JOIN stock_warehouse warehouse
                      ON location.id = warehouse.view_location_id
                      OR location.parent_path LIKE
                         ('%%/' || warehouse.view_location_id::text || '/%%')
                ),
                scan_rows AS (
                    SELECT
                        (scan.id * 2)::bigint AS id,
                        COALESCE(scan.batch_id, serial.current_batch_id, serial.batch_id)
                            AS batch_id,
                        scan.serial_id,
                        serial.code AS serial_code,
                        scan.product_id,
                        scan.picking_id,
                        scan.user_id AS operator_id,
                        scan.scan_at AS evidence_datetime,
                        'scan'::varchar AS evidence_kind
                    FROM ddmh_picking_serial_scan scan
                    JOIN inventory_unit_serial serial ON serial.id = scan.serial_id
                ),
                reservation_rows AS (
                    SELECT
                        (serial.id * 2 + 1)::bigint AS id,
                        COALESCE(serial.current_batch_id, serial.batch_id) AS batch_id,
                        serial.id AS serial_id,
                        serial.code AS serial_code,
                        serial.product_id,
                        serial.reserved_picking_id AS picking_id,
                        serial.reserved_by_id AS operator_id,
                        serial.reserved_at AS evidence_datetime,
                        'reservation'::varchar AS evidence_kind
                    FROM inventory_unit_serial serial
                    WHERE serial.reserved_picking_id IS NOT NULL
                      AND COALESCE(serial.current_batch_id, serial.batch_id) IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM ddmh_picking_serial_scan scan
                          WHERE scan.picking_id = serial.reserved_picking_id
                            AND scan.serial_id = serial.id
                      )
                ),
                evidence AS (
                    SELECT * FROM scan_rows WHERE batch_id IS NOT NULL
                    UNION ALL
                    SELECT * FROM reservation_rows
                ),
                documented AS (
                    SELECT
                        evidence.*,
                        picking.company_id,
                        batch.warehouse_id,
                        picking.picking_type_id,
                        picking.state AS document_state,
                        COALESCE(picking.date_done, evidence.evidence_datetime,
                                 picking.write_date, picking.create_date)
                            AS movement_datetime,
                        picking.origin,
                        picking.partner_id,
                        picking.location_id AS source_location_id,
                        picking.location_dest_id AS destination_location_id,
                        source_warehouse.warehouse_id AS source_warehouse_id,
                        destination_warehouse.warehouse_id AS destination_warehouse_id,
                        picking_type.code AS picking_type_code
                    FROM evidence
                    JOIN stock_picking picking ON picking.id = evidence.picking_id
                    JOIN stock_picking_type picking_type
                      ON picking_type.id = picking.picking_type_id
                    JOIN inventory_serial_label_batch batch
                      ON batch.id = evidence.batch_id
                    LEFT JOIN warehouse_locations source_warehouse
                      ON source_warehouse.location_id = picking.location_id
                    LEFT JOIN warehouse_locations destination_warehouse
                      ON destination_warehouse.location_id = picking.location_dest_id
                )
                SELECT
                    documented.id,
                    documented.movement_datetime,
                    documented.company_id,
                    documented.warehouse_id,
                    documented.batch_id,
                    documented.serial_id,
                    documented.serial_code,
                    documented.product_id,
                    documented.picking_id,
                    documented.picking_type_id,
                    documented.document_state,
                    CASE
                        WHEN documented.source_warehouse_id = documented.warehouse_id
                            THEN 'out'::varchar
                        WHEN documented.destination_warehouse_id = documented.warehouse_id
                            THEN 'in'::varchar
                        WHEN documented.picking_type_code IN ('outgoing', 'internal')
                            THEN 'out'::varchar
                        ELSE 'in'::varchar
                    END AS movement_kind,
                    documented.evidence_kind,
                    1::numeric AS quantity,
                    documented.origin,
                    documented.partner_id,
                    documented.operator_id,
                    documented.source_location_id,
                    documented.destination_location_id,
                    documented.source_warehouse_id,
                    documented.destination_warehouse_id
                FROM documented
            )
        """)
