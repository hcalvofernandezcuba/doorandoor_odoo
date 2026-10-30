from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import time

_logger = logging.getLogger(__name__)


class ZohoPartnerImport(models.TransientModel):
    _name = "zoho.partner.import"
    _description = "Import Partners from Zoho"
    _transient_max_hours = 0.25

    connector_id = fields.Many2one("zoho.connector", string="Zoho Connector", required=True)
    partner_type = fields.Selection([
        ("customer", "Customers Only"),
        ("vendor", "Vendors Only"),
        ("both", "Both Customers and Vendors")
    ], string="Partner Type", default="both", required=True)
    update_existing = fields.Boolean(string="Update Existing Partners", default=True)

    def _extract_zoho_error(self, response):
        try:
            error_data = response.json()
        except ValueError:
            return response.text[:500] or str(response.status_code)

        message = error_data.get("message") or error_data.get("error") or response.text[:500]
        code = error_data.get("code")
        if code:
            return f"[{code}] {message}"
        return message

    def action_import_partners(self):
        self.ensure_one()
        connector = self.connector_id

        if connector.state != "active":
            raise UserError(_("Connector is not active!"))

        import_types = []
        if self.partner_type in ["customer", "both"]:
            if not connector.import_customers:
                raise UserError(_("Customer import is not enabled in connector settings."))
            import_types.append("customer")

        if self.partner_type in ["vendor", "both"]:
            if not connector.import_vendors:
                raise UserError(_("Vendor import is not enabled in connector settings."))
            import_types.append("vendor")

        results = {}
        for imp_type in import_types:
            log = self.env["zoho.import.log"].create({
                "connector_id": connector.id,
                "import_type": imp_type,
                "state": "in_progress",
                "start_time": fields.Datetime.now(),
            })

            try:
                result = self._import_contacts(connector, imp_type, log)
                results[imp_type] = result
                connector.write({"last_partner_sync": fields.Datetime.now()})

            except Exception as e:
                log.write({
                    "state": "error",
                    "error_details": str(e),
                    "end_time": fields.Datetime.now(),
                })
                raise UserError(_("Failed to import %s: %s") % (imp_type, str(e)))

        total_imported = sum(r.get("imported", 0) for r in results.values())
        total_updated = sum(r.get("updated", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import Complete"),
                "message": _("Partners: %(imported)s created, %(updated)s updated, %(failed)s failed") % {
                    "imported": total_imported, "updated": total_updated, "failed": total_failed
                },
                "type": "success" if total_failed == 0 else "warning",
                "sticky": False,
            }
        }

    def _import_contacts(self, connector, contact_type, log):
        all_contacts = self._fetch_contacts(connector, contact_type)
        total = len(all_contacts)
        imported = 0
        updated = 0
        failed = 0
        errors = []
        created_partners = self.env["res.partner"]

        for contact in all_contacts:
            try:
                # The contacts collection endpoint only returns summary data.
                # Addresses and contact persons are available in the detail
                # endpoint, so always enrich the record before mapping it.
                detailed_contact = self._fetch_contact_detail(connector, contact)
                result = self._create_or_update_partner(
                    connector, detailed_contact, contact_type
                )
                if result.get("created"):
                    created_partners |= result.get("partner")
                    imported += 1
                elif result.get("updated"):
                    updated += 1
            except Exception as e:
                failed += 1
                error_msg = f"Contact '{contact.get('contact_name', 'Unknown')}': {str(e)}"
                errors.append(error_msg)
                _logger.error(error_msg)

        state = "done"
        if failed > 0 and (imported > 0 or updated > 0):
            state = "partial"
        elif failed > 0 and imported == 0 and updated == 0:
            state = "error"

        log.write({
            "state": state,
            "total_records": total,
            "imported_records": imported,
            "updated_records": updated,
            "failed_records": failed,
            "error_details": "\n".join(errors) if errors else False,
            "partner_ids": [(6, 0, created_partners.ids)],
            "end_time": fields.Datetime.now(),
        })

        return {
            "imported": imported,
            "updated": updated,
            "failed": failed,
        }

    def _fetch_contacts(self, connector, contact_type):
        all_contacts = []
        page = 1

        while True:
            url = connector._get_api_url("contacts")
            params = {
                "page": page,
                "per_page": 200,
                "contact_type": contact_type,
            }

            try:
                response = requests.get(url, headers=connector._get_headers(),
                                        params=params, timeout=60)
                if response.status_code != 200:
                    raise UserError(_("Zoho API error while fetching contacts: %s") % self._extract_zoho_error(response))
            except requests.exceptions.RequestException as e:
                raise UserError(_("Failed to fetch contacts: %s") % str(e))

            data = response.json()
            contacts = data.get("contacts", [])

            if not contacts:
                break

            all_contacts.extend(contacts)
            page += 1

            if page > 200:
                _logger.warning("Reached max page limit for contacts")
                break

        _logger.info("Fetched %s %s contacts from Zoho", len(all_contacts), contact_type)
        return all_contacts

    def _fetch_contact_detail(self, connector, contact):
        """Return the complete Zoho contact, including its addresses.

        Zoho's paginated ``contacts`` response deliberately omits
        ``billing_address``, ``shipping_address`` and ``contact_persons``.
        Importing that summary directly silently cleared those fields in Odoo.
        The detail endpoint is therefore required for a complete partner sync.
        """
        contact_id = contact.get("contact_id")
        if not contact_id:
            raise UserError(_("Zoho contact has no contact_id."))

        url = connector._get_api_url("contacts/%s" % contact_id)
        last_error = False
        for attempt in range(1, 6):
            try:
                response = requests.get(
                    url,
                    headers=connector._get_headers(),
                    timeout=60,
                )
            except requests.exceptions.RequestException as error:
                last_error = str(error)
            else:
                if response.status_code == 200:
                    detail = response.json().get("contact")
                    if not detail:
                        raise UserError(
                            _("Zoho returned no detail for contact %s.") % contact_id
                        )
                    return detail

                last_error = self._extract_zoho_error(response)
                if response.status_code not in (429, 500, 502, 503, 504):
                    break

                retry_after = response.headers.get("Retry-After")
                try:
                    delay = max(float(retry_after), 1.0)
                except (TypeError, ValueError):
                    delay = min(2 ** attempt, 30)
                _logger.warning(
                    "Zoho contact %s detail request returned HTTP %s; "
                    "retrying in %s seconds (attempt %s/5)",
                    contact_id,
                    response.status_code,
                    delay,
                    attempt,
                )
                time.sleep(delay)

        raise UserError(
            _("Could not fetch complete Zoho contact %(contact)s: %(error)s")
            % {"contact": contact_id, "error": last_error or _("Unknown error")}
        )

    def _create_or_update_partner(self, connector, zoho_data, contact_type):
        Partner = self.env["res.partner"]

        zoho_id = zoho_data.get("contact_id")
        name = zoho_data.get("contact_name")
        email = zoho_data.get("email")

        if not name:
            return {"partner": False, "created": False, "updated": False}

        domain = [("zoho_contact_id", "=", zoho_id)]
        if email:
            domain = ["|"] + domain + [("email", "=", email)]

        existing = Partner.search(domain, limit=1)

        is_customer = contact_type == "customer"
        is_vendor = contact_type == "vendor"

        # === DIRECCIONES ===
        billing = zoho_data.get("billing_address", {}) or {}
        shipping = zoho_data.get("shipping_address", {}) or {}

        # === DATOS PRINCIPALES DEL CONTACTO ===
        vals = {
            "name": name,
            "zoho_contact_id": zoho_id,
            "zoho_synced": True,
            "zoho_sync_date": fields.Datetime.now(),
            "email": email,
            "phone": zoho_data.get("phone"),
            "mobile": zoho_data.get("mobile"),
            "website": zoho_data.get("website"),
            # NIT/ID Fiscal - Zoho usa tax_id, gst_no, o cf_tax_id en custom fields
            "vat": self._extract_tax_id(zoho_data),
            "street": billing.get("address"),
            "street2": billing.get("street2"),
            "city": billing.get("city"),
            "zip": billing.get("zip"),
            "state_id": self._get_state(billing.get("state")),
            "country_id": self._get_country(
                billing.get("country"), billing.get("country_code")
            ),
            "customer_rank": 1 if is_customer else 0,
            "supplier_rank": 1 if is_vendor else 0,
            "is_company": zoho_data.get("contact_type") == "company",
            "company_type": "company" if zoho_data.get("contact_type") == "company" else "person",
            "comment": zoho_data.get("notes"),
            # NUEVOS CAMPOS
            "commercial_company_name": zoho_data.get("company_name"),
            "credit_limit": float(zoho_data.get("credit_limit", 0) or 0),
            "lang": self._map_language(zoho_data.get("language_code")),
            "ref": zoho_data.get("contact_name"),  # Referencia interna
        }

        # === TÉRMINOS DE PAGO ===
        payment_term = self._map_payment_terms(zoho_data.get("payment_terms"), 
                                                 zoho_data.get("payment_terms_label"))
        if payment_term:
            if is_customer:
                vals["property_payment_term_id"] = payment_term
            if is_vendor:
                vals["property_supplier_payment_term_id"] = payment_term

        # === MONEDA Y LISTA DE PRECIOS ===
        if zoho_data.get("currency_code"):
            currency = self.env["res.currency"].search([
                ("name", "=", zoho_data["currency_code"])
            ], limit=1)
            if currency:
                pricelist = self.env["product.pricelist"].search([
                    ("currency_id", "=", currency.id)
                ], limit=1)
                if pricelist:
                    vals["property_product_pricelist"] = pricelist.id

        # === CREAR O ACTUALIZAR ===
        if existing and self.update_existing:
            existing.write(vals)
            partner = existing
            created = False
            updated = True
        elif not existing:
            partner = Partner.create(vals)
            created = True
            updated = False
        else:
            return {"partner": existing, "created": False, "updated": False, "skipped": True}

        # === CONTACTOS/ PERSONAS ASOCIADAS (contact_persons) ===
        self._import_contact_persons(partner, zoho_data.get("contact_persons", []))

        # === DIRECCIÓN DE ENVÍO COMO CONTACTO HIJO ===
        if self._address_has_content(shipping):
            self._create_shipping_address(partner, shipping)

        # === ETIQUETAS / TAGS ===
        if zoho_data.get("tags"):
            self._assign_tags(partner, zoho_data["tags"])

        return {"partner": partner, "created": created, "updated": updated}

    def _extract_tax_id(self, zoho_data):
        """
        Extrae el NIT/ID fiscal de múltiples campos posibles en Zoho.
        Zoho puede tener: tax_id, gst_no, o custom fields como cf_tax_id, cf_nit, cf_ruc, etc.
        """
        # Campos estándar de Zoho
        for field in ["tax_id", "gst_no", "tax_id_formatted"]:
            value = zoho_data.get(field)
            if value:
                return value

        # Custom fields (cf_*) comunes para identificación fiscal
        custom_fields = zoho_data.get("custom_fields", []) or []
        for cf in custom_fields:
            label = (cf.get("label") or "").lower()
            value = cf.get("value")
            if value and any(keyword in label for keyword in ["tax", "nit", "ruc", "id", "cif", "dni", "cedula", "rut", "cnpj"]):
                return value

        # También buscar directamente en el dict si vienen como cf_tax_id, etc.
        for key, value in zoho_data.items():
            if key.startswith("cf_") and value:
                if any(keyword in key.lower() for keyword in ["tax", "nit", "ruc", "id_fiscal"]):
                    return value

        return False

    def _map_language(self, zoho_lang):
        """Mapea códigos de idioma de Zoho a códigos de Odoo."""
        if not zoho_lang:
            return False
        
        lang_map = {
            "en": "en_US",
            "en-US": "en_US",
            "es": "es_ES",
            "es-ES": "es_ES",
            "es-MX": "es_MX",
            "fr": "fr_FR",
            "de": "de_DE",
            "pt": "pt_PT",
            "pt-BR": "pt_BR",
            "it": "it_IT",
            "ja": "ja_JP",
            "zh": "zh_CN",
            "ru": "ru_RU",
            "ko": "ko_KR",
        }
        
        odoo_lang = lang_map.get(zoho_lang, zoho_lang)
        
        # Verificar que el idioma existe en Odoo
        lang_obj = self.env["res.lang"].search([("code", "=", odoo_lang)], limit=1)
        return odoo_lang if lang_obj else False

    def _map_payment_terms(self, terms_days, terms_label):
        """
        Busca o crea términos de pago basados en los días o la etiqueta de Zoho.
        """
        if not terms_days and not terms_label:
            return False

        AccountPaymentTerm = self.env["account.payment.term"]

        # Si hay etiqueta, buscar por nombre
        if terms_label:
            term = AccountPaymentTerm.search([("name", "ilike", terms_label)], limit=1)
            if term:
                return term.id

        # Si hay días, buscar o crear
        if terms_days:
            try:
                days = int(terms_days)
                term_name = f"{days} Days" if days > 0 else "Immediate Payment"
                
                term = AccountPaymentTerm.search([("name", "=", term_name)], limit=1)
                if term:
                    return term.id
                
                # Crear nuevo término de pago si no existe
                new_term = AccountPaymentTerm.create({
                    "name": term_name,
                    "line_ids": [(0, 0, {
                        "value": "percent" if days == 0 else "balance",
                        "days": days,
                        "end_month": False,
                    })]
                })
                return new_term.id
            except (ValueError, TypeError):
                pass

        return False

    def _import_contact_persons(self, partner, contact_persons):
        """
        Importa las personas de contacto asociadas como contactos hijos en Odoo.
        Zoho: contact_persons[{salutation, first_name, last_name, email, phone, mobile, designation}]
        """
        if not contact_persons:
            return

        for person in contact_persons:
            if not person.get("first_name") and not person.get("last_name"):
                continue

            first_name = person.get("first_name", "")
            last_name = person.get("last_name", "")
            person_name = f"{first_name} {last_name}".strip()
            if not person_name:
                continue

            # Buscar si ya existe este contacto hijo
            existing_child = self.env["res.partner"].search([
                ("parent_id", "=", partner.id),
                ("name", "=", person_name),
            ], limit=1)

            child_vals = {
                "name": person_name,
                "parent_id": partner.id,
                "type": "contact",
                "email": person.get("email"),
                "phone": person.get("phone"),
                "mobile": person.get("mobile"),
                "function": person.get("designation"),  # Cargo/Posición
                "title": self._get_title(person.get("salutation")),
                "company_type": "person",
            }

            if existing_child:
                existing_child.write(child_vals)
            else:
                self.env["res.partner"].create(child_vals)

    def _create_shipping_address(self, partner, shipping_data):
        """
        Crea la dirección de envío como un contacto hijo de tipo 'delivery'.
        """
        if not self._address_has_content(shipping_data):
            return

        # Verificar si ya existe una dirección de envío
        existing_shipping = self.env["res.partner"].search([
            ("parent_id", "=", partner.id),
            ("type", "=", "delivery"),
        ], limit=1)

        shipping_vals = {
            "name": f"{partner.name} - Shipping",
            "parent_id": partner.id,
            "type": "delivery",
            "street": shipping_data.get("address"),
            "street2": shipping_data.get("street2"),
            "city": shipping_data.get("city"),
            "zip": shipping_data.get("zip"),
            "state_id": self._get_state(shipping_data.get("state")),
            "country_id": self._get_country(
                shipping_data.get("country"), shipping_data.get("country_code")
            ),
            "phone": shipping_data.get("phone"),
        }

        if existing_shipping:
            existing_shipping.write(shipping_vals)
        else:
            self.env["res.partner"].create(shipping_vals)

    def _assign_tags(self, partner, tags_data):
        """
        Asigna etiquetas/tags al partner. Zoho envía tags como lista de strings o dicts.
        """
        if not tags_data:
            return

        PartnerCategory = self.env["res.partner.category"]
        tag_ids = []

        # Zoho puede enviar tags como string separado por comas o como lista
        if isinstance(tags_data, str):
            tag_names = [t.strip() for t in tags_data.split(",")]
        elif isinstance(tags_data, list):
            tag_names = []
            for tag in tags_data:
                if isinstance(tag, dict):
                    tag_names.append(tag.get("tag_option_name", ""))
                else:
                    tag_names.append(str(tag))
        else:
            tag_names = []

        for tag_name in tag_names:
            if not tag_name:
                continue
            
            tag = PartnerCategory.search([("name", "=", tag_name)], limit=1)
            if not tag:
                tag = PartnerCategory.create({"name": tag_name})
            tag_ids.append(tag.id)

        if tag_ids:
            partner.write({"category_id": [(6, 0, tag_ids)]})

    def _get_title(self, salutation):
        """Mapea saludos de Zoho a títulos de Odoo (Mr., Mrs., etc.)"""
        if not salutation:
            return False
        
        salutation = salutation.strip().lower()
        title_map = {
            "mr": "Mr.",
            "mr.": "Mr.",
            "mrs": "Mrs.",
            "mrs.": "Mrs.",
            "ms": "Ms.",
            "ms.": "Ms.",
            "dr": "Dr.",
            "dr.": "Dr.",
            "prof": "Prof.",
            "prof.": "Prof.",
        }
        
        title_name = title_map.get(salutation)
        if not title_name:
            return False

        title = self.env["res.partner.title"].search([("name", "=", title_name)], limit=1)
        if not title:
            title = self.env["res.partner.title"].create({"name": title_name})
        return title.id

    def _get_state(self, state_name):
        if not state_name:
            return False
        state = self.env["res.country.state"].search([
            ("name", "ilike", state_name)
        ], limit=1)
        return state.id if state else False

    def _address_has_content(self, address_data):
        """Ignore Zoho address shells that only contain technical IDs."""
        if not address_data:
            return False
        address_fields = (
            "address", "street2", "city", "zip", "state", "country",
            "country_code", "phone", "attention",
        )
        return any(address_data.get(field_name) for field_name in address_fields)

    def _get_country(self, country_name, country_code=False):
        if country_code:
            country = self.env["res.country"].search([
                ("code", "=ilike", country_code)
            ], limit=1)
            if country:
                return country.id
        if not country_name:
            return False
        country = self.env["res.country"].search([
            ("name", "ilike", country_name)
        ], limit=1)
        return country.id if country else False
