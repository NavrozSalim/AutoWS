"""Unit tests for the riskiest logic: mapper escaping/cents and validation."""
import json
from types import SimpleNamespace

from django.test import SimpleTestCase

from lasoo.lasoo_queries import build_payload, extract_lasoo_failure_message
from lasoo.services import mapper, validator


class MapperTests(SimpleTestCase):
    def test_dollars_to_cents(self):
        self.assertEqual(mapper.dollars_to_cents("199.99"), 19999)
        self.assertEqual(mapper.dollars_to_cents(185.99), 18599)
        self.assertEqual(mapper.dollars_to_cents(0), 0)

    def test_dollars_to_cents_invalid(self):
        with self.assertRaises(ValueError):
            mapper.dollars_to_cents("abc")

    def test_normalize_image_urls(self):
        self.assertEqual(
            mapper.normalize_image_urls("a.jpg, b.jpg ; c.jpg"),
            "a.jpg|b.jpg|c.jpg",
        )
        self.assertEqual(mapper.normalize_image_urls(["a", "b"]), "a|b")
        self.assertEqual(mapper.normalize_image_urls(""), "")

    def test_external_data_object_is_valid_json_string(self):
        data = {
            "title": "Product Title",
            "description": "A description",
            "image_urls": "https://a.com/1.jpg|https://b.com/2.jpg",
            "brand": "BrandName",
            "category": "Furniture > Living Room",
            "sku": "SKU-1",
            "barcode": "123456789012",
        }
        raw = mapper.build_external_data_object(data)
        parsed = json.loads(raw)  # must round-trip cleanly (escaped exactly once)
        self.assertEqual(parsed["productName"], "Product Title")
        self.assertEqual(parsed["Image URLS"], "https://a.com/1.jpg|https://b.com/2.jpg")
        self.assertEqual(parsed["Barcode"], "123456789012")
        self.assertNotIn("externalRegionKey", parsed)

    def test_external_data_object_omits_blank_barcode(self):
        data = {"title": "t", "description": "d", "image_urls": "a", "brand": "b",
                "category": "", "sku": "s", "barcode": ""}
        parsed = json.loads(mapper.build_external_data_object(data))
        self.assertNotIn("Barcode", parsed)

    def test_resolve_keys_falls_back_to_sku(self):
        self.assertEqual(mapper.resolve_keys({"sku": "SKU-1"}), ("SKU-1", "SKU-1"))
        self.assertEqual(
            mapper.resolve_keys({"sku": "SKU-1", "product_key": "P", "variant_key": "V"}),
            ("P", "V"),
        )

    def test_bulk_upsert_payload_shape(self):
        data = {"title": "t", "description": "d", "image_urls": "a", "brand": "b",
                "category": "c", "sku": "s", "original_price": "10", "sale_price": "8",
                "inventory": "5", "infinite_quantity": False}
        payload = mapper.build_bulk_upsert_payload([data], "AUTHKEY")
        self.assertEqual(payload["query"], "Variants_BulkUpsert")
        self.assertEqual(payload["auth"], "AUTHKEY")
        variant = payload["data"]["variants"][0]
        self.assertEqual(variant["variantOriginalPriceCents"], 1000)
        self.assertEqual(variant["variantSalePriceCents"], 800)
        self.assertEqual(variant["externalDataFormat"], "JSON")


class LasooQueriesTests(SimpleTestCase):
    def test_test_payload_matches_lasoo_spec(self):
        payload = build_payload("test")
        self.assertEqual(payload["query"], "Core_TestNoAuthentication")
        self.assertEqual(payload["name"], "Core - TestNoAuthentication : 1.0.0")
        self.assertNotIn("auth", payload)

    def test_bulk_payload_includes_auth(self):
        payload = build_payload("bulk_upsert", data={"variants": []}, auth="KEY")
        self.assertEqual(payload["query"], "Variants_BulkUpsert")
        self.assertEqual(payload["auth"], "KEY")

    def test_orders_uses_invoices_search(self):
        payload = build_payload("orders", data={"page": 1}, auth="KEY")
        self.assertEqual(payload["query"], "Invoices_Search")
        self.assertEqual(payload["name"], "Invoices - Search : 1.0.0")
        self.assertEqual(payload["auth"], "KEY")

    def test_shipping_uses_shipments_upsert(self):
        payload = build_payload("shipping", data={}, auth="KEY")
        self.assertEqual(payload["query"], "Shipments_Upsert")
        self.assertEqual(payload["name"], "Shipments - Upsert : 1.0.0")

    def test_shipments_search_spec(self):
        payload = build_payload("shipments_search", data={"invoiceId": 1}, auth="KEY")
        self.assertEqual(payload["query"], "Shipments_Search")

    def test_create_test_order_spec(self):
        payload = build_payload("create_test_order", data={}, auth="KEY")
        self.assertEqual(payload["query"], "Orders_CreateTestOrder")
        self.assertEqual(payload["name"], "Orders - CreateTestOrder : 1.0.0")

    def test_variants_search_and_delete_specs(self):
        self.assertEqual(
            build_payload("variants_search", data={}, auth="K")["query"],
            "Variants_Search",
        )
        self.assertEqual(
            build_payload("bulk_delete", data={"keys": []}, auth="K")["query"],
            "Variants_BulkDelete",
        )

    def test_extract_lasoo_failure_message(self):
        msg = extract_lasoo_failure_message(
            {"message": "Fail.. Query does not exist. Check the name and version"}
        )
        self.assertIn("Query does not exist", msg or "")


class VariantDeleteTests(SimpleTestCase):
    def test_environments_for_staging_upload(self):
        from lasoo.models import ListingStatus
        from lasoo.services import variant_delete_service

        listing = SimpleNamespace(
            status=ListingStatus.UPLOADED_STAGING,
        )
        self.assertEqual(
            variant_delete_service.environments_for_listing(listing),
            ["staging"],
        )

    def test_environments_for_production_upload(self):
        from lasoo.models import ListingStatus
        from lasoo.services import variant_delete_service

        listing = SimpleNamespace(
            status=ListingStatus.UPLOADED_PRODUCTION,
        )
        self.assertEqual(
            variant_delete_service.environments_for_listing(listing),
            ["production"],
        )

    def test_environments_for_draft_skips_lasoo(self):
        from lasoo.models import ListingStatus
        from lasoo.services import variant_delete_service

        listing = SimpleNamespace(status=ListingStatus.READY)
        self.assertEqual(variant_delete_service.environments_for_listing(listing), [])

    def test_bulk_delete_payload_shape(self):
        payload = build_payload(
            "bulk_delete",
            data={
                "keys": [
                    {
                        "externalProductKey": "P1",
                        "externalVariantKey": "V1",
                    }
                ]
            },
            auth="KEY",
        )
        self.assertEqual(payload["query"], "Variants_BulkDelete")
        self.assertEqual(payload["auth"], "KEY")
        self.assertEqual(len(payload["data"]["keys"]), 1)


class ValidatorTests(SimpleTestCase):
    def _base(self, **over):
        data = {
            "product_key": "P1", "variant_key": "V1", "title": "T",
            "description": "D", "brand": "B", "sku": "S",
            "image_urls": "https://a.com/x.jpg", "inventory": "5",
            "original_price": "10", "sale_price": "8", "infinite_quantity": False,
        }
        data.update(over)
        return data

    def test_valid(self):
        self.assertEqual(validator.validate_listing(self._base()), [])

    def test_blank_description(self):
        errors = validator.validate_listing(self._base(description=""))
        self.assertIn("Description is required for variant V1.", errors)

    def test_blank_images(self):
        errors = validator.validate_listing(self._base(image_urls=""))
        self.assertIn("Image URLs are required for variant V1.", errors)

    def test_sale_gt_original(self):
        errors = validator.validate_listing(self._base(original_price="5", sale_price="9"))
        self.assertIn(
            "Sale Price must be lower than or equal to Original Price for variant V1.",
            errors,
        )

    def test_inventory_not_number(self):
        errors = validator.validate_listing(self._base(inventory="lots"))
        self.assertIn("Inventory must be a valid number for variant V1.", errors)

    def test_infinite_quantity_skips_inventory(self):
        errors = validator.validate_listing(
            self._base(inventory="", infinite_quantity=True)
        )
        self.assertEqual(errors, [])
