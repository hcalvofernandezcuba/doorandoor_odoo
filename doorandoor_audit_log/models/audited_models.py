from odoo import api, models

from .audit_log import audit_snapshot


def _log_create(env, records, vals_list, tracked_fields):
    fields_to_log = set().union(*(set(vals) for vals in vals_list)) & tracked_fields
    env["doorandoor.audit.log"].log_changes(
        records, "create", tracked_fields=fields_to_log
    )


def _before_write(records, vals, tracked_fields):
    fields_to_log = set(vals) & tracked_fields
    return fields_to_log, audit_snapshot(records, fields_to_log) if fields_to_log else {}


def _log_write(env, records, fields_to_log, before):
    if fields_to_log:
        env["doorandoor.audit.log"].log_changes(
            records, "write", before=before, tracked_fields=fields_to_log
        )


def _before_unlink(records, tracked_fields):
    return records.exists(), audit_snapshot(records, tracked_fields)


def _log_unlink(env, records, before):
    env["doorandoor.audit.log"].log_changes(records, "unlink", before=before)


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _dd_audit_fields = {
        "name", "active", "list_price", "standard_price", "categ_id",
        "attribute_line_ids", "ddsp_is_special", "ddsp_product_kind",
        "ddsp_base_product_tmpl_id", "ddsp_special_changes",
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _log_create(self.env, records, vals_list, self._dd_audit_fields)
        return records

    def write(self, vals):
        fields_to_log, before = _before_write(self, vals, self._dd_audit_fields)
        result = super().write(vals)
        _log_write(self.env, self, fields_to_log, before)
        return result

    def unlink(self):
        records, before = _before_unlink(self, self._dd_audit_fields)
        _log_unlink(self.env, records, before)
        return super().unlink()


class ProductProduct(models.Model):
    _inherit = "product.product"
    _dd_audit_fields = {
        "active", "barcode", "default_code", "standard_price",
        "ddpc_variant_extra_price", "ddpc_is_custom_variant",
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _log_create(self.env, records, vals_list, self._dd_audit_fields)
        return records

    def write(self, vals):
        fields_to_log, before = _before_write(self, vals, self._dd_audit_fields)
        result = super().write(vals)
        _log_write(self.env, self, fields_to_log, before)
        return result

    def unlink(self):
        records, before = _before_unlink(self, self._dd_audit_fields)
        _log_unlink(self.env, records, before)
        return super().unlink()


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"
    _dd_audit_fields = {"price_extra", "product_attribute_value_id", "attribute_line_id"}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _log_create(self.env, records, vals_list, self._dd_audit_fields)
        return records

    def write(self, vals):
        fields_to_log, before = _before_write(self, vals, self._dd_audit_fields)
        result = super().write(vals)
        _log_write(self.env, self, fields_to_log, before)
        return result

    def unlink(self):
        records, before = _before_unlink(self, self._dd_audit_fields)
        _log_unlink(self.env, records, before)
        return super().unlink()


class ResUsers(models.Model):
    _inherit = "res.users"
    _dd_audit_fields = {"name", "login", "active", "groups_id", "ddpc_warehouse_ids"}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _log_create(self.env, records, vals_list, self._dd_audit_fields)
        return records

    def write(self, vals):
        fields_to_log, before = _before_write(self, vals, self._dd_audit_fields)
        result = super().write(vals)
        _log_write(self.env, self, fields_to_log, before)
        return result

    def unlink(self):
        records, before = _before_unlink(self, self._dd_audit_fields)
        _log_unlink(self.env, records, before)
        return super().unlink()


class ResGroups(models.Model):
    _inherit = "res.groups"
    _dd_audit_fields = {"name", "users"}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        _log_create(self.env, records, vals_list, self._dd_audit_fields)
        return records

    def write(self, vals):
        fields_to_log, before = _before_write(self, vals, self._dd_audit_fields)
        result = super().write(vals)
        _log_write(self.env, self, fields_to_log, before)
        return result

    def unlink(self):
        records, before = _before_unlink(self, self._dd_audit_fields)
        _log_unlink(self.env, records, before)
        return super().unlink()
