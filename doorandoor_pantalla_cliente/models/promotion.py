# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DoorandoorCustomerDisplayPromotion(models.Model):
    _name = "doorandoor.customer.display.promotion"
    _description = "Promoción pantalla de cliente"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    city_rule_id = fields.Many2one(
        "doorandoor.tax.state.rule", string="Ciudad / sucursal",
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        help="Vacío = promoción general. Con una ciudad, solo aparece en esa sucursal.",
    )
    media_type = fields.Selection([("image", "Imagen"), ("video", "Video")], default="image", required=True)
    display_seconds = fields.Integer(string="Duración en pantalla (segundos)", default=10, required=True)
    date_start = fields.Date(string="Válida desde")
    date_end = fields.Date(string="Válida hasta")
    conditions = fields.Text(string="Texto y condiciones", help="Texto comercial o condiciones visibles para el cliente.")
    image = fields.Image(max_width=1920, max_height=1080)
    video = fields.Binary(attachment=True)
    video_filename = fields.Char()
    video_mimetype = fields.Char(default="video/mp4")

    def ddpc_set_media_from_attachment(self, attachment_id, media_type):
        """Copy an item selected with Website's media library to this campaign.

        The media dialog stores uploads as ``ir.attachment`` records.  Keeping
        the campaign fields binary makes the public customer screen independent
        from an attachment URL or from the editor's local filesystem.
        """
        self.ensure_one()
        if media_type not in ("image", "video"):
            raise ValidationError(_("Tipo de contenido no válido."))
        attachment = self.env["ir.attachment"].browse(attachment_id).exists()
        if not attachment or not attachment.datas:
            raise ValidationError(_("No se encontró el archivo seleccionado."))
        mimetype = attachment.mimetype or ""
        if media_type == "image" and not mimetype.startswith("image/"):
            raise ValidationError(_("Seleccione una imagen válida."))
        if media_type == "video" and not mimetype.startswith("video/"):
            raise ValidationError(_("Seleccione un archivo de video válido."))
        values = {"media_type": media_type}
        if media_type == "image":
            values["image"] = attachment.datas
        else:
            values.update({
                "video": attachment.datas,
                "video_filename": attachment.name,
                "video_mimetype": mimetype,
            })
        self.write(values)
        return True

    @api.constrains("display_seconds", "date_start", "date_end")
    def _check_campaign_configuration(self):
        for promo in self:
            if promo.display_seconds < 3 or promo.display_seconds > 300:
                raise ValidationError(_("La duración debe estar entre 3 y 300 segundos."))
            if promo.date_start and promo.date_end and promo.date_end < promo.date_start:
                raise ValidationError(_("La fecha final no puede ser anterior a la fecha inicial."))

    @api.model
    def _ddpc_active_for_city(self, company, city_rule=False):
        today = fields.Date.context_today(self)
        domain = [
            ("company_id", "=", company.id), ("active", "=", True),
            "|", ("date_start", "=", False), ("date_start", "<=", today),
            "|", ("date_end", "=", False), ("date_end", ">=", today),
        ]
        if city_rule:
            domain += ["|", ("city_rule_id", "=", False), ("city_rule_id", "=", city_rule.id)]
        else:
            domain.append(("city_rule_id", "=", False))
        return self.search(domain, order="sequence, id")

    def _ddpc_as_payload(self):
        self.ensure_one()
        as_text = lambda value: value.decode() if isinstance(value, bytes) else (value or "")
        return {
            "name": self.name,
            "city": self.city_rule_id.county_name or "Door&Door",
            "media_type": self.media_type,
            "image": as_text(self.image),
            "video": as_text(self.video),
            "video_mimetype": self.video_mimetype or "video/mp4",
            "seconds": self.display_seconds,
            "conditions": self.conditions or "",
        }
