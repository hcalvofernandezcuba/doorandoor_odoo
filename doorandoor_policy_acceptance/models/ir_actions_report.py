from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _ddpa_check_commercial_report_policy(self, report_ref, res_ids):
        """Protect direct PDF/HTML report routes, not only form buttons."""
        if self.env.user.has_group("base.group_system"):
            return
        report = self._get_report(report_ref)
        if report.model not in ("sale.order", "account.move") or not res_ids:
            return
        records = self.env[report.model].browse(res_ids).exists()
        if report.model == "account.move":
            records = records.filtered(lambda move: move.move_type == "out_invoice")
        records._ddpa_require_policy_acceptance()

    def report_action(self, docids, data=None, config=True):
        ids = docids.ids if hasattr(docids, "ids") else docids
        if isinstance(ids, int):
            ids = [ids]
        self._ddpa_check_commercial_report_policy(self, ids)
        return super().report_action(docids, data=data, config=config)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        self._ddpa_check_commercial_report_policy(report_ref, res_ids)
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _render_qweb_html(self, report_ref, docids, data=None):
        self._ddpa_check_commercial_report_policy(report_ref, docids)
        return super()._render_qweb_html(report_ref, docids, data=data)
