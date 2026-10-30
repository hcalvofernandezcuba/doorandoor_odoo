import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWarehouseParser(TransactionCase):
    def _parse(self, text):
        return list(self.env["ddii.inventory.import"]._parse_warehouse(text))

    def test_complete_and_incomplete_door_rows_are_preserved(self):
        rows = self._parse("""
1 LITE   24   80 SLAB     238
1 SMALL LITE   36   80           32
CARRARA   24      SLAB     48
MONROE    24   96 SLAB
""")
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["qty"], "238")
        self.assertEqual(rows[1].get("configuration"), None)
        self.assertEqual(rows[1]["qty"], "32")
        self.assertEqual(rows[2].get("height"), None)
        self.assertEqual(rows[2]["qty"], "48")
        self.assertEqual(rows[3]["qty"], None)

    def test_hardware_frames_and_blank_quantities_are_preserved(self):
        rows = self._parse("""
BLACK HINGES      3.5       3.5
BLACK HIDDEN HINGES
FRAME X 80      1 1/4 4 9/16 RH
FRAME PIANO                     RH /LH   1390
FRAME PIANO                     LH
""")
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["width"], "3.5")
        self.assertEqual(rows[1]["qty"], None)
        self.assertEqual(rows[2]["configuration"], "RH")
        self.assertEqual(rows[3]["qty"], "1390")
        self.assertEqual(rows[4]["qty"], None)

    def test_wrapped_molding_and_baseboard_rows_are_reconstructed(self):
        rows = self._parse("""
MOLDING       1/2\" X 3 17'
                       1/2\"              339
BASEBOARD 1/2\" X 3 16' 1/2\"              400
""")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["model"], 'MOLDING 1/2" X 3 1/2" X 17\'')
        self.assertEqual(rows[0]["qty"], "339")
        self.assertEqual(rows[1]["model"], 'BASEBOARD 1/2" X 3 1/2" X 16\'')
        self.assertEqual(rows[1]["qty"], "400")

    def test_analyze_defaults_missing_door_color_and_blank_quantity_for_review(self):
        inventory_import = self.env["ddii.inventory.import"].new({
            "source_format": "tampa_warehouse_pdf",
        })
        parsed = list(inventory_import._parse_warehouse("MONROE 24 96 SLAB"))[0]
        self.assertEqual(parsed["row_type"], "door")
        self.assertIsNone(parsed.get("qty"))

    def _new_import(self):
        location = self.env["stock.location"].search([
            ("usage", "=", "internal"),
            ("company_id", "in", [False, self.env.company.id]),
        ], limit=1)
        return self.env["ddii.inventory.import"].create({
            "source_format": "tampa_warehouse_pdf",
            "location_id": location.id,
            "source_file": base64.b64encode(b"test source"),
            "state": "review",
        })

    def test_force_matched_only_keeps_matches_and_excludes_untouched_unresolved(self):
        inventory_import = self._new_import()
        product = self.env["product.product"].create({
            "name": "DDII force test product",
            "is_storable": True,
        })
        matched = self.env["ddii.inventory.import.line"].create({
            "import_id": inventory_import.id,
            "source_line": 1,
            "source_model": "MATCHED",
            "quantity": 3,
            "quantity_present": True,
            "product_id": product.id,
            "match_state": "matched",
        })
        ambiguous = self.env["ddii.inventory.import.line"].create({
            "import_id": inventory_import.id,
            "source_line": 2,
            "source_model": "AMBIGUOUS",
            "quantity": 4,
            "quantity_present": True,
            "match_state": "ambiguous",
            "candidate_count": 2,
        })

        inventory_import.action_force_matched_only()

        self.assertFalse(matched.excluded)
        self.assertTrue(ambiguous.excluded)
        self.assertIn("Force matched ITEMs", ambiguous.exclusion_reason)

    def test_force_matched_only_protects_edited_ambiguity(self):
        inventory_import = self._new_import()
        self.env["ddii.inventory.import.line"].create({
            "import_id": inventory_import.id,
            "source_line": 7,
            "source_model": "EDITED AMBIGUOUS",
            "quantity": 1,
            "quantity_present": True,
            "match_state": "ambiguous",
            "candidate_count": 2,
            "manually_edited": True,
        })

        with self.assertRaises(ValidationError):
            inventory_import.action_force_matched_only()

    def test_automatic_ambiguity_is_not_marked_as_manual_edit(self):
        inventory_import = self._new_import()
        token = "DDIIAUTOMATICAMBIGUITY"
        for suffix in ("A", "B"):
            self.env["product.product"].create({
                "name": "%s %s" % (token, suffix),
                "is_storable": True,
            })
        line = self.env["ddii.inventory.import.line"].create({
            "import_id": inventory_import.id,
            "source_line": 9,
            "source_model": token,
            "quantity": 1,
            "quantity_present": True,
        })

        line._match_variant()

        self.assertEqual(line.match_state, "ambiguous")
        self.assertFalse(line.manually_edited)
