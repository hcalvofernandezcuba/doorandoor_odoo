from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        if report.report_name in (
            "account.report_invoice",
            "account.report_invoice_with_payments",
        ) and res_ids:
            self.env["account.move"].browse(res_ids).exists()._ddipg_check_printable_invoice()
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
