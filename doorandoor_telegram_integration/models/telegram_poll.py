import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DoorandoorTelegramPoll(models.Model):
    _name = "doorandoor.telegram.poll"
    _description = "Encuesta de aprobación por Telegram"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _check_company_auto = True

    name = fields.Char(string="Asunto", required=True, tracking=True)
    description = fields.Text(string="Pregunta / instrucciones", required=True)
    bot_id = fields.Many2one(
        "doorandoor.telegram.bot", string="Bot", required=True, check_company=True,
        domain="[('environment', '=', 'local'), ('state', '=', 'running')]",
        ondelete="restrict", tracking=True,
    )
    company_id = fields.Many2one(related="bot_id.company_id", store=True, index=True)
    state = fields.Selection(
        [("draft", "Borrador"), ("open", "En votación"),
         ("approved", "Aprobada"), ("closed", "Cerrada"), ("cancelled", "Cancelada")],
        string="Estado", default="draft", required=True, tracking=True, index=True,
    )
    deadline = fields.Datetime(string="Fecha límite", tracking=True)
    voter_ids = fields.Many2many(
        "res.users", "ddtg_poll_user_rel", "poll_id", "user_id",
        string="Votantes autorizados", required=True,
        domain="[('share', '=', False), ('active', '=', True)]",
    )
    option_ids = fields.One2many(
        "doorandoor.telegram.poll.option", "poll_id", string="Variantes", copy=True,
    )
    vote_ids = fields.One2many("doorandoor.telegram.poll.vote", "poll_id", string="Votos")
    vote_count = fields.Integer(string="Votos recibidos", compute="_compute_results")
    voter_count = fields.Integer(string="Votantes", compute="_compute_results")
    participation = fields.Float(string="Participación (%)", compute="_compute_results")
    winning_option_id = fields.Many2one(
        "doorandoor.telegram.poll.option", string="Resultado ganador",
        compute="_compute_results", store=False,
    )
    sent_at = fields.Datetime(string="Enviada", readonly=True, copy=False)
    closed_at = fields.Datetime(string="Cerrada", readonly=True, copy=False)

    @api.depends("vote_ids", "vote_ids.option_id", "voter_ids", "option_ids")
    def _compute_results(self):
        for poll in self:
            poll.vote_count = len(poll.vote_ids)
            poll.voter_count = len(poll.voter_ids)
            poll.participation = 100.0 * poll.vote_count / poll.voter_count if poll.voter_count else 0.0
            counts = {option.id: 0 for option in poll.option_ids}
            for vote in poll.vote_ids:
                counts[vote.option_id.id] = counts.get(vote.option_id.id, 0) + 1
            winner_id = max(counts, key=counts.get) if counts and max(counts.values()) else False
            poll.winning_option_id = winner_id

    @api.constrains("bot_id")
    def _check_local_bot(self):
        for poll in self:
            if poll.bot_id and poll.bot_id.environment != "local":
                raise ValidationError(_("Durante esta validación solo se permite el bot de desarrollo local."))

    def action_open_and_send(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Solo se puede enviar una encuesta en borrador."))
        if self.bot_id.state != "running":
            raise UserError(_("El bot local debe estar activo y con webhook registrado."))
        if len(self.option_ids) < 2:
            raise UserError(_("Agregue al menos dos variantes."))
        if not self.voter_ids:
            raise UserError(_("Seleccione al menos un votante autorizado."))
        links = self.env["doorandoor.telegram.user.link"].search([
            ("bot_id", "=", self.bot_id.id), ("user_id", "in", self.voter_ids.ids),
            ("state", "=", "active"),
        ])
        linked_users = links.mapped("user_id")
        missing = self.voter_ids - linked_users
        if missing:
            raise UserError(_("Estos votantes no tienen Telegram activo con el bot local: %s") % ", ".join(missing.mapped("name")))
        self.write({"state": "open", "sent_at": fields.Datetime.now()})
        for link in links:
            self._send_to_link(link)
        self.message_post(body=_("Encuesta enviada por Telegram a %s votantes.") % len(links))
        return self.bot_id._notification(_("Encuesta enviada"), _("Las variantes y botones de votación fueron enviados correctamente."))

    def _send_to_link(self, link):
        self.ensure_one()
        heading = "🗳️ %s\n\n%s" % (self.name, self.description)
        if self.deadline:
            heading += "\n\n⏰ Cierre: %s" % fields.Datetime.to_string(self.deadline)
        self.bot_id.send_message(link.telegram_chat_id, heading)
        for index, option in enumerate(self.option_ids.sorted("sequence"), 1):
            caption = "%s. %s" % (index, option.name)
            if option.description:
                caption += "\n%s" % option.description
            if option.image:
                self.bot_id.send_photo(
                    link.telegram_chat_id, base64.b64decode(option.image),
                    option.image_filename or "variante_%s.png" % index, caption,
                )
            else:
                self.bot_id.send_message(link.telegram_chat_id, caption)
        keyboard = []
        for index, option in enumerate(self.option_ids.sorted("sequence"), 1):
            keyboard.append([{
                "text": "✅ %s. %s" % (index, option.name[:35]),
                "callback_data": "ddvote:%s:%s" % (self.id, option.id),
            }])
        self.bot_id.send_message(
            link.telegram_chat_id,
            _("Seleccione una variante. Puede cambiar su voto mientras la encuesta esté abierta."),
            reply_markup={"inline_keyboard": keyboard},
        )

    def action_close(self):
        self.ensure_one()
        if self.state != "open":
            raise UserError(_("Solo se puede cerrar una encuesta abierta."))
        winner = self.winning_option_id
        self.write({
            "state": "approved" if winner else "closed",
            "closed_at": fields.Datetime.now(),
        })
        result = _("Encuesta cerrada sin votos.")
        if winner:
            result = _("Variante aprobada: %s, con %s voto(s).") % (winner.name, winner.vote_count)
        self.message_post(body=result)
        for link in self.env["doorandoor.telegram.user.link"].search([
            ("bot_id", "=", self.bot_id.id), ("user_id", "in", self.voter_ids.ids),
            ("state", "=", "active"),
        ]):
            self.bot_id.send_message(link.telegram_chat_id, "🏁 %s\n%s" % (self.name, result))
        return self.bot_id._notification(_("Encuesta cerrada"), result)

    def action_cancel(self):
        self.filtered(lambda poll: poll.state in ("draft", "open")).write({
            "state": "cancelled", "closed_at": fields.Datetime.now(),
        })
        return True

    def register_telegram_vote(self, option, telegram_user_id):
        self.ensure_one()
        if self.state != "open":
            raise ValidationError(_("La encuesta ya no acepta votos."))
        if option.poll_id != self:
            raise ValidationError(_("La variante no pertenece a esta encuesta."))
        if self.deadline and fields.Datetime.now() > self.deadline:
            raise ValidationError(_("El plazo de votación terminó."))
        link = self.env["doorandoor.telegram.user.link"].sudo().search([
            ("bot_id", "=", self.bot_id.id),
            ("telegram_user_id", "=", str(telegram_user_id or "")),
            ("state", "=", "active"),
        ], limit=1)
        if not link or link.user_id not in self.voter_ids:
            raise ValidationError(_("Su usuario no está autorizado para votar en esta encuesta."))
        vote_model = self.env["doorandoor.telegram.poll.vote"].sudo()
        vote = vote_model.search([("poll_id", "=", self.id), ("user_id", "=", link.user_id.id)], limit=1)
        values = {
            "option_id": option.id, "link_id": link.id,
            "telegram_user_id": link.telegram_user_id, "voted_at": fields.Datetime.now(),
        }
        if vote:
            vote.write(values)
        else:
            values.update({"poll_id": self.id, "user_id": link.user_id.id})
            vote = vote_model.create(values)
        self.message_post(body=_("%s seleccionó la variante %s.") % (link.user_id.name, option.name))
        return vote


class DoorandoorTelegramPollOption(models.Model):
    _name = "doorandoor.telegram.poll.option"
    _description = "Variante de encuesta Telegram"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    poll_id = fields.Many2one("doorandoor.telegram.poll", required=True, ondelete="cascade", index=True)
    name = fields.Char(string="Variante", required=True)
    description = fields.Text(string="Descripción")
    image = fields.Image(string="Imagen", required=True, max_width=2000, max_height=2000)
    image_filename = fields.Char(string="Nombre del archivo")
    vote_ids = fields.One2many("doorandoor.telegram.poll.vote", "option_id", string="Detalle de votos")
    vote_count = fields.Integer(string="Votos", compute="_compute_vote_count")

    @api.depends("vote_ids")
    def _compute_vote_count(self):
        for option in self:
            option.vote_count = len(option.vote_ids)


class DoorandoorTelegramPollVote(models.Model):
    _name = "doorandoor.telegram.poll.vote"
    _description = "Voto de aprobación Telegram"
    _order = "voted_at desc"

    poll_id = fields.Many2one("doorandoor.telegram.poll", required=True, ondelete="cascade", index=True)
    option_id = fields.Many2one("doorandoor.telegram.poll.option", required=True, ondelete="cascade", index=True)
    user_id = fields.Many2one("res.users", string="Votante", required=True, ondelete="restrict", index=True)
    link_id = fields.Many2one("doorandoor.telegram.user.link", string="Cuenta Telegram", ondelete="set null")
    telegram_user_id = fields.Char(string="ID Telegram", readonly=True)
    voted_at = fields.Datetime(string="Fecha del voto", required=True, readonly=True)

    _sql_constraints = [
        ("ddtg_poll_vote_user_unique", "unique(poll_id, user_id)", "Cada usuario puede registrar un solo voto por encuesta."),
    ]

    @api.constrains("poll_id", "option_id")
    def _check_option_poll(self):
        for vote in self:
            if vote.option_id.poll_id != vote.poll_id:
                raise ValidationError(_("La variante seleccionada no pertenece a la encuesta."))
