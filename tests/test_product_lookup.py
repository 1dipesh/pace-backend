from fastapi.testclient import TestClient

from app.api.routes.product_lookup import get_product_provider
from app.main import app

client = TestClient(app)
A = {"Authorization": "Bearer user-a-token"}


class FakeProductProvider:
    def lookup(self, barcode):
        if barcode == "12345678":
            return {"status": 0}
        return {"status": 1, "product": {
            "product_name": "Greek yogurt", "brands": "Pace Test",
            "serving_size": "1 pot (150 g)", "serving_quantity": 150,
            "nutriments": {"energy-kcal_serving": 130, "proteins_serving": 15,
                            "carbohydrates_serving": 8, "fat_serving": 4,
                            "fiber_serving": 0},
        }}


def setup_module():
    app.dependency_overrides[get_product_provider] = lambda: FakeProductProvider()


def teardown_module():
    app.dependency_overrides.pop(get_product_provider, None)


def test_barcode_lookup_requires_auth_and_returns_editable_nutrition():
    assert client.get("/api/v1/nutrition/barcode/8851234567890").status_code == 401
    response = client.get("/api/v1/nutrition/barcode/8851234567890", headers=A)
    assert response.status_code == 200
    assert response.json()["name"] == "Greek yogurt"
    assert response.json()["basis_amount"] == 150
    assert response.json()["nutrition"]["protein"] == 15


def test_barcode_lookup_validates_and_handles_unknown_products():
    assert client.get("/api/v1/nutrition/barcode/not-a-code", headers=A).status_code == 422
    assert client.get("/api/v1/nutrition/barcode/12345678", headers=A).status_code == 404
