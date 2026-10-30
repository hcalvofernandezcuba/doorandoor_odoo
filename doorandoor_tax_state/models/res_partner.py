# -*- coding: utf-8 -*-

import base64
import binascii

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    _DDTS_TAX_EXEMPTION_FIELDS = {
        "ddts_tax_exempt",
        "ddts_tax_exemption_number",
        "ddts_tax_exemption_document",
        "ddts_tax_exemption_document_name",
        "ddts_tax_exemption_uploaded_at",
        "ddts_tax_exemption_uploaded_by",
    }

    ddts_tax_exempt = fields.Boolean(
        string="Exento de impuestos",
        help="Indica que el cliente dispone de una exención fiscal válida.",
    )
    ddts_tax_exemption_number = fields.Char(
        string="Número de registro fiscal de exención",
        copy=False,
        help="Número oficial del certificado o registro que autoriza la exención.",
    )
    ddts_tax_exemption_document = fields.Binary(
        string="Certificado oficial de exención",
        attachment=True,
        copy=False,
        help="Documento PDF oficial que acredita la exención fiscal del cliente.",
    )
    ddts_tax_exemption_document_name = fields.Char(
        string="Nombre del certificado",
        copy=False,
    )
    ddts_tax_exemption_uploaded_at = fields.Datetime(
        string="Fecha de carga",
        readonly=True,
        copy=False,
    )
    ddts_tax_exemption_uploaded_by = fields.Many2one(
        "res.users",
        string="Cargado por",
        readonly=True,
        copy=False,
    )

    def _ddts_check_tax_exemption_edit_access(self, vals):
        protected_fields = self._DDTS_TAX_EXEMPTION_FIELDS.intersection(vals)
        if not protected_fields:
            return
        if self.env.is_superuser() or self.env.user.has_group(
            "account.group_account_user"
        ):
            return

        # The contact form sends invisible exemption fields with False when a
        # salesperson creates a regular customer. Their mere presence is not
        # an exemption change and must not block customer creation.
        if not self:
            if not any(vals.get(field_name) for field_name in protected_fields):
                return
        else:
            has_real_change = False
            for partner in self:
                for field_name in protected_fields:
                    current_value = partner[field_name]
                    if hasattr(current_value, "id"):
                        current_value = current_value.id or False
                    incoming_value = vals.get(field_name)
                    if (current_value or False) != (incoming_value or False):
                        has_real_change = True
                        break
                if has_real_change:
                    break
            if not has_real_change:
                return
        raise ValidationError(
            _(
                "Solo los usuarios de Contabilidad pueden modificar la "
                "condición de exención fiscal y su documento acreditativo."
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._ddts_check_tax_exemption_edit_access(vals)
            if vals.get("ddts_tax_exemption_document"):
                vals.update(
                    {
                        "ddts_tax_exemption_uploaded_at": fields.Datetime.now(),
                        "ddts_tax_exemption_uploaded_by": self.env.user.id,
                    }
                )
        return super().create(vals_list)

    def write(self, vals):
        self._ddts_check_tax_exemption_edit_access(vals)
        if vals.get("ddts_tax_exemption_document"):
            vals = dict(vals)
            vals.update(
                {
                    "ddts_tax_exemption_uploaded_at": fields.Datetime.now(),
                    "ddts_tax_exemption_uploaded_by": self.env.user.id,
                }
            )
        return super().write(vals)

    @api.constrains(
        "ddts_tax_exempt",
        "ddts_tax_exemption_number",
        "ddts_tax_exemption_document",
        "ddts_tax_exemption_document_name",
    )
    def _check_ddts_tax_exemption_number(self):
        for partner in self:
            if partner.ddts_tax_exempt and not (
                partner.ddts_tax_exemption_number or ""
            ).strip():
                raise ValidationError(
                    _(
                        "Debe indicar el número de registro fiscal que autoriza "
                        "la exención de impuestos."
                    )
                )
            if partner.ddts_tax_exempt and not partner.ddts_tax_exemption_document:
                raise ValidationError(
                    _(
                        "Debe adjuntar el documento PDF oficial que acredita "
                        "la exención de impuestos."
                    )
                )
            if partner.ddts_tax_exemption_document:
                try:
                    content = base64.b64decode(
                        partner.ddts_tax_exemption_document, validate=False
                    )
                except (binascii.Error, ValueError, TypeError):
                    content = b""
                if not content.startswith(b"%PDF-"):
                    raise ValidationError(
                        _("El certificado de exención debe ser un archivo PDF válido.")
                    )
                filename = partner.ddts_tax_exemption_document_name or ""
                if filename and not filename.lower().endswith(".pdf"):
                    raise ValidationError(
                        _("El nombre del certificado debe tener extensión .pdf.")
                    )
