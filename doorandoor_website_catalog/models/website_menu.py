from lxml import etree

from odoo import api, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    @api.model
    def _ddwc_apply_catalog_navigation(self):
        event_menus = self.search([("url", "in", ["/event", "/events"])])
        if event_menus:
            event_menus.unlink()

        # El catálogo editorial, la tienda nativa y la galería son accesos
        # independientes. Recupera la página histórica de Galería, cuya URL
        # quedó corrompida al convertir un enlace absoluto en una ruta local.
        gallery_view = self.env.ref("website.services", raise_if_not_found=False)
        if not gallery_view:
            gallery_view = self.env["ir.ui.view"].search(
                [("key", "=", "website.services"), ("website_id", "!=", False)],
                limit=1,
            )
        gallery_page = self.env["website.page"].search(
            [("view_id", "=", gallery_view.id)], limit=1
        ) if gallery_view else self.env["website.page"]
        if gallery_page:
            gallery_page.write({
                "name": "Galería",
                "url": "/galeria",
                "is_published": True,
            })

        for menu in self.search([]):
            translated_names = {
                menu.with_context(lang=lang).name
                for lang in ("es_ES", "es_419", "en_US")
            }
            if translated_names.intersection({"Galería", "Gallery", "Services"}):
                values = {"name": "Galería", "url": "/galeria"}
                if gallery_page:
                    values["page_id"] = gallery_page.id
                menu.write(values)

        # Convierte el bloque "Galería de Proyectos" de Inicio en una entrada
        # funcional: sus imágenes abren la galería y se agrega una llamada a
        # la acción clara. La transformación es idempotente y conserva las
        # imágenes y el diseño editados desde Website.
        homepage = self.env["website.page"].search(
            [("url", "=", "/"), ("website_id", "!=", False)], limit=1
        )
        if homepage and homepage.view_id.arch_db:
            root = etree.fromstring(homepage.view_id.arch_db.encode("utf-8"))
            sections = root.xpath(
                "//section[.//*[contains(normalize-space(string(.)), "
                "'Galería de Proyectos')]]"
            )
            if sections:
                section = sections[0]
                section.set("id", "dd-project-gallery")
                for anchor in section.xpath(".//a[@href='#']"):
                    anchor.set("href", "/galeria")
                if not section.xpath(".//a[contains(@class, 'dd-gallery-cta')]"):
                    container = section.xpath("./div[contains(@class, 'container') or contains(@class, 'container-fluid')]")
                    target = container[0] if container else section
                    cta = etree.Element("div", {
                        "class": "text-center pt24 pb32 dd-gallery-link",
                    })
                    link = etree.SubElement(cta, "a", {
                        "href": "/galeria",
                        "class": "btn btn-primary btn-lg dd-gallery-cta",
                    })
                    link.text = "Ver galería completa"
                    target.append(cta)
                homepage.view_id.arch_db = etree.tostring(
                    root, encoding="unicode"
                )

        roots = self.env["website.menu"]
        default_root = self.env.ref("website.main_menu", raise_if_not_found=False)
        if default_root:
            roots |= default_root
        roots |= self.env["website"].search([]).mapped("menu_id")

        for root in roots:
            children = root.child_id.sorted(lambda menu: (menu.sequence, menu.id))
            catalog_menu = children.filtered(lambda menu: menu.url == "/catalogo")[:1]
            if not catalog_menu:
                continue
            ordered = children - catalog_menu
            ordered = ordered[:1] + catalog_menu + ordered[1:]
            for index, menu in enumerate(ordered, start=1):
                menu.sequence = index * 10
        return True
