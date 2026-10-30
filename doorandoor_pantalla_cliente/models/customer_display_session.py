# -*- coding: utf-8 -*-

import secrets

from odoo import fields, models


class DoorandoorCustomerDisplaySession(models.Model):
    """Persistent public endpoint for a seller's customer screen."""

    _name = "doorandoor.customer.display.session"
    _description = "Sesión de pantalla de cliente"
    _order = "write_date desc, id desc"

    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", required=True, index=True, ondelete="cascade")
    token = fields.Char(required=True, readonly=True, index=True, copy=False)
    active = fields.Boolean(default=True, index=True)
    expires_at = fields.Datetime(required=True, readonly=True)
    document_model = fields.Selection([("account.move", "Factura"), ("sale.order", "Cotización")], readonly=True)
    document_id = fields.Integer(readonly=True)
    document_seen_at = fields.Datetime(readonly=True)
    city_rule_id = fields.Many2one("doorandoor.tax.state.rule", readonly=True)

    _sql_constraints = [
        ("ddpc_unique_session_per_user_company", "unique(user_id, company_id)",
         "Solo puede existir una pantalla de cliente por usuario y compañía."),
    ]

    @staticmethod
    def _ddpc_expiry():
        return fields.Datetime.add(fields.Datetime.now(), hours=18)

    @classmethod
    def _ddpc_for_user(cls, env, user=None, company=None):
        user, company = user or env.user, company or env.company
        return env[cls._name].sudo().search([("user_id", "=", user.id), ("company_id", "=", company.id)], limit=1)

    @classmethod
    def _ddpc_start_for_user(cls, env, user=None, company=None):
        user, company = user or env.user, company or env.company
        session = cls._ddpc_for_user(env, user, company)
        values = {"active": True, "expires_at": cls._ddpc_expiry()}
        if not session:
            values.update({"user_id": user.id, "company_id": company.id, "token": secrets.token_urlsafe(32)})
            session = env[cls._name].sudo().create(values)
        else:
            session.sudo().write(values)
        return session

    def _ddpc_is_valid(self, token):
        self.ensure_one()
        return bool(self.active and self.token and token and secrets.compare_digest(self.token, token)
                    and self.expires_at and self.expires_at >= fields.Datetime.now())

    def _ddpc_set_document(self, document):
        self.ensure_one()
        city = document.ddts_tax_city_rule_id if "ddts_tax_city_rule_id" in document._fields else False
        self.sudo().write({"document_model": document._name, "document_id": document.id,
                           "city_rule_id": city.id if city else False, "active": True,
                           "expires_at": self._ddpc_expiry(),
                           "document_seen_at": fields.Datetime.now()})

    def _ddpc_heartbeat_document(self, document):
        """Keep a document on the customer screen while its backend form is open.

        Odoo can cache form components while changing actions.  In that case an
        unmount event is not guaranteed, so the public screen must also have a
        short, server-side presence timeout instead of relying on that event.
        """
        self.ensure_one()
        if self.document_model == document._name and self.document_id == document.id:
            self.sudo().write({"document_seen_at": fields.Datetime.now(), "expires_at": self._ddpc_expiry()})

    def _ddpc_leave_document(self, model, record_id):
        self.ensure_one()
        # Form navigation is asynchronous; an old form must never clear a newer one.
        if self.document_model == model and self.document_id == int(record_id):
            self.sudo().write({"document_model": False, "document_id": False, "document_seen_at": False})

    def _ddpc_payload(self):
        self.ensure_one()
        # A missing heartbeat means the salesperson has left the form.  Five
        # seconds tolerates a short network delay while keeping the client
        # display responsive when Odoo caches the departing form component.
        if self.document_model and self.document_seen_at:
            deadline = fields.Datetime.add(self.document_seen_at, seconds=5)
            if deadline < fields.Datetime.now():
                self.sudo().write({"document_model": False, "document_id": False, "document_seen_at": False})
        document = self.env[self.document_model].sudo().browse(self.document_id).exists() if self.document_model and self.document_id else False
        if document:
            return document.with_context(ddpc_session_display=True)._ddpc_customer_display_payload()
        promotions = self.env["doorandoor.customer.display.promotion"].sudo()._ddpc_active_for_city(self.company_id, self.city_rule_id)
        return {"mode": "promotion", "city": self.city_rule_id.county_name or "Door&Door",
                "promotions": [promotion._ddpc_as_payload() for promotion in promotions]}
