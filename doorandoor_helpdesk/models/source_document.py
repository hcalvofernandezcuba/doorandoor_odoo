from odoo import _, models


def _ddhd_ticket_action(record, area, office=False, warehouse=False):
    record.ensure_one()
    office = office or record.env.user.ddco_office_id
    warehouse = warehouse or office.operational_warehouse_id
    base_url = record.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
    return {
        "type": "ir.actions.act_window",
        "name": _("Crear ticket de soporte"),
        "res_model": "doorandoor.helpdesk.ticket",
        "view_mode": "form",
        "target": "current",
        "context": {
            "default_title": _("Soporte requerido en %s") % record.display_name,
            "default_requester_id": record.env.user.id,
            "default_office_id": office.id,
            "default_warehouse_id": warehouse.id,
            "default_affected_area": area,
            "default_request_channel": "system",
            "default_model_name": record._name,
            "default_record_id": record.id,
            "default_source_display_name": record.display_name,
            "default_current_url": "%s/web#id=%s&model=%s&view_type=form" % (
                base_url, record.id, record._name,
            ),
            "default_description": _(
                "Explique qué intentaba hacer, qué ocurrió y qué resultado esperaba."
            ),
        },
    }


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_ddhd_create_ticket(self):
        self.ensure_one()
        office = self.ddco_office_id or self.user_id.ddco_office_id
        return _ddhd_ticket_action(self, "sales", office, self.warehouse_id)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_ddhd_create_ticket(self):
        self.ensure_one()
        sale_order = self.sale_order_id or self.invoice_line_ids.sale_line_ids.order_id[:1]
        office = (
            self.ddco_office_id
            or sale_order.ddco_office_id
            or self.invoice_user_id.ddco_office_id
        )
        warehouse = (
            office.operational_warehouse_id
            or sale_order.warehouse_id
            or self.invoice_line_ids.ddsn_supply_warehouse_id[:1]
        )
        return _ddhd_ticket_action(self, "invoicing", office, warehouse)


class InventoryCountSession(models.Model):
    _inherit = "inventory.count.session"

    def action_ddhd_create_ticket(self):
        self.ensure_one()
        return _ddhd_ticket_action(
            self, "inventory", warehouse=self.location_id.warehouse_id
        )


class InventorySerialLabelBatch(models.Model):
    _inherit = "inventory.serial.label.batch"

    def action_ddhd_create_ticket(self):
        self.ensure_one()
        return _ddhd_ticket_action(self, "inventory", warehouse=self.warehouse_id)
