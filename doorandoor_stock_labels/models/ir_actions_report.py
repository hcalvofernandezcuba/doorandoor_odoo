from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _build_wkhtmltopdf_args(
        self,
        paperformat_id,
        landscape,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        args = super()._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        zebra_format = self.env.ref(
            "doorandoor_stock_labels.paperformat_ddsl_zebra_4x6_portrait",
            raise_if_not_found=False,
        )
        if paperformat_id != zebra_format:
            return args

        # report.paperformat stores custom dimensions as integers. A physical
        # 4 x 6 inch roll is exactly 101.6 x 152.4 mm; rounding it to 102 x 152
        # makes the printer drift progressively after several labels.
        exact_dimensions = {
            "--page-width": "101.6mm",
            "--page-height": "152.4mm",
        }
        for option, value in exact_dimensions.items():
            if option in args:
                args[args.index(option) + 1] = value
            else:
                args.extend([option, value])
        return args
