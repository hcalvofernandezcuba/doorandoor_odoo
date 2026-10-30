import re

from odoo import api, fields, models


class DoorAndDoorWebsiteShowroom(models.Model):
    _name = "doorandoor.website.showroom"
    _description = "DoorAndDoor Website Showroom"
    _inherit = ["mail.thread", "mail.activity.mixin", "website.published.mixin", "website.seo.metadata"]
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    image_1920 = fields.Image(string="Imagen de portada", max_width=1920, max_height=1920)
    description = fields.Html(string="Descripción", translate=True, sanitize=True)
    street = fields.Char(string="Dirección")
    city = fields.Char()
    state_name = fields.Char(string="Estado")
    zip = fields.Char(string="Código postal")
    phone = fields.Char(string="Teléfono")
    email = fields.Char()
    map_url = fields.Char(string="Enlace de mapa")
    video_source = fields.Selection(
        [("external", "YouTube o Vimeo"), ("upload", "Archivo MP4")],
        string="Origen del video",
        default="external",
        required=True,
        tracking=True,
    )
    video_url = fields.Char(string="Enlace de video")
    video_embed_url = fields.Char(compute="_compute_video_embed_url")
    video_file = fields.Binary(string="Video MP4", attachment=True)
    video_filename = fields.Char(string="Nombre del archivo")
    has_video = fields.Boolean(compute="_compute_has_video")

    @api.depends("video_source", "video_url", "video_file")
    def _compute_has_video(self):
        for showroom in self:
            showroom.has_video = bool(
                showroom.video_url if showroom.video_source == "external" else showroom.video_file
            )

    @api.depends("video_url")
    def _compute_video_embed_url(self):
        for showroom in self:
            url = (showroom.video_url or "").strip()
            youtube = re.search(r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})", url)
            vimeo = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
            if youtube:
                showroom.video_embed_url = "https://www.youtube-nocookie.com/embed/%s" % youtube.group(1)
            elif vimeo:
                showroom.video_embed_url = "https://player.vimeo.com/video/%s" % vimeo.group(1)
            else:
                showroom.video_embed_url = False

    def _publish_video_attachment(self):
        attachments = self.env["ir.attachment"].sudo().search([
            ("res_model", "=", self._name),
            ("res_id", "in", self.ids),
            ("res_field", "=", "video_file"),
        ])
        attachments.write({"public": True})

    @api.model_create_multi
    def create(self, vals_list):
        showrooms = super().create(vals_list)
        showrooms._publish_video_attachment()
        return showrooms

    def write(self, vals):
        result = super().write(vals)
        if "video_file" in vals:
            self._publish_video_attachment()
        return result
