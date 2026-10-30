# -*- coding: utf-8 -*-

import json

from odoo import fields, http
from odoo.http import request


class DoorandoorCustomerDisplayController(http.Controller):

    @staticmethod
    def _ddpc_valid_record_id(record_id):
        value = str(record_id or "").strip()
        return int(value) if value.isdigit() and int(value) > 0 else False

    @http.route("/pantalla-cliente/document/leave", type="http", auth="user", methods=["POST"], csrf=False, website=False)
    def customer_display_document_leave(self, model=None, record_id=None, **kwargs):
        allowed_models = {"account.move", "sale.order"}
        record_id = self._ddpc_valid_record_id(record_id)
        if model not in allowed_models or not record_id:
            return request.make_response("{}", headers=[("Content-Type", "application/json")])
        session = request.env["doorandoor.customer.display.session"]._ddpc_for_user(
            request.env, request.env.user, request.env.company,
        )
        if session and session.active:
            session._ddpc_leave_document(model, record_id)
        return request.make_response("{}", headers=[("Content-Type", "application/json")])

    @http.route("/pantalla-cliente/session/activate", type="http", auth="user", methods=["POST"], csrf=False, website=False)
    def customer_display_session_activate(self, model=None, record_id=None, **kwargs):
        record_id = self._ddpc_valid_record_id(record_id)
        if model not in {"account.move", "sale.order"} or not record_id:
            return request.make_response("{}", headers=[("Content-Type", "application/json")])
        document = request.env[model].browse(int(record_id)).exists()
        session = request.env["doorandoor.customer.display.session"]._ddpc_for_user(
            request.env, request.env.user, request.env.company,
        )
        if document and session and session.active:
            session._ddpc_set_document(document)
        return request.make_response("{}", headers=[("Content-Type", "application/json")])

    @http.route("/pantalla-cliente/session/heartbeat", type="http", auth="user", methods=["POST"], csrf=False, website=False)
    def customer_display_session_heartbeat(self, model=None, record_id=None, **kwargs):
        record_id = self._ddpc_valid_record_id(record_id)
        if model not in {"account.move", "sale.order"} or not record_id:
            return request.make_response("{}", headers=[("Content-Type", "application/json")])
        document = request.env[model].browse(int(record_id)).exists()
        session = request.env["doorandoor.customer.display.session"]._ddpc_for_user(
            request.env, request.env.user, request.env.company,
        )
        if document and session and session.active:
            session._ddpc_heartbeat_document(document)
        return request.make_response("{}", headers=[("Content-Type", "application/json")])

    def _ddpc_get_session(self, token):
        session = request.env["doorandoor.customer.display.session"].sudo().search([
            ("token", "=", token), ("active", "=", True),
        ], limit=1)
        return session if session and session._ddpc_is_valid(token) else None

    @http.route("/pantalla-cliente/s/<string:token>", type="http", auth="public", methods=["GET"], website=False)
    def customer_display_session(self, token, **kwargs):
        session = self._ddpc_get_session(token)
        if not session:
            return request.not_found()
        return request.render("doorandoor_pantalla_cliente.customer_display", {
            "invoice": False, "token": token,
            "data_url": "/pantalla-cliente/s/%s/data" % token,
        })

    @http.route("/pantalla-cliente/s/<string:token>/data", type="http", auth="public", methods=["GET"], website=False)
    def customer_display_session_data(self, token, **kwargs):
        session = self._ddpc_get_session(token)
        if not session:
            return request.not_found()
        return request.make_response(json.dumps(session._ddpc_payload()), headers=[("Content-Type", "application/json"), ("Cache-Control", "no-store")])

    def _ddpc_get_invoice(self, invoice_id, token):
        invoice = request.env["account.move"].sudo().browse(invoice_id).exists()
        if not invoice or invoice.move_type != "out_invoice" or not invoice._ddpc_customer_display_is_valid(token):
            return None
        return invoice

    @http.route(
        "/pantalla-cliente/<int:invoice_id>/<string:token>",
        type="http", auth="public", methods=["GET"], website=False,
    )
    def customer_display(self, invoice_id, token, **kwargs):
        invoice = self._ddpc_get_invoice(invoice_id, token)
        if invoice is None:
            return request.not_found()
        return request.render("doorandoor_pantalla_cliente.customer_display", {
            "invoice": invoice,
            "token": token,
            "data_url": "/pantalla-cliente/%s/%s/data" % (invoice.id, token),
        })

    @http.route(
        "/pantalla-cliente/<int:invoice_id>/<string:token>/data",
        type="http", auth="public", methods=["GET"], website=False,
    )
    def customer_display_data(self, invoice_id, token, **kwargs):
        invoice = self._ddpc_get_invoice(invoice_id, token)
        if invoice is None:
            return request.not_found()
        return request.make_response(
            json.dumps(invoice._ddpc_customer_display_payload()),
            headers=[("Content-Type", "application/json"), ("Cache-Control", "no-store")],
        )

    @http.route("/pantalla-cliente/cotizacion/<int:order_id>/<string:token>", type="http", auth="public", methods=["GET"], website=False)
    def customer_display_sale_order(self, order_id, token, **kwargs):
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if not order or not order._ddpc_customer_display_is_valid(token):
            return request.not_found()
        return request.render("doorandoor_pantalla_cliente.customer_display", {
            "invoice": order, "token": token,
            "data_url": "/pantalla-cliente/cotizacion/%s/%s/data" % (order.id, token),
        })

    @http.route("/pantalla-cliente/cotizacion/<int:order_id>/<string:token>/data", type="http", auth="public", methods=["GET"], website=False)
    def customer_display_sale_order_data(self, order_id, token, **kwargs):
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if not order or not order._ddpc_customer_display_is_valid(token):
            return request.not_found()
        return request.make_response(json.dumps(order._ddpc_customer_display_payload()), headers=[("Content-Type", "application/json"), ("Cache-Control", "no-store")])
