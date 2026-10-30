import base64
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class LegacyDeliveryImportBatch(models.Model):
    _name = "doorandoor.legacy.delivery.import.batch"
    _description = "Lote de PDF de ventas históricas"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False)
    warehouse_id = fields.Many2one("stock.warehouse", required=True, tracking=True)
    supply_warehouse_id = fields.Many2one("stock.warehouse", required=True, tracking=True)
    inventory_treatment = fields.Selection(
        [
            ("existing_stock", "Consumir stock existente de Odoo"),
            ("excluded_legacy", "Excluir: inventario controlado en sistema anterior"),
            ("exceptional_regularization", "Regularización excepcional"),
        ],
        string="Tratamiento de inventario",
        default="existing_stock",
        required=True,
        tracking=True,
    )
    inventory_treatment_reason = fields.Text(
        string="Motivo / evidencia del tratamiento", tracking=True,
    )
    payment_note = fields.Char(
        required=True,
        default="Pago verificado en el sistema anterior",
        help="Constancia general aplicada a los documentos de este lote.",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", "ddlo_batch_attachment_rel", "batch_id", "attachment_id",
        string="Facturas PDF",
    )
    document_ids = fields.One2many(
        "doorandoor.legacy.delivery.ocr", "batch_id", string="Documentos creados",
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("queued", "En cola"), ("done", "Procesado")],
        default="draft", required=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "doorandoor.legacy.delivery.import.batch"
                ) or _("Nuevo")
        return super().create(vals_list)

    def action_enqueue(self):
        Document = self.env["doorandoor.legacy.delivery.ocr"]
        for batch in self:
            if batch.state != "draft":
                continue
            if not batch.attachment_ids:
                raise UserError(_("Adjunte al menos un PDF."))
            invalid = batch.attachment_ids.filtered(
                lambda a: a.mimetype != "application/pdf"
                and not (a.name or "").lower().endswith(".pdf")
            )
            if invalid:
                raise ValidationError(_("Solo se admiten archivos PDF: %s") % ", ".join(invalid.mapped("name")))
            for attachment in batch.attachment_ids:
                Document.create({
                    "batch_id": batch.id,
                    "file_name": attachment.name,
                    "file_data": attachment.datas,
                    "warehouse_id": batch.warehouse_id.id,
                    "supply_warehouse_id": batch.supply_warehouse_id.id,
                    "inventory_treatment": batch.inventory_treatment,
                    "inventory_treatment_reason": batch.inventory_treatment_reason,
                    "payment_note": batch.payment_note,
                    "company_id": batch.company_id.id,
                    "state": "queued",
                })
            batch.state = "queued"
        return True


class LegacyDeliveryOCR(models.Model):
    _name = "doorandoor.legacy.delivery.ocr"
    _description = "Importación OCR de venta histórica"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: _("Nuevo"), readonly=True, copy=False, tracking=True)
    batch_id = fields.Many2one(
        "doorandoor.legacy.delivery.import.batch", ondelete="set null", index=True,
    )
    file_name = fields.Char(required=True)
    file_data = fields.Binary(required=True, attachment=True)
    file_sha256 = fields.Char(readonly=True, copy=False, index=True)
    extraction_method = fields.Selection(
        [("pdf_text", "Texto PDF"), ("ocr", "OCR"), ("manual", "Revisión manual")],
        readonly=True, copy=False,
    )
    source_system = fields.Selection(
        [("zoho", "Zoho"), ("quickbooks", "QuickBooks"), ("unknown", "No identificado")],
        string="Sistema de origen", readonly=True, copy=False, tracking=True,
    )
    raw_text = fields.Text(readonly=True, copy=False)
    external_reference = fields.Char(string="Factura anterior", tracking=True)
    sale_date = fields.Date(tracking=True)
    customer_text = fields.Char(string="Cliente detectado", readonly=True)
    salesperson_text = fields.Char(string="Vendedor anterior", readonly=True)
    payment_method_text = fields.Char(string="Método de pago detectado", readonly=True)
    legacy_status = fields.Char(string="Estado anterior", readonly=True)
    amount_total = fields.Monetary(string="Total anterior", readonly=True)
    amount_paid = fields.Monetary(string="Pagado anteriormente", readonly=True)
    amount_due = fields.Monetary(string="Saldo anterior", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True,
    )
    partner_id = fields.Many2one("res.partner", string="Cliente", tracking=True)
    warehouse_id = fields.Many2one("stock.warehouse", required=True, tracking=True)
    supply_warehouse_id = fields.Many2one("stock.warehouse", required=True, tracking=True)
    inventory_treatment = fields.Selection(
        [
            ("existing_stock", "Consumir stock existente de Odoo"),
            ("excluded_legacy", "Excluir: inventario controlado en sistema anterior"),
            ("exceptional_regularization", "Regularización excepcional"),
        ],
        string="Tratamiento de inventario",
        default="existing_stock",
        required=True,
        tracking=True,
    )
    inventory_treatment_reason = fields.Text(
        string="Motivo / evidencia del tratamiento", tracking=True,
    )
    payment_note = fields.Char(required=True, tracking=True)
    line_ids = fields.One2many(
        "doorandoor.legacy.delivery.ocr.line", "document_id", string="Productos detectados",
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("queued", "En cola"), ("processing", "Procesando"),
         ("review", "Revisión requerida"), ("ready", "Lista para aprobar"),
         ("approved", "Entrega creada"), ("error", "Error"), ("cancel", "Anulada")],
        default="draft", required=True, copy=False, tracking=True,
    )
    error_message = fields.Text(readonly=True, copy=False)
    reviewed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    reviewed_at = fields.Datetime(readonly=True, copy=False)
    approved_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    approved_at = fields.Datetime(readonly=True, copy=False)
    historical_delivery_id = fields.Many2one(
        "doorandoor.historical.delivery", readonly=True, copy=False,
    )
    picking_id = fields.Many2one(
        "stock.picking", related="historical_delivery_id.picking_id", readonly=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
    )
    needs_review = fields.Boolean(compute="_compute_needs_review")

    _sql_constraints = [
        ("file_sha256_company_unique", "unique(file_sha256, company_id)",
         "Este PDF ya fue importado en la compañía."),
    ]

    @api.depends(
        "partner_id", "external_reference", "sale_date",
        "line_ids.match_state", "line_ids.mapping_confirmed",
    )
    def _compute_needs_review(self):
        for record in self:
            record.needs_review = bool(
                not record.partner_id or not record.external_reference or not record.sale_date
                or not record.line_ids.filtered(lambda l: l.quantity > 0)
                or record.line_ids.filtered(
                    lambda l: l.quantity > 0 and (
                        l.match_state != "matched"
                        or (l.mapping_proposed and not l.mapping_confirmed)
                    )
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            data = base64.b64decode(vals.get("file_data") or b"")
            if data and not data.startswith(b"%PDF"):
                raise ValidationError(_("El archivo %s no es un PDF válido.") % vals.get("file_name", ""))
            vals["file_sha256"] = hashlib.sha256(data).hexdigest() if data else False
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "doorandoor.legacy.delivery.ocr"
                ) or _("Nuevo")
        return super().create(vals_list)

    def action_queue(self):
        self.filtered(lambda r: r.state in ("draft", "error")).write({
            "state": "queued", "error_message": False,
        })
        return True

    @api.model
    def _cron_process_queue(self, limit=5):
        documents = self.search([("state", "=", "queued")], limit=limit, order="id")
        for document in documents:
            try:
                document._process_document()
                self.env.cr.commit()
            except Exception as error:  # keep the remaining batch moving
                self.env.cr.rollback()
                failed = self.browse(document.id).exists()
                failed.write({"state": "error", "error_message": str(error)})
                self.env.cr.commit()
        batches = documents.mapped("batch_id")
        for batch in batches:
            if batch.document_ids and not batch.document_ids.filtered(lambda d: d.state in ("queued", "processing")):
                batch.state = "done"

    def action_extract_now(self):
        for document in self:
            document._process_document()
        return True

    def _process_document(self):
        self.ensure_one()
        self.write({"state": "processing", "error_message": False})
        pdf_data = base64.b64decode(self.file_data or b"")
        text, method = self._extract_pdf_text(pdf_data)
        source_system = self._detect_source_system(text)
        values = self._parse_header(text, source_system=source_system)
        self.line_ids.unlink()
        lines = self._parse_product_lines(text, source_system=source_system)
        values.update({
            "raw_text": text,
            "extraction_method": method,
            "source_system": source_system,
            "state": "review",
            "line_ids": [(0, 0, line) for line in lines],
        })
        self.write(values)
        self.message_post(body=_(
            "PDF procesado mediante %(method)s. Se detectaron %(lines)s líneas; "
            "revise toda coincidencia antes de aprobar."
        ) % {"method": method, "lines": len(lines)})

    def _extract_pdf_text(self, pdf_data):
        with tempfile.TemporaryDirectory(prefix="ddlo_") as temp_dir:
            pdf_path = os.path.join(temp_dir, "source.pdf")
            txt_path = os.path.join(temp_dir, "source.txt")
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(pdf_data)
            subprocess.run(
                ["pdftotext", "-layout", pdf_path, txt_path],
                check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            text = ""
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8", errors="replace") as text_file:
                    text = text_file.read()
            if len(re.sub(r"\s+", "", text)) >= 80:
                return text, "pdf_text"
            if not shutil.which("tesseract"):
                raise UserError(_(
                    "El PDF parece escaneado y el motor OCR Tesseract no está instalado."
                ))
            image_root = os.path.join(temp_dir, "page")
            subprocess.run(
                ["pdftoppm", "-jpeg", "-r", "200", pdf_path, image_root],
                check=True, timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            pages = []
            for image_name in sorted(name for name in os.listdir(temp_dir) if name.startswith("page-") and name.endswith(".jpg")):
                result = subprocess.run(
                    ["tesseract", os.path.join(temp_dir, image_name), "stdout", "-l", "eng+spa"],
                    check=True, timeout=180, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                pages.append(result.stdout.decode("utf-8", errors="replace"))
            return "\n\f\n".join(pages), "ocr"

    @api.model
    def _ddhi_parse_money(self, value):
        return float((value or "0").replace("$", "").replace(",", "").strip() or 0.0)

    @api.model
    def _detect_source_system(self, text):
        if re.search(r"(?i)QuickBooks|Business at a glance|Receive\s*payment", text):
            return "quickbooks"
        if re.search(r"(?i)Zoho|Payment\s+Made|Sales\s+person\s*:", text):
            return "zoho"
        # The clean QuickBooks print view does not print the QuickBooks brand.
        if re.search(r"(?im)^\s*Invoice\s+no\.\s*:\s*INV-", text) and re.search(
            r"(?i)\bPayment\s+Method\s+1\s*:", text
        ):
            return "quickbooks"
        return "unknown"

    def _parse_header(self, text, source_system=None):
        source_system = source_system or self._detect_source_system(text)
        if source_system == "quickbooks":
            return self._parse_quickbooks_header(text)
        return self._parse_zoho_header(text)

    def _parse_zoho_header(self, text):
        values = {}
        reference = re.search(
            r"(?im)^\s*#?\s*(INV[-/][A-Z0-9./_-]+)\s*$",
            text,
        )
        if reference:
            values["external_reference"] = reference.group(1).strip().upper()
        date_match = re.search(
            r"(?im)^\s*(?:invoice\s+date|date|fecha)\s*:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
        )
        if date_match:
            for date_format in ("%d %b %Y", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%y"):
                try:
                    from datetime import datetime
                    values["sale_date"] = datetime.strptime(date_match.group(1), date_format).date()
                    break
                except ValueError:
                    continue
        customer = re.search(r"(?im)^\s*Bill\s+To\s*\n\s*([^\n]{3,100}?)(?:\s{4,}.*)?$", text)
        if customer:
            customer_text = customer.group(1).strip()
            values["customer_text"] = customer_text
            partner = self.env["res.partner"].search([("name", "=ilike", customer_text)], limit=1)
            if not partner:
                partner = self.env["res.partner"].search([("name", "ilike", customer_text)], limit=1)
            if partner:
                values["partner_id"] = partner.id
        mappings = {
            "salesperson_text": r"(?im)^\s*Sales\s+person\s*:\s*(.+?)\s*$",
            "payment_method_text": r"(?im)^\s*Payment\s+Method\s*:\s*(.+?)\s*$",
            "legacy_status": r"(?im)^.*Invoice\s+Status\s*:\s*(.+?)\s*$",
        }
        for field_name, pattern in mappings.items():
            match = re.search(pattern, text)
            if match:
                values[field_name] = match.group(1).strip()
        total_matches = re.findall(r"(?im)^\s*Total\s+\$?([\d,]+\.\d{2})\s*$", text)
        paid = re.search(r"(?im)^\s*Payment\s+Made\s+\(?-?\)?\s*\$?([\d,]+\.\d{2})\s*$", text)
        due_matches = re.findall(r"(?im)^\s*Balance\s+Due\s+\$?([\d,]+\.\d{2})\s*$", text)
        if total_matches:
            values["amount_total"] = self._ddhi_parse_money(total_matches[-1])
        if paid:
            values["amount_paid"] = self._ddhi_parse_money(paid.group(1))
        if due_matches:
            values["amount_due"] = self._ddhi_parse_money(due_matches[-1])
        return values

    def _parse_quickbooks_header(self, text):
        values = {}
        reference = re.search(r"(?im)Invoice\s+no\.\s*:\s*(INV[-/][A-Z0-9./_-]+)", text)
        if not reference:
            reference = re.search(r"(?im)^\s*Invoice\s+(INV[-/][A-Z0-9./_-]+)\s*$", text)
        if reference:
            values["external_reference"] = reference.group(1).strip().upper()

        date_match = re.search(
            r"(?im)Invoice\s+date\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text
        )
        if date_match:
            from datetime import datetime
            for date_format in ("%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"):
                try:
                    values["sale_date"] = datetime.strptime(date_match.group(1), date_format).date()
                    break
                except ValueError:
                    continue

        customer = re.search(r"(?im)^.*Bill\s+to\s*$\n\s*([^\n]{3,160})$", text)
        if customer:
            customer_text = re.split(r"\s{4,}", customer.group(1).strip(), maxsplit=1)[0].strip()
            values["customer_text"] = customer_text
            partner = self.env["res.partner"].search([("name", "=ilike", customer_text)], limit=1)
            if not partner:
                partner = self.env["res.partner"].search([("name", "ilike", customer_text)], limit=1)
            if partner:
                values["partner_id"] = partner.id

        mappings = {
            "salesperson_text": r"(?im)Sales\s+Rep\s*:\s*([^\n]+)",
            "payment_method_text": r"(?im)Payment(?:\s+\w+){0,2}\s+Method\s+1\s*:\s*([^\n]+)",
            "legacy_status": r"(?im)Invoice\s+Status\s*:\s*([^\n]+)",
        }
        for field_name, pattern in mappings.items():
            match = re.search(pattern, text)
            if match:
                values[field_name] = re.split(r"\s{3,}", match.group(1).strip(), maxsplit=1)[0].strip()

        money_patterns = {
            "amount_total": r"(?im)^.*\bTotal\s+\$?([\d,]+\.\d{2})\s*$",
            "amount_paid": r"(?im)^.*\bPayment\s+-?\$?([\d,]+\.\d{2})\s*$",
            "amount_due": r"(?im)^.*\bBalance\s+due\s+\$?([\d,]+\.\d{2})\s*$",
        }
        for field_name, pattern in money_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                values[field_name] = self._ddhi_parse_money(matches[-1])
        return values

    def _parse_product_lines(self, text, source_system=None):
        source_system = source_system or self._detect_source_system(text)
        if source_system == "quickbooks":
            return self._parse_quickbooks_product_lines(text)
        return self._parse_zoho_product_lines(text)

    def _parse_zoho_product_lines(self, text):
        start_pattern = re.compile(
            r"(?m)^\s*(\d+)\s{3,}(.+?)\s{2,}(\d+\.\d{2})\s+([\d,]+\.\d{2}|0\.00)\s+.*$"
        )
        matches = list(start_pattern.finditer(text))
        lines = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.start():end]
            if re.search(r"(?i)Delivery\s+Sevices|Delivery\s+Services", match.group(2)):
                continue
            billed = float(match.group(3))
            description = " ".join(match.group(2).split()).strip(" /")
            size = re.search(r"(?im)^\s*SIZE\s*:\s*([^\n]+)", block)
            swing = re.search(r"(?im)^\s*SWING\s*:\s*([^\s]+)", block)
            color = re.search(r"(?im)^\s*COLOR\s*:\s*([^\s]+)", block)
            glass = re.search(r"(?im)^\s*GLASS\s*:\s*([^\s]+)", block)
            logistics = []
            for note in re.findall(r"(?im)^\s*((?:\d+[- ]*)?(?:recibido|entregado|pendiente)[^\n]*)", block):
                logistics.append(" ".join(note.split()))
            notes = " | ".join(logistics)
            delivered_match = re.search(r"(?i)entregado\s+(\d+(?:\.\d+)?)", notes)
            delivered = min(float(delivered_match.group(1)), billed) if delivered_match else 0.0
            if not delivered_match and re.search(r"(?i)entregado", notes):
                delivered = billed
            pending = max(billed - delivered, 0.0)
            size_text = size.group(1).strip() if size else ""
            # Zoho aligns the unit (for example ``pcs``) on the same visual
            # row as SIZE. It is not part of either dimension.
            size_text = re.sub(r"\s+(?:pcs|units?|unidades?)\s*$", "", size_text, flags=re.I)
            attributes = {
                "size": size_text,
                "swing": swing.group(1).strip() if swing else "",
                "color": color.group(1).strip() if color else "",
                "glass": glass.group(1).strip() if glass else "",
            }
            product, confidence, state = self._match_product(
                description, attributes, source_system="zoho"
            )
            lines.append({
                "source_text": " ".join(block.split()),
                "description": description,
                "billed_quantity": billed,
                "delivered_quantity": delivered,
                "quantity": pending,
                "logistic_notes": notes,
                "legacy_size": attributes["size"],
                "legacy_swing": attributes["swing"],
                "legacy_color": attributes["color"],
                "legacy_glass": attributes["glass"],
                "product_id": product.id if product else False,
                "confidence": confidence,
                "match_state": state,
                "mapping_proposed": bool(product and confidence == 60.0),
            })
        return lines

    def _parse_quickbooks_product_lines(self, text):
        starts = list(re.finditer(r"(?m)^\s*(\d+)\.\s+([^\n]+)$", text))
        lines = []
        for index, start in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            block = text[start.start():end]
            first_row = start.group(2).strip()
            if re.match(r"(?i)Late\s+fee\b", first_row):
                continue

            # The description is the text before the first dimension. The rest
            # of the block may contain unrelated QuickBooks dashboard columns.
            size = re.search(r"\b(\d+(?:\.\d+)?\s*[Xx]\s*\d+(?:\.\d+)?)\b", block)
            if not size:
                continue
            size_in_row = re.search(re.escape(size.group(1)), first_row, flags=re.I)
            description = first_row[:size_in_row.start()].strip() if size_in_row else ""
            if not description:
                description = re.split(r"\s{2,}", first_row, maxsplit=1)[0].strip()

            # Prefer a row carrying qty + rate + amount. It can occur after the
            # product header when QuickBooks inserts dashboard text in between.
            price_row = re.search(
                r"(?m)(?:^|\s)(\d+(?:\.\d+)?)\s+\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$",
                block,
            )
            if price_row:
                billed = float(price_row.group(1))
            else:
                # Some clean QuickBooks print views intentionally omit rates
                # and amounts but still print an explicit Qty column. Accept
                # that quantity only when it follows the dimension on the
                # numbered product row; never infer it from the row number.
                quantity_tail = first_row[size_in_row.end():] if size_in_row else ""
                quantity_match = re.search(
                    r"\s+(\d+(?:\.\d+)?)\s*$", quantity_tail
                )
                if not quantity_match:
                    continue
                billed = float(quantity_match.group(1))

            tokens = re.findall(
                r"(?i)\b(LH|RH|BLANCO|BLANCA|WHITE|BRONCE|GREY|GRAY|CLEAR|CWI|GWI|XX|AG[- ]?\d+)\b",
                block,
            )
            token_upper = [token.strip().upper() for token in tokens]
            swing = next((token for token in token_upper if token in ("LH", "RH")), "")
            color = next((token for token in token_upper if token in ("BLANCO", "BLANCA", "WHITE", "BRONCE")), "")
            glass = next((token for token in token_upper if token in ("GREY", "GRAY", "CLEAR", "CWI", "GWI")), "")
            model = next((token for token in token_upper if token == "XX" or token.startswith("AG")), "")
            attributes = {
                "size": re.sub(r"\s+", "", size.group(1)),
                "swing": swing,
                "color": color,
                "glass": glass,
                "model": model,
            }
            product, confidence, state = self._match_product(
                description, attributes, source_system="quickbooks"
            )
            lines.append({
                "source_text": " ".join(block.split()),
                "description": description,
                "billed_quantity": billed,
                "delivered_quantity": 0.0,
                "quantity": billed,
                "logistic_notes": " | ".join(filter(None, [attributes["size"], swing, color, glass, model])),
                "legacy_size": attributes["size"],
                "legacy_swing": swing,
                "legacy_color": color,
                "legacy_glass": glass,
                "legacy_model": model,
                "product_id": product.id if product else False,
                "confidence": confidence,
                "match_state": state,
                "mapping_proposed": bool(product and confidence == 60.0),
            })
        return lines

    @api.model
    def _ddhi_decimal_dimension(self, value):
        value = (value or "").strip()
        match = re.match(r"^(\d+)(?:\s+(\d+)\s*/\s*(\d+))?$", value)
        if not match:
            return value
        result = float(match.group(1))
        if match.group(2):
            result += float(match.group(2)) / float(match.group(3))
        nominal_to_catalog = {62.0: 62.75, 37.5: 38.125, 25.0: 25.75}
        result = nominal_to_catalog.get(result, result)
        return ("%.3f" % result).rstrip("0").rstrip(".")

    @api.model
    def _ddhi_normalize_mapping_value(self, value):
        return re.sub(r"\s+", " ", (value or "").strip()).upper()

    def _match_product(self, description, attributes=None, source_system="unknown"):
        Product = self.env["product.product"]
        attributes = attributes or {}
        normalized = description.strip()
        mapping = self.env["doorandoor.legacy.product.mapping"].search([
            ("company_id", "=", self.env.company.id),
            ("source_system", "=", source_system),
            ("legacy_name", "=", self._ddhi_normalize_mapping_value(description)),
            ("legacy_size", "=", self._ddhi_normalize_mapping_value(attributes.get("size"))),
            ("legacy_swing", "=", self._ddhi_normalize_mapping_value(attributes.get("swing"))),
            ("legacy_color", "=", self._ddhi_normalize_mapping_value(attributes.get("color"))),
            ("legacy_glass", "=", self._ddhi_normalize_mapping_value(attributes.get("glass"))),
            ("legacy_model", "=", self._ddhi_normalize_mapping_value(attributes.get("model"))),
            ("active", "=", True),
        ], limit=1)
        if mapping:
            mapping.write({
                "use_count": mapping.use_count + 1,
                "last_used_at": fields.Datetime.now(),
            })
            # A saved equivalence proposes the current ITEM but never approves
            # it. The operator must explicitly confirm every imported line.
            return mapping.product_id, 60.0, "ambiguous"
        exact = Product.search([
            "|", ("default_code", "=ilike", normalized), ("barcode", "=", normalized)
        ], limit=2)
        if len(exact) == 1:
            return exact, 100.0, "matched"
        class_map = {
            "SINGLE HUNG": "SH",
            "SLIDING WINDOW": "RW",
            "FIX WINDOW": "FIX",
        }
        product_class = next(
            (target for source, target in class_map.items() if source in normalized.upper()),
            False,
        )
        size_match = re.search(r"(.+?)\s*[Xx]\s*(.+)", attributes.get("size", ""))
        width = self._ddhi_decimal_dimension(size_match.group(1)) if size_match else False
        height = self._ddhi_decimal_dimension(size_match.group(2)) if size_match else False
        color_map = {"BLANCO": "white", "BLANCA": "white", "WHITE": "white"}
        color = color_map.get(attributes.get("color", "").upper(), attributes.get("color", "").lower())
        glass = attributes.get("glass", "").lower()
        domain = [("is_storable", "=", True), ("active", "=", True)]
        for token in (product_class, width, height, color, glass):
            if token:
                domain.append(("product_template_attribute_value_ids.name", "=ilike", token))
        candidates_recordset = Product.search(domain, limit=3) if product_class else Product
        if len(candidates_recordset) == 1:
            return candidates_recordset, 95.0, "matched"
        candidates = Product.name_search(name=normalized, args=[("is_storable", "=", True)], limit=3)
        if any(attributes.values()):
            # A matching legacy name is not enough for configured doors and
            # windows. Different dimensions, swing, color or glass represent
            # a different physical ITEM and must remain under human review.
            return Product, 0.0, "unmatched" if not candidates else "ambiguous"
        if len(candidates) == 1:
            return Product.browse(candidates[0][0]), 85.0, "matched"
        return Product, 0.0, "unmatched" if not candidates else "ambiguous"

    def action_mark_ready(self):
        for document in self:
            if document.needs_review:
                raise UserError(_(
                    "Complete número, fecha, cliente y todas las coincidencias de ITEM antes de enviar a aprobación."
                ))
            duplicate = self.env["doorandoor.historical.delivery"].search_count([
                ("external_reference", "=", document.external_reference.strip().upper()),
                ("company_id", "=", document.company_id.id),
            ])
            if duplicate:
                raise UserError(_("La factura histórica %s ya tiene una entrega registrada.") % document.external_reference)
            document._save_reviewed_product_mappings()
            document.write({
                "state": "ready",
                "reviewed_by_id": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            })
        return True

    def _save_reviewed_product_mappings(self):
        Mapping = self.env["doorandoor.legacy.product.mapping"]
        for document in self:
            for line in document.line_ids.filtered(
                lambda item: item.product_id and item.quantity > 0
                and item.match_state == "matched" and item.mapping_confirmed
            ):
                key = {
                    "company_id": document.company_id.id,
                    "source_system": document.source_system or "unknown",
                    "legacy_name": self._ddhi_normalize_mapping_value(line.description),
                    "legacy_size": self._ddhi_normalize_mapping_value(line.legacy_size),
                    "legacy_swing": self._ddhi_normalize_mapping_value(line.legacy_swing),
                    "legacy_color": self._ddhi_normalize_mapping_value(line.legacy_color),
                    "legacy_glass": self._ddhi_normalize_mapping_value(line.legacy_glass),
                    "legacy_model": self._ddhi_normalize_mapping_value(line.legacy_model),
                }
                mapping = Mapping.search([(field, "=", value) for field, value in key.items()], limit=1)
                values = dict(key, product_id=line.product_id.id, active=True)
                if mapping:
                    mapping.write(values)
                else:
                    Mapping.create(values)

    def _check_can_approve(self):
        if not (
            self.env.user.has_group("base.group_system")
            or self.env.user.has_group(
                "doorandoor_import_historic_invoices.group_legacy_delivery_ocr_supervisor"
            )
        ):
            raise AccessError(_("Solo Yuliet, Supervisores autorizados o Administrador/Ajustes pueden aprobar la importación."))

    def action_approve_and_create_delivery(self):
        self._check_can_approve()
        for document in self:
            if document.state != "ready" or document.needs_review:
                raise UserError(_("El documento debe estar completamente revisado antes de aprobarlo."))
            history = self.env["doorandoor.historical.delivery"].create({
                "external_reference": document.external_reference,
                "sale_date": document.sale_date,
                "partner_id": document.partner_id.id,
                "warehouse_id": document.warehouse_id.id,
                "supply_warehouse_id": document.supply_warehouse_id.id,
                "payment_note": document.payment_note,
                "ddhl_inventory_treatment": document.inventory_treatment,
                "ddhl_exclusion_reason": document.inventory_treatment_reason,
                "note": _("Importado por OCR desde %(document)s. Huella: %(hash)s") % {
                    "document": document.name, "hash": document.file_sha256,
                },
                "line_ids": [(0, 0, {
                    "product_id": line.product_id.id,
                    "quantity": line.quantity,
                }) for line in document.line_ids.filtered(lambda item: item.quantity > 0)],
            })
            attachment = self.env["ir.attachment"].create({
                "name": document.file_name,
                "datas": document.file_data,
                "mimetype": "application/pdf",
                "res_model": history._name,
                "res_id": history.id,
            })
            history.evidence_attachment_ids = [(4, attachment.id)]
            # Normal historical imports consume labels that already exist in
            # Odoo.  A receipt/new-label cycle is allowed only when the reviewer
            # explicitly classifies the case as an exceptional regularization.
            if (
                document.inventory_treatment == "existing_stock"
                and hasattr(history, "action_ddhl_prepare_existing_stock")
            ):
                history.action_ddhl_prepare_existing_stock()
            elif (
                document.inventory_treatment == "excluded_legacy"
                and hasattr(history, "action_ddhl_mark_excluded")
            ):
                history.action_ddhl_mark_excluded()
            elif hasattr(history, "action_ddhl_start_predispatch_cycle"):
                history.action_ddhl_start_predispatch_cycle()
            else:
                history.action_create_operation()
            document.write({
                "state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_at": fields.Datetime.now(),
                "historical_delivery_id": history.id,
            })
            document.message_post(body=_(
                "Aprobado por %(user)s. Se creó %(history)s sin factura contable. "
                "Tratamiento de inventario: %(treatment)s. "
                "No se generan recepciones ni labels nuevos salvo regularización excepcional."
            ) % {
                "user": self.env.user.display_name,
                "history": history.name,
                "treatment": dict(document._fields["inventory_treatment"].selection).get(
                    document.inventory_treatment
                ),
            })
        return True

    def action_open_historical_delivery(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "doorandoor.historical.delivery",
            "res_id": self.historical_delivery_id.id,
            "view_mode": "form",
            "target": "current",
        }


class LegacyDeliveryOCRLine(models.Model):
    _name = "doorandoor.legacy.delivery.ocr.line"
    _description = "Línea OCR de venta histórica"
    _order = "id"

    document_id = fields.Many2one(
        "doorandoor.legacy.delivery.ocr", required=True, ondelete="cascade",
    )
    source_text = fields.Char(string="Texto original", readonly=True)
    description = fields.Char(string="Descripción detectada", required=True)
    billed_quantity = fields.Float(
        string="Facturado", required=True, default=1.0,
        digits="Product Unit of Measure",
    )
    delivered_quantity = fields.Float(
        string="Ya entregado", default=0.0, digits="Product Unit of Measure",
    )
    quantity = fields.Float(required=True, default=1.0, digits="Product Unit of Measure")
    logistic_notes = fields.Char(string="Notas logísticas", readonly=True)
    legacy_size = fields.Char(string="Medida anterior", readonly=True)
    legacy_swing = fields.Char(string="Mano anterior", readonly=True)
    legacy_color = fields.Char(string="Color anterior", readonly=True)
    legacy_glass = fields.Char(string="Cristal anterior", readonly=True)
    legacy_model = fields.Char(string="Modelo anterior", readonly=True)
    product_id = fields.Many2one(
        "product.product", string="ITEM", domain="[('is_storable', '=', True)]",
    )
    confidence = fields.Float(string="Confianza %", readonly=True)
    match_state = fields.Selection(
        [("matched", "Coincidencia"), ("ambiguous", "Ambigua"), ("unmatched", "Sin coincidencia")],
        default="unmatched", required=True,
    )
    mapping_proposed = fields.Boolean(string="Propuesto por diccionario", readonly=True)
    mapping_confirmed = fields.Boolean(string="ITEM revisado por operador")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.match_state = "matched"
            self.mapping_confirmed = True
            if not self.mapping_proposed:
                self.confidence = 100.0

    @api.onchange("mapping_confirmed")
    def _onchange_mapping_confirmed(self):
        for line in self:
            if line.mapping_proposed and line.mapping_confirmed and line.product_id:
                line.match_state = "matched"
                line.confidence = min(line.confidence or 60.0, 60.0)
            elif line.mapping_proposed and not line.mapping_confirmed:
                line.match_state = "ambiguous"

    @api.constrains("quantity")
    def _check_quantity(self):
        if any(line.quantity < 0 for line in self):
            raise ValidationError(_("La cantidad pendiente no puede ser negativa."))

    def action_open_historical_special_wizard(self):
        self.ensure_one()
        if self.document_id.state not in ("review", "ready"):
            raise UserError(_("El documento OCR debe estar en revisión para crear el especial histórico."))
        wizard = self.env["doorandoor.legacy.special.product.wizard"].create({
            "line_id": self.id,
            "name": self.description,
            "size": self.legacy_size,
            "swing": self.legacy_swing,
            "color": self.legacy_color,
            "glass": self.legacy_glass,
            "model_code": self.legacy_model,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Crear ITEM especial histórico"),
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }


class LegacyProductMapping(models.Model):
    _name = "doorandoor.legacy.product.mapping"
    _description = "Equivalencia de producto histórico"
    _rec_name = "legacy_name"
    _order = "source_system, legacy_name, legacy_size"

    source_system = fields.Selection(
        [("zoho", "Zoho"), ("quickbooks", "QuickBooks"), ("unknown", "No identificado")],
        required=True, index=True,
    )
    legacy_name = fields.Char(string="Nombre anterior", required=True, index=True)
    legacy_size = fields.Char(string="Medida anterior", required=True, default="")
    legacy_swing = fields.Char(string="Mano anterior", required=True, default="")
    legacy_color = fields.Char(string="Color anterior", required=True, default="")
    legacy_glass = fields.Char(string="Cristal anterior", required=True, default="")
    legacy_model = fields.Char(string="Modelo anterior", required=True, default="")
    product_id = fields.Many2one(
        "product.product", string="ITEM actual", required=True,
        domain="[('is_storable', '=', True)]", ondelete="restrict", index=True,
    )
    use_count = fields.Integer(string="Usos automáticos", readonly=True)
    last_used_at = fields.Datetime(string="Último uso", readonly=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )

    _sql_constraints = [
        (
            "legacy_product_mapping_unique",
            "unique(company_id, source_system, legacy_name, legacy_size, legacy_swing, legacy_color, legacy_glass, legacy_model)",
            "Ya existe una asociación para esta firma de producto anterior.",
        ),
    ]
