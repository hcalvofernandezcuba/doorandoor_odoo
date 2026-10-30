from odoo import fields, models


class DoorAndDoorCatalogCategory(models.Model):
    _name = "doorandoor.website.catalog.category"
    _description = "DoorAndDoor Website Catalog Category"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    slug = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    item_ids = fields.One2many("doorandoor.website.catalog.item", "category_id")
    product_tmpl_ids = fields.One2many(
        "product.template", "ddwc_catalog_category_id", string="Productos"
    )

    _sql_constraints = [
        ("slug_unique", "unique(slug)", "La URL de la categoría debe ser única."),
    ]


class DoorAndDoorCatalogItem(models.Model):
    _name = "doorandoor.website.catalog.item"
    _description = "DoorAndDoor Website Catalog Item"
    _inherit = ["mail.thread", "mail.activity.mixin", "website.published.mixin", "website.seo.metadata"]
    _order = "sequence, id desc"

    name = fields.Char(required=True, translate=True, tracking=True)
    subtitle = fields.Char(translate=True)
    category_id = fields.Many2one(
        "doorandoor.website.catalog.category",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    image_1920 = fields.Image(string="Imagen principal", max_width=1920, max_height=1920)
    description = fields.Html(translate=True, sanitize=True)
    specifications = fields.Html(string="Especificaciones", translate=True, sanitize=True)
    featured = fields.Boolean(string="Destacado")
    made_to_order = fields.Boolean(string="Fabricado bajo pedido", default=True)
    lead_time_note = fields.Char(string="Tiempo estimado", translate=True)
    website_url = fields.Char(compute="_compute_website_url")

    def _compute_website_url(self):
        for item in self:
            item.website_url = f"/catalogo/{item.id}"


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ddwc_catalog_visible = fields.Boolean(
        string="Visible en catálogo DoorAndDoor",
        help="Publica este producto base en el catálogo público, sin mostrar precio ni existencia.",
    )
    ddwc_catalog_category_id = fields.Many2one(
        "doorandoor.website.catalog.category",
        string="Categoría del catálogo",
        ondelete="restrict",
    )
    ddwc_catalog_featured = fields.Boolean(string="Destacado en catálogo")

    def ddwc_catalog_url(self):
        self.ensure_one()
        return f"/catalogo/producto/{self.id}"
