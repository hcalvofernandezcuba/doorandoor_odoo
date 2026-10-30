from odoo import _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup, escape


class DoorandoorHelpdeskTicket(models.Model):
    _name = "doorandoor.helpdesk.ticket"
    _description = "Ticket de soporte técnico DoorAndDoor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Ticket", default=lambda self: _("Nuevo"), readonly=True,
        copy=False, index=True,
    )
    title = fields.Char(string="Asunto", required=True, tracking=True)
    description = fields.Html(string="Descripción", required=True)
    state = fields.Selection(
        [
            ("new", "Nuevo"),
            ("analysis", "En análisis"),
            ("waiting", "Esperando al usuario"),
            ("resolved", "Resuelto"),
            ("closed", "Cerrado"),
            ("cancel", "Cancelado"),
        ],
        default="new", required=True, tracking=True, index=True,
        group_expand="_group_expand_states",
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Importante"), ("2", "Urgente"), ("3", "Crítica")],
        default="0", required=True, tracking=True, index=True,
    )
    requester_id = fields.Many2one(
        "res.users", string="Originado por", required=True,
        default=lambda self: self.env.user, tracking=True, index=True,
    )
    received_by_id = fields.Many2one(
        "res.users", string="Recibido / registrado por", required=True,
        default=lambda self: self.env.user, readonly=True, tracking=True,
        index=True, copy=False,
    )
    request_channel = fields.Selection(
        [
            ("odoo_chat", "Chat interno de Odoo"),
            ("external_chat", "Chat externo"),
            ("phone", "Teléfono"),
            ("email", "Correo electrónico"),
            ("in_person", "Presencial"),
            ("system", "Generado desde el sistema"),
            ("other", "Otro"),
        ],
        string="Canal de recepción", required=True, default="other",
        tracking=True, index=True,
    )
    assigned_user_id = fields.Many2one(
        "res.users", string="Técnico responsable", tracking=True, index=True,
        domain="[('share','=',False)]",
    )
    office_id = fields.Many2one(
        "doorandoor.commercial.office", string="Oficina",
        default=lambda self: self.env.user.ddco_office_id,
        tracking=True, index=True, check_company=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Almacén",
        default=lambda self: self.env.user.ddco_office_id.operational_warehouse_id,
        tracking=True, index=True, check_company=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True,
    )
    affected_area = fields.Selection(
        [
            ("sales", "Ventas"),
            ("invoicing", "Facturación"),
            ("payments", "Pagos / Caja"),
            ("inventory", "Inventario"),
            ("hanger", "Hanger"),
            ("website", "Website"),
            ("accounting", "Contabilidad"),
            ("manufacturing", "Manufactura"),
            ("access", "Permisos / Acceso"),
            ("other", "Otro"),
        ],
        string="Área afectada", required=True, default="other",
        tracking=True, index=True,
    )
    model_name = fields.Char(string="Modelo técnico", readonly=True, copy=False)
    record_id = fields.Integer(string="ID del registro", readonly=True, copy=False)
    source_display_name = fields.Char(string="Documento afectado", readonly=True, copy=False)
    current_url = fields.Char(string="Pantalla / URL", readonly=True, copy=False)
    error_details = fields.Text(string="Detalle técnico", copy=False)
    user_action_required = fields.Boolean(
        string="Requiere acción del usuario", tracking=True, copy=False,
    )
    required_action = fields.Text(
        string="Acción requerida al usuario", tracking=True, copy=False,
        help=(
            "Instrucción concreta que debe completar el usuario para continuar "
            "o cerrar la solución del ticket."
        ),
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", "ddhd_ticket_attachment_rel", "ticket_id", "attachment_id",
        string="Evidencias", copy=False,
    )
    analysis_started_at = fields.Datetime(string="Inicio del análisis", readonly=True, copy=False)
    resolved_at = fields.Datetime(string="Resuelto el", readonly=True, copy=False)
    resolution_notified_at = fields.Datetime(
        string="Solución notificada el", readonly=True, copy=False,
    )
    closed_at = fields.Datetime(string="Cerrado el", readonly=True, copy=False)
    solution_hours = fields.Float(
        string="Tiempo de solución (h)", compute="_compute_solution_efficiency",
        store=True, aggregator="avg", copy=False,
        help=(
            "Horas transcurridas desde el inicio del análisis, o desde la "
            "creación si no se registró ese inicio, hasta marcar la solución."
        ),
    )
    solution_efficiency = fields.Selection(
        [
            ("excellent", "Excelente (hasta 4 h)"),
            ("good", "Buena (hasta 24 h)"),
            ("attention", "Requiere atención (hasta 72 h)"),
            ("delayed", "Demorada (más de 72 h)"),
        ],
        string="Eficiencia de solución", compute="_compute_solution_efficiency",
        store=True, copy=False, index=True,
    )

    @api.depends("create_date", "analysis_started_at", "resolved_at")
    def _compute_solution_efficiency(self):
        for ticket in self:
            if not ticket.resolved_at:
                ticket.solution_hours = 0.0
                ticket.solution_efficiency = False
                continue
            started_at = ticket.analysis_started_at or ticket.create_date
            hours = max(
                (ticket.resolved_at - started_at).total_seconds() / 3600.0,
                0.0,
            )
            ticket.solution_hours = hours
            if hours <= 4:
                ticket.solution_efficiency = "excellent"
            elif hours <= 24:
                ticket.solution_efficiency = "good"
            elif hours <= 72:
                ticket.solution_efficiency = "attention"
            else:
                ticket.solution_efficiency = "delayed"

    @api.model
    def _group_expand_states(self, states, domain):
        """Keep the complete support workflow visible even with empty stages."""
        return [key for key, _label in self._fields["state"].selection]

    def _is_support_manager(self):
        return bool(
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group("doorandoor_helpdesk.group_ddhd_manager")
        )

    def _check_state_change_access(self, target_state=None):
        if self._is_support_manager():
            return True
        is_technician = self.env.user.has_group(
            "doorandoor_helpdesk.group_ddhd_technician"
        )
        for ticket in self:
            may_claim = target_state == "analysis" and not ticket.assigned_user_id
            is_assigned = ticket.assigned_user_id == self.env.user
            if not is_technician or not (may_claim or is_assigned):
                raise UserError(_(
                    "Solo un administrador, un responsable de soporte o el técnico "
                    "asignado puede cambiar el estado del ticket."
                ))
        return True

    def _check_close_confirmation(self):
        if self._is_support_manager():
            return True
        for ticket in self:
            if ticket.state != "resolved":
                raise UserError(_(
                    "El ticket debe estar resuelto y notificado antes de cerrarse."
                ))
            if ticket.requester_id != self.env.user:
                raise UserError(_(
                    "Solo la persona que originó el ticket, un administrador o "
                    "un responsable de soporte puede cerrarlo."
                ))
        return True

    def write(self, vals):
        previous_states = {
            ticket.id: ticket.state for ticket in self
        } if "state" in vals else {}
        if {"user_action_required", "required_action"}.intersection(vals) and not self._is_support_manager():
            is_technician = self.env.user.has_group(
                "doorandoor_helpdesk.group_ddhd_technician"
            )
            if not is_technician or any(
                ticket.assigned_user_id != self.env.user for ticket in self
            ):
                raise UserError(_(
                    "Solo soporte asignado o un administrador puede definir "
                    "la acción requerida al usuario."
                ))
        if "state" in vals:
            if vals.get("state") == "closed":
                self._check_close_confirmation()
            else:
                self._check_state_change_access(vals.get("state"))
        if "assigned_user_id" in vals and not self._is_support_manager():
            for ticket in self:
                claiming_self = (
                    not ticket.assigned_user_id
                    and vals.get("assigned_user_id") == self.env.user.id
                )
                if not claiming_self:
                    raise UserError(_(
                        "Solo un administrador o responsable de soporte puede "
                        "reasignar un ticket."
                    ))
        result = super().write(vals)
        if "state" in vals:
            system_author = self.env.ref("base.user_root").partner_id
            state_labels = dict(self._fields["state"].selection)
            actor = self.env.user.display_name
            for ticket in self:
                previous_state = previous_states.get(ticket.id)
                if previous_state == ticket.state:
                    continue
                recipients = (
                    ticket.requester_id.partner_id
                    | ticket.received_by_id.partner_id
                )
                ticket.message_post(
                    body=_(
                        "Estado actualizado: %(previous)s → %(current)s. "
                        "Cambio realizado por %(actor)s."
                    ) % {
                        "previous": state_labels.get(previous_state, previous_state),
                        "current": state_labels.get(ticket.state, ticket.state),
                        "actor": actor,
                    },
                    author_id=system_author.id,
                    partner_ids=recipients.ids,
                    subtype_xmlid="mail.mt_comment",
                )
        action_was_updated = bool(
            {"user_action_required", "required_action"}.intersection(vals)
        )
        for ticket in self.filtered("user_action_required"):
            if not action_was_updated or not (ticket.required_action or "").strip():
                continue
            recipients = ticket.requester_id.partner_id
            ticket.message_post(
                body=Markup("<strong>%s</strong><br/>%s") % (
                    escape(_("Acción requerida para continuar:")),
                    escape(ticket.required_action).replace("\n", Markup("<br/>")),
                ),
                partner_ids=recipients.ids,
                subtype_xmlid="mail.mt_comment",
            )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code("doorandoor.helpdesk.ticket") or _("Nuevo")
            requester = self.env["res.users"].browse(vals.get("requester_id") or self.env.user.id)
            vals.setdefault("company_id", requester.company_id.id)
            vals.setdefault("office_id", requester.ddco_office_id.id)
            vals.setdefault(
                "warehouse_id", requester.ddco_office_id.operational_warehouse_id.id
            )
        tickets = super().create(vals_list)
        for ticket in tickets:
            ticket.message_post(body=_("Ticket creado por %s.") % ticket.requester_id.display_name)
        return tickets

    def action_start_analysis(self):
        self._check_state_change_access("analysis")
        for ticket in self:
            if ticket.state in ("resolved", "closed", "cancel"):
                raise UserError(_("No se puede iniciar el análisis de un ticket terminado."))
            values = {"state": "analysis", "assigned_user_id": self.env.user.id}
            if not ticket.analysis_started_at:
                values["analysis_started_at"] = fields.Datetime.now()
            ticket.write(values)
        return True

    def action_waiting(self):
        self._check_state_change_access("waiting")
        missing_action = self.filtered(
            lambda ticket: not (ticket.required_action or "").strip()
        )
        if missing_action:
            raise UserError(_(
                "Antes de esperar respuesta debe escribir la acción concreta "
                "que necesita realizar el usuario."
            ))
        self.write({
            "user_action_required": True,
            "state": "waiting",
        })
        return True

    def action_resolve(self):
        self._check_state_change_access("resolved")
        now = fields.Datetime.now()
        self.write({
            "state": "resolved",
            "user_action_required": False,
            "resolved_at": now,
            "resolution_notified_at": now,
        })
        for ticket in self:
            ticket.message_post(
                body=_(
                    "La solución fue marcada como resuelta. %(requester)s debe "
                    "revisarla y confirmar el cierre del ticket."
                ) % {"requester": ticket.requester_id.display_name},
                partner_ids=ticket.requester_id.partner_id.ids,
                subtype_xmlid="mail.mt_comment",
            )
        return True

    def action_confirm_required_action(self):
        """Let the requester report completion without closing the ticket."""
        actor = self.env.user
        for ticket in self:
            if ticket.state != "waiting" or not ticket.user_action_required:
                raise UserError(_(
                    "Solo puede confirmar una acción pendiente en un ticket "
                    "que esté esperando al usuario."
                ))
            if ticket.requester_id != actor and not ticket._is_support_manager():
                raise UserError(_(
                    "Solo la persona que originó el ticket puede confirmar "
                    "que realizó la acción solicitada."
                ))

            # This transition is intentionally available to the requester. Use
            # the base write to avoid granting general support state privileges.
            super(DoorandoorHelpdeskTicket, ticket.sudo()).write({
                "state": "analysis",
                "user_action_required": False,
            })
            recipients = (
                ticket.assigned_user_id.partner_id
                | ticket.received_by_id.partner_id
            ) - actor.partner_id
            ticket.sudo().message_post(
                body=_(
                    "%(requester)s confirmó que realizó la acción solicitada. "
                    "El ticket vuelve a análisis para que Soporte verifique "
                    "el resultado."
                ) % {"requester": actor.display_name},
                author_id=actor.partner_id.id,
                partner_ids=recipients.ids,
                subtype_xmlid="mail.mt_comment",
            )
        return True

    def action_close(self):
        self._check_close_confirmation()
        self.write({"state": "closed", "closed_at": fields.Datetime.now()})
        for ticket in self:
            ticket.message_post(
                body=_("Solución aceptada y ticket cerrado por %s.")
                % self.env.user.display_name,
            )
        return True

    def action_reopen(self):
        self._check_state_change_access("analysis")
        self.write({
            "state": "analysis",
            "resolved_at": False,
            "resolution_notified_at": False,
            "closed_at": False,
        })
        return True
