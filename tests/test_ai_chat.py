from fastapi.testclient import TestClient

from app.api.routes.ai_chat import get_ai_provider
from app.main import app

client = TestClient(app)
A = {"Authorization": "Bearer user-a-token"}
B = {"Authorization": "Bearer user-b-token"}


class FakeAiProvider:
    def moderated(self, text: str) -> bool:
        return "blocked-content" in text

    def respond(self, messages):
        return f"Safe answer to: {messages[-1]['content']}", 12, 8

    def analyze_food_photo(self, image_data_url):
        assert image_data_url.startswith("data:image/jpeg;base64,")
        return {"items": [{"name": "Rice", "portion_description": "about 1 cup",
                            "calories": 205, "protein": 4.3, "carbs": 45,
                            "fat": 0.4, "fiber": 0.6, "confidence": "medium"}],
                "notes": "Review the portion before logging."}, 20, 15

    def image_moderated(self, image_data_url):
        return False


def setup_module():
    app.dependency_overrides[get_ai_provider] = lambda: FakeAiProvider()


def teardown_module():
    app.dependency_overrides.pop(get_ai_provider, None)


def test_beta_plan_is_explicit_and_unlimited():
    response = client.get("/api/v1/ai/plan", headers=A)
    assert response.status_code == 200
    assert response.json()["plan"] == "beta"
    assert response.json()["unlimited"] is True
    assert response.json()["monthly_limit"] is None


def test_chat_persists_history_and_is_user_scoped():
    first = client.post("/api/v1/ai/chat", headers=A, json={"message": "How should I structure a beginner workout?"})
    assert first.status_code == 200
    body = first.json()
    cid = body["conversation"]["id"]
    assert body["message"]["role"] == "assistant"
    assert body["safety_intervened"] is False

    second = client.post("/api/v1/ai/chat", headers=A, json={"conversation_id": cid, "message": "Make it three days."})
    assert second.status_code == 200
    history = client.get(f"/api/v1/ai/conversations/{cid}", headers=A)
    assert [item["role"] for item in history.json()["messages"]] == ["user", "assistant", "user", "assistant"]
    assert client.get(f"/api/v1/ai/conversations/{cid}", headers=B).status_code == 404

    assert client.delete(f"/api/v1/ai/conversations/{cid}", headers=B).status_code == 404
    assert client.delete(f"/api/v1/ai/conversations/{cid}", headers=A).status_code == 204


def test_emergency_and_moderation_guardrails_do_not_call_generation():
    emergency = client.post("/api/v1/ai/chat", headers=B, json={"message": "My friend is unconscious after drinking"})
    assert emergency.status_code == 200
    assert emergency.json()["safety_intervened"] is True
    assert "emergency services" in emergency.json()["message"]["content"]

    moderated = client.post("/api/v1/ai/chat", headers=B, json={"message": "blocked-content"})
    assert moderated.status_code == 200
    assert moderated.json()["safety_intervened"] is True


def test_chat_requires_authentication_and_rejects_oversized_input():
    assert client.post("/api/v1/ai/chat", json={"message": "Hello"}).status_code == 401
    response = client.post("/api/v1/ai/chat", headers=A, json={"message": "x" * 2001})
    assert response.status_code == 422


def test_food_photo_is_authenticated_validated_and_metered():
    image = "data:image/jpeg;base64,/9j/2TAwMDAwMDAwMDAwMDAwMDAwMDAw"
    response = client.post("/api/v1/ai/food-photo", headers=A,
                           json={"image_data_url": image})
    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Rice"
    assert response.json()["items"][0]["confidence"] == "medium"
    assert response.json()["plan"]["used_this_month"] >= 1
    assert client.post("/api/v1/ai/food-photo", json={"image_data_url": image}).status_code == 401
    invalid = client.post("/api/v1/ai/food-photo", headers=A,
                          json={"image_data_url": "data:image/gif;base64,R0lGODlhMDAwMDAwMDAwMDAw"})
    assert invalid.status_code == 415
