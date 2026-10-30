from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DoorAndDoorHistoricNextOperationWizard(models.TransientModel):
    _name = "doorandoor.historic.next.operation.wizard"
    _description = "Seleccionar siguiente operación de la factura histórica"

    historical_delivery_id = fields.Many2one(
        "doorandoor.historical.delivery",
        string="Factura histórica",
        readonly=True,
    )
    available_source_operation_ids = fields.Many2many(
        "stock.picking",
        compute="_compute_available_source_operations",
    )
    source_operation_id = fields.Many2one(
        "stock.picking",
        string="Recepción confirmada",
        required=True,
        domain="[('id', 'in', available_source_operation_ids)]",
        help="Recepción confirmada que contiene la mercancía y los labels de esta factura.",
    )
    operation_kind = fields.Selection(
        [
            ("internal", "Traslado interno"),
            ("delivery", "Entrega al cliente"),
        ],
        string="Siguiente operación",
        required=True,
        default="delivery",
    )
    source_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén de origen",
        compute="_compute_source_warehouse",
        readonly=True,
    )
    destination_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacén de destino",
        domain=lambda self: self.env["doorandoor.historical.delivery"]._warehouse_domain(),
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
    )
    destination_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación de destino",
        domain="[('usage', '=', 'internal'), ('warehouse_id', '=', destination_warehouse_id)]",
    )
    line_summary = fields.Text(
        string="Productos y cantidades",
        compute="_compute_line_summary",
        readonly=True,
    )

    @api.depends("historical_delivery_id", "source_operation_id")
    def _compute_available_source_operations(self):
        for wizard in self:
            if wizard.historical_delivery_id:
                regularizations = wizard.historical_delivery_id.ddhl_regularization_ids.filtered(
                    lambda record: (
                        record.state == "done"
                        and record.destination_mode == "predispatch"
                        and record.picking_id.state == "done"
                    )
                )
                wizard.available_source_operation_ids = regularizations.mapped("picking_id")
            else:
                wizard.available_source_operation_ids = wizard.source_operation_id

    @api.depends("source_operation_id")
    def _compute_source_warehouse(self):
        for wizard in self:
            wizard.source_warehouse_id = (
                wizard.source_operation_id.location_dest_id.warehouse_id
                or wizard.source_operation_id.picking_type_id.warehouse_id
            )

    @api.depends(
        "historical_delivery_id.line_ids.product_id",
        "historical_delivery_id.line_ids.quantity",
    )
    def _compute_line_summary(self):
        for wizard in self:
            if wizard.historical_delivery_id:
                lines = (
                    (line.product_id, line.quantity)
                    for line in wizard.historical_delivery_id.line_ids
                )
            else:
                lines = (
                    (
                        move.product_id,
                        move.quantity if move.state == "done" else move.product_uom_qty,
                    )
                    for move in wizard.source_operation_id.move_ids.filtered(
                        lambda move: move.state != "cancel"
                    )
                )
            wizard.line_summary = "\n".join(
                "%s × %s" % (product.display_name, quantity)
                for product, quantity in lines if quantity > 0
            )

    @api.onchange("historical_delivery_id", "operation_kind")
    def _onchange_historical_operation(self):
        if self.historical_delivery_id:
            self.destination_warehouse_id = self.historical_delivery_id.warehouse_id
            self.partner_id = self.historical_delivery_id.partner_id
        elif self.source_operation_id:
            self.destination_warehouse_id = self.source_warehouse_id
            self.partner_id = self.source_operation_id.partner_id
        if self.destination_warehouse_id:
            self.destination_location_id = self.destination_warehouse_id.lot_stock_id
        if not self.source_operation_id and self.available_source_operation_ids:
            self.source_operation_id = self.available_source_operation_ids[:1]

    @api.onchange("destination_warehouse_id")
    def _onchange_destination_warehouse(self):
        self.destination_location_id = self.destination_warehouse_id.lot_stock_id

    def _operation_lines(self):
        self.ensure_one()
        if self.historical_delivery_id:
            return [
                (line.product_id, line.product_uom_id, line.quantity)
                for line in self.historical_delivery_id.line_ids
                if line.quantity > 0
            ]
        return [
            (
                move.product_id,
                move.product_uom,
                move.quantity if move.state == "done" else move.product_uom_qty,
            )
            for move in self.source_operation_id.move_ids.filtered(
                lambda move: move.state != "cancel"
            )
            if (move.quantity if move.state == "done" else move.product_uom_qty) > 0
        ]

    def _check_ready_source(self):
        self.ensure_one()
        history = self.historical_delivery_id
        if not self.source_operation_id:
            raise UserError(_("Seleccione el documento que contiene la mercancía."))
        if not self._operation_lines():
            raise UserError(_(
                "El documento de origen no contiene cantidades disponibles para copiar."
            ))
        if not history:
            return self.env["doorandoor.historic.regularization"]
        if history.picking_id or history.transfer_dispatch_id:
            raise UserError(_(
                "La factura histórica ya tiene una entrega o traslado creado. "
                "Use Operaciones del ciclo para abrirlo."
            ))
        if not history.line_ids:
            raise UserError(_("La factura histórica no contiene productos."))
        if self.source_operation_id not in self.available_source_operation_ids:
            raise UserError(_(
                "Seleccione una recepción confirmada de esta misma factura histórica."
            ))
        regularization = history.ddhl_regularization_ids.filtered(
            lambda record: record.picking_id == self.source_operation_id
        )
        if len(regularization) != 1:
            raise UserError(_(
                "No se pudo identificar una única recepción histórica para continuar."
            ))
        pending = history.line_ids.filtered(
            lambda line: line.ddhl_regularized_qty + 1e-6 < line.quantity
        )
        if pending:
            raise UserError(_(
                "Confirme primero todas las cantidades de la recepción: %s"
            ) % ", ".join(
                "%s (faltan %.2f)" % (
                    line.product_id.display_name,
                    line.quantity - line.ddhl_regularized_qty,
                )
                for line in pending
            ))
        return regularization

    def _create_internal_transfer(self, regularization):
        self.ensure_one()
        history = self.historical_delivery_id
        source_warehouse = self.source_warehouse_id
        destination_warehouse = self.destination_warehouse_id
        if not destination_warehouse:
            raise ValidationError(_("Seleccione el almacén de destino."))
        picking_type = source_warehouse.int_type_id
        source = (
            regularization.destination_location_id
            if regularization
            else self.source_operation_id.location_dest_id
        )
        destination = self.destination_location_id or destination_warehouse.lot_stock_id
        if not picking_type or not source or not destination:
            raise UserError(_(
                "El origen o el destino no tiene configurado el traslado interno."
            ))
        if source == destination:
            raise ValidationError(_(
                "La ubicación de destino debe ser diferente a la ubicación de origen."
            ))
        company = history.company_id if history else self.source_operation_id.company_id
        origin = (
            _("Factura histórica %(control)s / %(reference)s") % {
                "control": history.display_name,
                "reference": history.external_reference,
            }
            if history
            else _("Continuación de %(operation)s") % {
                "operation": self.source_operation_id.display_name,
            }
        )
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "origin": origin,
            "scheduled_date": fields.Datetime.now(),
            "company_id": company.id,
            "ddpc_transfer_target_location_id": destination.id,
            "ddhl_source_operation_id": self.source_operation_id.id,
        })
        for product, uom, quantity in self._operation_lines():
            self.env["stock.move"].create({
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": uom.id,
                "picking_id": picking.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "company_id": company.id,
            })
        picking.action_confirm()
        picking.action_assign()
        if history:
            history.write({
                "warehouse_id": destination_warehouse.id,
                "transfer_dispatch_id": picking.id,
                "state": "transfer_pending",
            })
        if regularization:
            regularization._ddhl_reserve_received_labels(picking)
        return picking

    def _create_customer_delivery(self, regularization):
        self.ensure_one()
        history = self.historical_delivery_id
        if self.destination_warehouse_id and self.destination_warehouse_id != self.source_warehouse_id:
            raise ValidationError(_(
                "La mercancía está en %(source)s. Para entregar desde %(destination)s, "
                "cree primero un traslado interno."
            ) % {
                "source": self.source_warehouse_id.display_name,
                "destination": self.destination_warehouse_id.display_name,
            })
        if not self.partner_id:
            raise ValidationError(_("Seleccione el cliente de la entrega."))
        if history:
            if history.warehouse_id != self.source_warehouse_id:
                history.write({"warehouse_id": self.source_warehouse_id.id})
            picking = history._create_customer_delivery()
            picking.write({"ddhl_source_operation_id": self.source_operation_id.id})
            history.write({"picking_id": picking.id, "state": "ready"})
            regularization._ddhl_reserve_received_labels(picking)
            history._post_release_audit(picking)
            return picking

        source = self.source_operation_id.location_dest_id
        warehouse = self.source_warehouse_id
        picking_type = warehouse.out_type_id
        destination = self.partner_id.property_stock_customer
        if not source or source.usage != "internal" or not picking_type or not destination:
            raise UserError(_(
                "El documento, almacén o cliente no tiene configurada la entrega."
            ))
        picking = self.env["stock.picking"].create({
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "origin": _("Continuación de %(operation)s") % {
                "operation": self.source_operation_id.display_name,
            },
            "scheduled_date": fields.Datetime.now(),
            "company_id": self.source_operation_id.company_id.id,
            "ddhl_source_operation_id": self.source_operation_id.id,
        })
        for product, uom, quantity in self._operation_lines():
            self.env["stock.move"].create({
                "name": product.display_name,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom": uom.id,
                "picking_id": picking.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "company_id": self.source_operation_id.company_id.id,
            })
        picking.action_confirm()
        picking.action_assign()
        return picking

    def action_create_operation(self):
        self.ensure_one()
        regularization = self._check_ready_source()
        if self.operation_kind == "internal":
            picking = self._create_internal_transfer(regularization)
            operation_label = _("Traslado interno")
        else:
            picking = self._create_customer_delivery(regularization)
            operation_label = _("Entrega al cliente")

        history = self.historical_delivery_id
        body = Markup(
            "<p><strong>Siguiente operación creada desde el panel histórico.</strong></p>"
            "<p>Tipo: %(kind)s<br/>Factura histórica: %(history)s / %(reference)s<br/>"
            "Recepción origen: %(source)s<br/>Nueva operación: %(operation)s<br/>"
            "Productos copiados automáticamente: %(lines)s.<br/>Creada por: %(user)s.</p>"
        ) % {
            "kind": escape(operation_label),
            "history": escape(history.display_name if history else _("No aplica")),
            "reference": escape(history.external_reference if history else _("Documento operativo")),
            "source": escape(self.source_operation_id.display_name),
            "operation": escape(picking.display_name),
            "lines": len(self._operation_lines()),
            "user": escape(self.env.user.display_name),
        }
        if history:
            history.message_post(body=body)
        self.source_operation_id.message_post(body=body)
        picking.message_post(body=body)
        if history:
            history._ddhl_invalidate_linked_operation_cache()
            return history.get_formview_action()
        return self.source_operation_id.get_formview_action()
