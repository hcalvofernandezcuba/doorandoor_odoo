import logging

from odoo import _
from odoo.addons.sale.controllers.product_configurator import (
    SaleProductConfiguratorController,
)
from odoo.exceptions import AccessError, UserError
from odoo.http import request, route


_logger = logging.getLogger(__name__)


class DoorAndDoorSaleProductConfiguratorController(
    SaleProductConfiguratorController
):
    """Keep product administration out of the salesperson's access groups."""

    def _ddpc_get_sales_template(self, product_template_id):
        """Return a narrowly elevated template for the sales configurator.

        The standard configurator may materialize a dynamic variant while it
        resolves or confirms a combination.  That internal operation writes
        technical variant metadata on ``product.template``.  Salespeople must
        not receive generic product write access, so elevate only the template
        already selected in this configurator after validating read access and
        the user's commercial role.
        """
        user = request.env.user
        template = request.env["product.template"].browse(
            product_template_id
        ).exists()
        template.check_access("read")
        if not template or not template.sale_ok:
            raise UserError(_("Seleccione un producto vendible valido."))
        if not (
            user.has_group("base.group_user")
            and (
                user.has_group("sales_team.group_sale_salesman")
                or user.has_group("account.group_account_invoice")
            )
        ):
            raise AccessError(_("No tiene permiso para configurar productos de venta."))
        return template.sudo()

    def _get_product_template(self, product_template_id):
        """Protect every standard configurator route, not only confirmation."""
        return self._ddpc_get_sales_template(product_template_id)

    @route()
    def sale_product_configurator_create_product(
        self, product_template_id, ptav_ids
    ):
        user = request.env.user
        template = self._ddpc_get_sales_template(product_template_id)

        combination = request.env["product.template.attribute.value"].browse(
            ptav_ids
        )
        if combination.filtered(
            lambda value: value.product_tmpl_id != template
        ):
            raise UserError(_("La combinacion no pertenece al producto seleccionado."))

        product = template.sudo()._create_product_variant(combination.sudo())
        if not product:
            raise UserError(_("La combinacion seleccionada no es valida."))
        _logger.info(
            "DDPC configurator resolved product=%s template=%s requested_by=%s",
            product.id,
            template.id,
            user.id,
        )
        template.sudo().message_post(
            body=_(
                "Variante %(variant)s resuelta desde el configurador de ventas por %(user)s."
            )
            % {"variant": product.display_name, "user": user.display_name}
        )
        return product.id
