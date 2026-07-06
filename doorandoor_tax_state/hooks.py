# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


US_STATE_BASE_RATES = [
    ("AL", 4.0), ("AK", 0.0), ("AZ", 5.6), ("AR", 6.5), ("CA", 6.25),
    ("CO", 2.9), ("CT", 6.35), ("DE", 0.0), ("FL", 6.0), ("GA", 4.0),
    ("HI", 4.0), ("ID", 6.0), ("IL", 6.25), ("IN", 7.0), ("IA", 6.0),
    ("KS", 6.5), ("KY", 6.0), ("LA", 5.0), ("ME", 5.5), ("MD", 6.0),
    ("MA", 6.25), ("MI", 6.0), ("MN", 6.875), ("MS", 7.0), ("MO", 4.225),
    ("MT", 0.0), ("NE", 5.5), ("NV", 6.85), ("NH", 0.0), ("NJ", 6.625),
    ("NM", 4.875), ("NY", 4.0), ("NC", 4.75), ("ND", 5.0), ("OH", 5.75),
    ("OK", 4.5), ("OR", 0.0), ("PA", 6.0), ("RI", 7.0), ("SC", 6.0),
    ("SD", 4.2), ("TN", 7.0), ("TX", 6.25), ("UT", 4.85), ("VT", 6.0),
    ("VA", 4.3), ("WA", 6.5), ("WV", 6.0), ("WI", 5.0), ("WY", 4.0),
    ("DC", 6.0),
]

US_STATE_RATE_SOURCE = (
    "Initial statewide sales tax seed based on public published state-rate charts "
    "from Sales Tax Institute and Avalara. Editable after install."
)


def post_init_hook(env):
    if not isinstance(env, api.Environment):
        env = api.Environment(env, SUPERUSER_ID, {})
    country = env.ref("base.us", raise_if_not_found=False)
    if not country:
        return

    Rate = env["doorandoor.tax.state.rate"]
    existing = {
        (rate.state_id.id, rate.effective_date): rate
        for rate in Rate.search([("state_id.country_id", "=", country.id)])
    }
    states = {
        state.code: state
        for state in env["res.country.state"].search([("country_id", "=", country.id)])
    }

    for code, rate in US_STATE_BASE_RATES:
        state = states.get(code)
        if not state:
            continue
        key = (state.id, "2026-07-01")
        if key in existing:
            continue
        Rate.create(
            {
                "state_id": state.id,
                "rate": rate,
                "effective_date": "2026-07-01",
                "source_url": "https://www.salestaxinstitute.com/resources/rates",
                "source_note": US_STATE_RATE_SOURCE,
                "active": True,
            }
        )
