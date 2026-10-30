# -*- coding: utf-8 -*-
import base64
import io
import re
import subprocess
import tempfile

from PyPDF2 import PdfReader

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _normal(value):
    """Comparison key deliberately tolerant of PDF spacing and case."""
    value = (value or "").upper().strip()
    return re.sub(r"[^A-Z0-9.]", "", value)


class DoorAndDoorInventoryImport(models.Model):
    _name = "ddii.inventory.import"
    _description = "DoorAndDoor Initial Inventory Import"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False)
    source_format = fields.Selection([
        ("tampa_warehouse_pdf", "Tampa Warehouse PDF"),
        ("tampa_store_pdf", "Tampa Store PDF"),
    ], required=True, default="tampa_warehouse_pdf", tracking=True)
    location_id = fields.Many2one(
        "stock.location", required=True, tracking=True,
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [False, company_id])]",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
    )
    inventory_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    source_file = fields.Binary(required=True, attachment=True)
    source_filename = fields.Char()
    state = fields.Selection([
        ("draft", "Draft"), ("analyzed", "Analyzed"), ("review", "Ready for review"),
        ("ready", "Validated"), ("applied", "Applied"), ("cancel", "Cancelled"),
    ], default="draft", required=True, tracking=True)
    line_ids = fields.One2many("ddii.inventory.import.line", "import_id", copy=False)
    parsed_line_count = fields.Integer(compute="_compute_counts")
    matched_line_count = fields.Integer(compute="_compute_counts")
    pending_line_count = fields.Integer(compute="_compute_counts")
    ambiguous_line_count = fields.Integer(compute="_compute_counts")
    review_line_count = fields.Integer(compute="_compute_counts")
    excluded_line_count = fields.Integer(compute="_compute_counts")
    note = fields.Text(readonly=True)

    @api.depends(
        "line_ids.match_state", "line_ids.review_required",
        "line_ids.review_confirmed", "line_ids.excluded",
    )
    def _compute_counts(self):
        for record in self:
            record.parsed_line_count = len(record.line_ids)
            included = record.line_ids.filtered(lambda line: not line.excluded)
            record.matched_line_count = len(included.filtered(lambda l: l.match_state == "matched"))
            record.pending_line_count = len(included.filtered(lambda l: l.match_state == "pending"))
            record.ambiguous_line_count = len(included.filtered(lambda l: l.match_state == "ambiguous"))
            record.review_line_count = len(record.line_ids.filtered(
                lambda line: not line.excluded and line.review_required and not line.review_confirmed
            ))
            record.excluded_line_count = len(record.line_ids.filtered("excluded"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("ddii.inventory.import") or _("New")
        return super().create(vals_list)

    def _pdf_text(self):
        self.ensure_one()
        if not self.source_file:
            raise UserError(_("Attach the PDF inventory file first."))
        pdf_bytes = base64.b64decode(self.source_file)
        # The Tampa sheets were produced by Excel. PyPDF2 obtains their text but
        # loses column spacing, so pdftotext -layout is the primary extractor.
        text = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf:
                temp_pdf.write(pdf_bytes)
                temp_pdf.flush()
                result = subprocess.run(
                    ["pdftotext", "-layout", temp_pdf.name, "-"], check=True,
                    capture_output=True, text=True,
                )
                text = result.stdout or ""
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as exc:
                raise UserError(_("The PDF could not be read.")) from exc
        if not text.strip():
            raise UserError(_("The PDF has no readable text."))
        return text

    @staticmethod
    def _parse_warehouse(text):
        """Parse every physical row from the fixed-column Warehouse PDF.

        The source Excel sheet contains intentionally blank cells.  Its final
        page also contains hardware, frames and trim rather than doors, and
        ``pdftotext -layout`` splits the molding width and quantity over two
        text lines.  Keep incomplete rows for review instead of silently
        dropping them or assuming a zero quantity.
        """
        door_full = re.compile(
            r"^(?P<model>.+?)\s+(?P<width>\d+(?:\.\d+)?)\s+"
            r"(?P<height>\d+(?:\.\d+)?)\s+"
            r"(?P<configuration>SLAB|BIFOLD|RH|LH)"
            r"(?:\s+(?P<qty>\d+))?\s*$",
            re.I,
        )
        door_without_height = re.compile(
            r"^(?P<model>.+?)\s+(?P<width>\d+(?:\.\d+)?)\s+"
            r"(?P<configuration>SLAB|BIFOLD|RH|LH)"
            r"(?:\s+(?P<qty>\d+))?\s*$",
            re.I,
        )
        door_without_configuration = re.compile(
            r"^(?P<model>.+?)\s+(?P<width>\d+(?:\.\d+)?)\s+"
            r"(?P<height>\d+(?:\.\d+)?)\s+(?P<qty>\d+)\s*$",
            re.I,
        )
        frame = re.compile(
            r"^(?P<model>FRAME\s+X\s*\d+)\s+"
            r"(?P<width>\d+\s+\d+/\d+)\s+"
            r"(?P<height>\d+\s+\d+/\d+)\s+"
            r"(?P<configuration>RH|LH)\s*$",
            re.I,
        )
        frame_piano = re.compile(
            r"^(?P<model>FRAME\s+PIANO)\s+"
            r"(?P<configuration>RH\s*/\s*LH|RH|LH)"
            r"(?:\s+(?P<qty>\d+))?\s*$",
            re.I,
        )
        molding_first = re.compile(
            r"^(?P<name>MOLDING)\s+(?P<thickness>\d+/\d+\")\s+X\s+"
            r"(?P<width_whole>\d+)\s+(?P<length>\d+')\s*$",
            re.I,
        )
        molding_continuation = re.compile(
            r"^(?P<width_fraction>\d+/\d+\")\s+(?P<qty>\d+)\s*$",
            re.I,
        )
        baseboard = re.compile(
            r"^(?P<name>BASEBOARD)\s+(?P<thickness>\d+/\d+\")\s+X\s+"
            r"(?P<width_whole>\d+)\s+(?P<length>\d+')\s+"
            r"(?P<width_fraction>\d+/\d+\")\s+(?P<qty>\d+)\s*$",
            re.I,
        )
        hardware_dimensions = re.compile(
            r"^(?P<model>.+?HINGES)\s+(?P<width>\d+(?:\.\d+)?)\s+"
            r"(?P<height>\d+(?:\.\d+)?)\s*$",
            re.I,
        )

        source_lines = list(enumerate(text.splitlines(), 1))
        index = 0
        while index < len(source_lines):
            number, raw = source_lines[index]
            stripped = raw.strip()
            index += 1
            if not stripped:
                continue

            first = molding_first.match(stripped)
            if first and index < len(source_lines):
                next_number, next_raw = source_lines[index]
                continuation = molding_continuation.match(next_raw.strip())
                if continuation:
                    index += 1
                    values = first.groupdict()
                    extra = continuation.groupdict()
                    model = "%s %s X %s %s X %s" % (
                        values["name"], values["thickness"], values["width_whole"],
                        extra["width_fraction"], values["length"],
                    )
                    yield {
                        "model": model,
                        "qty": extra["qty"],
                        "row_type": "trim",
                        "source_line": number,
                        "raw_text": "%s | %s" % (stripped, next_raw.strip()),
                    }
                    continue

            baseboard_match = baseboard.match(stripped)
            if baseboard_match:
                values = baseboard_match.groupdict()
                model = "%s %s X %s %s X %s" % (
                    values["name"], values["thickness"], values["width_whole"],
                    values["width_fraction"], values["length"],
                )
                yield {
                    "model": model,
                    "qty": values["qty"],
                    "row_type": "trim",
                    "source_line": number,
                    "raw_text": stripped,
                }
                continue

            match = (
                door_full.match(stripped)
                or door_without_height.match(stripped)
                or door_without_configuration.match(stripped)
                or frame.match(stripped)
                or frame_piano.match(stripped)
                or hardware_dimensions.match(stripped)
            )
            if match:
                row_type = "door" if match.re in (
                    door_full, door_without_height, door_without_configuration
                ) else "hardware"
                yield {
                    **match.groupdict(),
                    "row_type": row_type,
                    "source_line": number,
                    "raw_text": stripped,
                }
                continue

            # Hardware descriptions with blank measure/quantity cells are real
            # rows too.  Retain the full description for manual or rule-based
            # matching and leave quantity absent so validation blocks applying.
            yield {
                "model": stripped,
                "qty": None,
                "row_type": "hardware",
                "source_line": number,
                "raw_text": stripped,
            }

    @staticmethod
    def _parse_store(text):
        # Store has explicit columns. A missing quantity remains pending; it is never guessed as zero.
        pattern = re.compile(
            r"^(?P<model>[A-Z0-9 -]+?)\s+(?P<width>\d+(?:\.\d+)?)\s+"
            r"(?P<height>\d+(?:\.\d+)?)\s+(?P<configuration>[A-Z/]+)?\s*"
            r"(?P<color>WHITE|BRONZE|BLACK|GOLD|SILVER)?\s*"
            r"(?P<glass>LOWE CLEAR|CWI|GWI|GRAY|CLEAR)?\s*(?P<qty>\d+)?\s*$", re.I)
        for number, raw in enumerate(text.splitlines(), 1):
            match = pattern.match(raw.strip())
            if match:
                values = match.groupdict()
                yield {**values, "source_line": number, "raw_text": raw.strip()}

    def action_analyze(self):
        for record in self:
            if record.state not in ("draft", "analyzed", "review"):
                raise UserError(_("Only a draft or review import can be analyzed again."))
            record.line_ids.unlink()
            parser = record._parse_warehouse if record.source_format == "tampa_warehouse_pdf" else record._parse_store
            commands = []
            for parsed in parser(record._pdf_text()):
                qty = parsed.get("qty")
                review_reasons = []
                source_color = parsed.get("color")
                if (
                    record.source_format == "tampa_warehouse_pdf"
                    and parsed.get("row_type") == "door"
                    and not source_color
                ):
                    source_color = "white"
                    review_reasons.append(_("Color absent in PDF; defaulted to white."))
                if qty in (None, ""):
                    qty = 0.0
                    review_reasons.append(_("Quantity blank in PDF; defaulted to zero."))
                commands.append((0, 0, {
                    "source_line": parsed["source_line"], "raw_text": parsed["raw_text"],
                    "source_model": parsed.get("model"), "source_width": parsed.get("width"),
                    "source_height": parsed.get("height"), "source_configuration": parsed.get("configuration"),
                    "source_color": source_color, "source_glass": parsed.get("glass"),
                    "quantity": float(qty),
                    "quantity_present": True,
                    "review_required": bool(review_reasons),
                    "review_confirmed": False,
                    "review_note": " ".join(review_reasons),
                }))
            record.write({"line_ids": commands, "state": "analyzed", "note": _("Analysis completed. Match variants before applying any inventory adjustment.")})
            record.action_match_variants()
        return True

    def action_match_variants(self):
        for record in self:
            for line in record.line_ids.filtered(lambda candidate: not candidate.excluded):
                line._match_variant()
            record.state = "review"
        return True

    def action_mark_ready(self):
        for record in self:
            included_lines = record.line_ids.filtered(lambda line: not line.excluded)
            invalid = included_lines.filtered(
                lambda line: (
                    line.match_state != "matched"
                    or not line.product_id
                    or not line.quantity_present
                    or (line.review_required and not line.review_confirmed)
                )
            )
            if invalid:
                raise ValidationError(_(
                    "Resolve every pending or ambiguous line and confirm every defaulted value before approving the import."
                ))
            if not included_lines:
                raise ValidationError(_("The import has no prepared lines."))
            duplicates = {}
            for line in included_lines:
                duplicates.setdefault(line.product_id, self.env["ddii.inventory.import.line"])
                duplicates[line.product_id] |= line
            repeated = [product.display_name for product, lines in duplicates.items() if len(lines) > 1]
            if repeated:
                raise ValidationError(_(
                    "The same ITEM appears on more than one line. Consolidate its quantity before validation: %s"
                ) % ", ".join(repeated[:20]))
            record.state = "ready"
        return True

    def action_force_matched_only(self):
        """Exclude untouched unresolved rows while preserving them as evidence."""
        for record in self:
            unresolved = record.line_ids.filtered(
                lambda line: not line.excluded and (
                    line.match_state != "matched" or not line.product_id
                )
            )
            protected = unresolved.filtered(
                lambda line: line.manually_edited or line.manual_match
            )
            if protected:
                raise ValidationError(_(
                    "Some unresolved lines were edited manually and cannot be excluded automatically. Resolve or explicitly exclude them first: source lines %s"
                ) % ", ".join(str(line.source_line) for line in protected[:20]))
            unresolved.write({
                "excluded": True,
                "exclusion_reason": _(
                    "Excluded by Force matched ITEMs: unresolved and never edited manually."
                ),
            })
            record.message_post(body=_(
                "Force matched ITEMs excluded %s untouched pending/ambiguous line(s). No stock was modified."
            ) % len(unresolved))
        return True

    def action_confirm_reviewed_lines(self):
        for record in self:
            lines = record.line_ids.filtered(
                lambda line: (
                    not line.excluded
                    and line.review_required
                    and not line.review_confirmed
                )
            )
            lines.write({"review_confirmed": True})
            record.message_post(body=_(
                "Confirmed review of %s defaulted line(s)."
            ) % len(lines))
        return True

    def action_back_to_review(self):
        self.filtered(lambda record: record.state == "ready").write({"state": "review"})
        return True

    def action_apply_inventory(self):
        """Set the physical on-hand quantity for each prepared ITEM/location."""
        for record in self:
            if record.state != "ready":
                raise UserError(_("Validate the prepared lines before applying inventory."))
            Quant = self.env["stock.quant"]
            included_lines = record.line_ids.filtered(lambda candidate: not candidate.excluded)
            for line in included_lines:
                product = line.product_id
                if not product.is_storable:
                    raise ValidationError(_("%s is not a storable product.") % product.display_name)
                if product.tracking != "none":
                    raise ValidationError(_(
                        "%s requires lot/serial tracking and cannot be loaded as an untracked initial quantity."
                    ) % product.display_name)
                quant = Quant.search([
                    ("product_id", "=", product.id),
                    ("location_id", "=", record.location_id.id),
                    ("lot_id", "=", False),
                    ("package_id", "=", False),
                    ("owner_id", "=", False),
                ], limit=1)
                if not quant:
                    quant = Quant.create({
                        "product_id": product.id,
                        "location_id": record.location_id.id,
                    })
                quant.inventory_quantity = line.quantity
                quant.with_context(inventory_name=record.name).action_apply_inventory()
            record.write({
                "state": "applied",
                "note": _("Initial inventory applied from the reviewed source document."),
            })
            record.message_post(body=_(
                "Initial inventory applied to %s ITEM(s) at %s from import %s."
            ) % (len(included_lines), record.location_id.display_name, record.name))
        return True


class DoorAndDoorInventoryImportLine(models.Model):
    _name = "ddii.inventory.import.line"
    _description = "DoorAndDoor Initial Inventory Import Line"
    _order = "source_line, id"

    import_id = fields.Many2one("ddii.inventory.import", required=True, ondelete="cascade")
    source_line = fields.Integer(readonly=True)
    raw_text = fields.Char(readonly=True)
    source_model = fields.Char(string="Model")
    source_width = fields.Char(string="Width")
    source_height = fields.Char(string="Height")
    source_configuration = fields.Char(string="Configuration")
    source_color = fields.Char(string="Color")
    source_glass = fields.Char(string="Glass")
    quantity = fields.Float(required=True, digits="Product Unit of Measure")
    quantity_present = fields.Boolean(readonly=True)
    product_id = fields.Many2one(
        "product.product", string="Matched item",
        domain="[('is_storable', '=', True), ('company_id', 'in', [False, company_id])]",
    )
    manual_match = fields.Boolean(string="Manual ITEM", readonly=True)
    review_required = fields.Boolean(string="Requires review", readonly=True)
    review_confirmed = fields.Boolean(string="Reviewed")
    review_note = fields.Char(string="Review reason", readonly=True)
    manually_edited = fields.Boolean(string="Edited manually", readonly=True)
    excluded = fields.Boolean(string="Excluded from load")
    exclusion_reason = fields.Char(string="Exclusion reason", readonly=True)
    company_id = fields.Many2one(related="import_id.company_id")
    candidate_count = fields.Integer(readonly=True)
    match_state = fields.Selection([
        ("matched", "Matched"), ("pending", "Pending"), ("ambiguous", "Ambiguous"),
    ], default="pending", readonly=True)
    match_message = fields.Char(readonly=True)

    @api.onchange("quantity")
    def _onchange_quantity(self):
        for line in self:
            line.quantity_present = True

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.manual_match = True
                line.match_state = "matched"
                line.candidate_count = 1
                line.match_message = _("ITEM selected manually and pending batch validation.")
            else:
                line.match_state = "pending"
                line.candidate_count = 0
                line.match_message = _("Select an ITEM or run automatic matching again.")

    @api.onchange(
        "source_model", "source_width", "source_height",
        "source_configuration", "source_color", "source_glass",
    )
    def _onchange_source_values(self):
        for line in self:
            line.product_id = False
            line.manual_match = False
            line.match_state = "pending"
            line.candidate_count = 0
            line.match_message = _("Captured values changed; select an ITEM or run matching again.")

    def write(self, vals):
        if any(line.import_id.state in ("ready", "applied", "cancel") for line in self):
            editable_technical = {"match_state", "candidate_count", "match_message"}
            if set(vals) - editable_technical:
                raise UserError(_("Validated, applied, or cancelled import lines cannot be edited."))
        if "quantity" in vals:
            vals["quantity_present"] = True
        source_fields = {
            "source_model", "source_width", "source_height",
            "source_configuration", "source_color", "source_glass",
        }
        user_edit_fields = source_fields | {"quantity", "product_id"}
        if (
            user_edit_fields.intersection(vals)
            and not self.env.context.get("ddii_auto_match")
            and not self.env.context.get("ddii_system_write")
        ):
            vals["manually_edited"] = True
        if source_fields.intersection(vals) and "product_id" not in vals:
            vals.update({
                "product_id": False,
                "manual_match": False,
                "match_state": "pending",
                "candidate_count": 0,
                "match_message": _("Captured values changed; select an ITEM or run matching again."),
            })
        if vals.get("product_id") and "match_state" not in vals:
            vals.update({
                "manual_match": not self.env.context.get("ddii_auto_match"),
                "match_state": "matched",
                "candidate_count": 1,
                "match_message": _("ITEM selected manually and pending batch validation."),
            })
        elif "product_id" in vals and "match_state" not in vals:
            vals.update({"manual_match": False, "match_state": "pending", "candidate_count": 0})
        return super().write(vals)

    def _source_tokens(self):
        return [_normal(value) for value in (
            self.source_model, self.source_width, self.source_height,
            self.source_configuration, self.source_color, self.source_glass,
        ) if value]

    def _match_variant(self):
        self.ensure_one()
        if self.manual_match and self.product_id:
            self.with_context(ddii_auto_match=True).write({
                "match_state": "matched", "candidate_count": 1,
                "match_message": _("ITEM selected manually."),
            })
            return
        if not self.quantity_present:
            self.with_context(ddii_auto_match=True).write({"match_state": "pending", "product_id": False, "candidate_count": 0,
                        "match_message": _("Quantity is blank in the source file; it was not assumed to be zero.")})
            return
        tokens = self._source_tokens()
        if not tokens:
            self.with_context(ddii_auto_match=True).write({"match_state": "pending", "product_id": False, "candidate_count": 0,
                        "match_message": _("The source line has no usable variant data.")})
            return
        # Candidate set is intentionally conservative: every source token must occur in
        # an existing variant attribute value or its internal reference/display name.
        candidates = self.env["product.product"].search([("active", "=", True)])
        def fits(product):
            values = [_normal(v.name) for v in product.product_template_attribute_value_ids.product_attribute_value_id]
            haystack = values + [_normal(product.default_code), _normal(product.display_name)]
            return all(any(token == value or token in value for value in haystack) for token in tokens)
        candidates = candidates.filtered(fits)
        if len(candidates) == 1:
            self.with_context(ddii_auto_match=True).write({"match_state": "matched", "product_id": candidates.id, "candidate_count": 1,
                        "match_message": _("Exact ITEM match found.")})
        elif len(candidates) > 1:
            self.with_context(ddii_auto_match=True).write({"match_state": "ambiguous", "product_id": False, "candidate_count": len(candidates),
                        "match_message": _("More than one ITEM matches; choose a mapping rule before applying.")})
        else:
            self.with_context(ddii_auto_match=True).write({"match_state": "pending", "product_id": False, "candidate_count": 0,
                        "match_message": _("No existing ITEM matches this source combination.")})
