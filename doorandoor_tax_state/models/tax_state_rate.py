# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DoorandoorTaxStateRate(models.Model):
    _name = "doorandoor.tax.state.rate"
    _description = "DoorAndDoor Tax State Rate"
    _order = "state_id, effective_date desc, id desc"

    active = fields.Boolean(default=True)
    state_id = fields.Many2one(
        "res.country.state",
        required=True,
        ondelete="restrict",
        domain="[('country_id.code', '=', 'US')]",
        index=True,
    )
    county_name = fields.Char(index=True)
    rate = fields.Float(required=True, digits=(16, 4))
    effective_date = fields.Date(required=True, default=fields.Date.today)
    source_url = fields.Char()
    source_note = fields.Char()
    display_name = fields.Char(compute="_compute_display_name")

    _sql_constraints = [
        (
            "doorandoor_tax_state_rate_state_county_date_unique",
            "unique(state_id, county_name, effective_date)",
            "There is already a rate for this state, county and effective date.",
        ),
    ]

    @api.depends("state_id", "county_name", "rate", "effective_date")
    def _compute_display_name(self):
        for record in self:
            parts = [record.state_id.code or record.state_id.name]
            if record.county_name:
                parts.append(record.county_name)
            record.display_name = "%s - %s%% (%s)" % (
                " / ".join(parts),
                record.rate,
                record.effective_date or "",
            )

    @api.model
    def _get_latest_rate_for_state(self, state, county_name=False):
        county_name = (county_name or "").strip()
        if county_name:
            county_rate = self.search(
                [
                    ("state_id", "=", state.id),
                    ("county_name", "=", county_name),
                    ("active", "=", True),
                ],
                limit=1,
                order="effective_date desc, id desc",
            )
            if county_rate:
                return county_rate
        return self.search(
            [
                ("state_id", "=", state.id),
                "|",
                ("county_name", "=", False),
                ("county_name", "=", ""),
                ("active", "=", True),
            ],
            limit=1,
            order="effective_date desc, id desc",
        )
