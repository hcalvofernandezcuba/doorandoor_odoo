from odoo import api, models


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ddsn_sync_related_invoices()
        return records

    def unlink(self):
        related_moves = self._ddsn_get_related_invoices()
        result = super().unlink()
        related_moves._ddsn_sync_release_from_payments()
        return result

    def _ddsn_sync_related_invoices(self):
        self._ddsn_get_related_invoices()._ddsn_sync_release_from_payments()

    def _ddsn_get_related_invoices(self):
        moves = (
            self.mapped("debit_move_id.move_id")
            | self.mapped("credit_move_id.move_id")
        ).filtered(lambda move: move.move_type == "out_invoice")
        return moves
