from __future__ import annotations

import re

import httpx
from fastapi import HTTPException, status

BARCODE_PATTERN = re.compile(r"^[0-9]{8,14}$")
OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org"
OPEN_FOOD_FACTS_USER_AGENT = "Pace/0.23 (food barcode lookup)"
FIELDS = ",".join(("code", "product_name", "generic_name", "brands", "serving_size",
                   "serving_quantity", "nutrition_data_per", "nutriments"))


class OpenFoodFactsProvider:
    def lookup(self, barcode: str) -> dict:
        url = f"{OPEN_FOOD_FACTS_URL}/api/v2/product/{barcode}.json"
        try:
            response = httpx.get(url, params={"fields": FIELDS},
                                 headers={"User-Agent": OPEN_FOOD_FACTS_USER_AGENT,
                                          "Accept": "application/json"}, timeout=12.0)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                "Barcode lookup is temporarily unavailable") from exc


def _number(values: dict, key: str) -> float:
    value = values.get(key)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, number), 2)


def lookup_product(barcode: str, provider: OpenFoodFactsProvider) -> dict:
    clean = barcode.strip()
    if not BARCODE_PATTERN.fullmatch(clean):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Enter a valid 8–14 digit barcode")
    payload = provider.lookup(clean)
    if payload.get("status") != 1 or not isinstance(payload.get("product"), dict):
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Product not found. You can still log it manually.")
    product = payload["product"]
    nutriments = product.get("nutriments") or {}
    name = (product.get("product_name") or product.get("generic_name") or "").strip()
    if not name:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "This barcode has no usable product name.")

    serving_quantity = _number(product, "serving_quantity")
    per_serving = serving_quantity > 0 and any(
        key.endswith("_serving") for key in nutriments
    )
    suffix = "serving" if per_serving else "100g"
    basis_amount = serving_quantity if per_serving else 100.0
    serving_size = str(product.get("serving_size") or "").strip() or None

    return {
        "barcode": clean, "name": name[:160],
        "brand": (str(product.get("brands") or "").strip() or None),
        "basis_amount": basis_amount, "basis_unit": "g",
        "serving_label": serving_size,
        "nutrition": {
            "calories": _number(nutriments, f"energy-kcal_{suffix}"),
            "protein": _number(nutriments, f"proteins_{suffix}"),
            "carbs": _number(nutriments, f"carbohydrates_{suffix}"),
            "fat": _number(nutriments, f"fat_{suffix}"),
            "fiber": _number(nutriments, f"fiber_{suffix}") if f"fiber_{suffix}" in nutriments else None,
        },
        "source_url": f"{OPEN_FOOD_FACTS_URL}/product/{clean}",
    }
