import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.telemetry.synth import SIM_CIRCUIT, generate_lap, lap_time_ms


async def _auth(client, email: str = "bill@apexai.dev") -> dict[str, str]:
    reg = await client.post("/auth/register", json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


def _upload_payload(seed: int, client_lap_uuid: str) -> dict:
    trace = generate_lap(SIM_CIRCUIT.name, seed=seed)
    meta = {
        "client_lap_uuid": client_lap_uuid,
        "client_session_uuid": "billing-session",
        "game": "f1_25",
        "track": SIM_CIRCUIT.name,
        "car_or_team": "Demo",
        "lap_time_ms": lap_time_ms(trace),
        "valid": True,
        "recorded_at": "2026-06-17T10:00:00Z",
        "sample_count": trace.points,
    }
    return {
        "data": {"meta": json.dumps(meta)},
        "files": {"trace": ("lap.json.gz", trace.to_gzip(), "application/gzip")},
    }


def _ref_from_checkout(checkout_url: str) -> str:
    return parse_qs(urlparse(checkout_url).query)["ref"][0]


def _signed(payload: dict) -> tuple[dict[str, str], bytes]:
    raw = json.dumps(payload).encode()
    sig = hmac.new(settings.billing_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    return {"x-stub-signature": sig}, raw


async def test_list_plans(client):
    resp = await client.get("/billing/plans")
    assert resp.status_code == 200
    assert {"free", "pro_monthly", "pro_yearly"} <= {p["id"] for p in resp.json()}


async def test_subscribe_creates_pending_checkout(client):
    headers = await _auth(client)
    resp = await client.post("/billing/subscribe", headers=headers, json={"plan": "pro_monthly"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["checkout_url"].startswith("http")
    assert resp.json()["provider"] == "stub"
    me = await client.get("/me", headers=headers)
    assert me.json()["plan"] == "free"  # not upgraded until the webhook confirms


async def test_webhook_activates_then_unlimited(client, monkeypatch):
    monkeypatch.setattr(settings, "free_monthly_lap_limit", 2)
    headers = await _auth(client, email="upgrade@apexai.dev")
    sub = (
        await client.post("/billing/subscribe", headers=headers, json={"plan": "pro_yearly"})
    ).json()
    ref = _ref_from_checkout(sub["checkout_url"])

    sig_headers, raw = _signed({"type": "subscription.activated", "provider_ref": ref})
    webhook = await client.post("/billing/webhook", headers=sig_headers, content=raw)
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "activated"

    me = await client.get("/me", headers=headers)
    assert me.json()["plan"] == "pro"
    assert me.json()["subscription"]["status"] == "active"

    # Pro ignores the (tightened) free lap cap.
    for i in range(3):
        resp = await client.post(
            "/laps", headers=headers, **_upload_payload(i, f"pro-lap-{i:03d}")
        )
        assert resp.status_code == 201, resp.text


async def test_webhook_rejects_bad_signature(client):
    headers = await _auth(client, email="badsig@apexai.dev")
    sub = (
        await client.post("/billing/subscribe", headers=headers, json={"plan": "pro_monthly"})
    ).json()
    ref = _ref_from_checkout(sub["checkout_url"])
    raw = json.dumps({"type": "subscription.activated", "provider_ref": ref}).encode()
    resp = await client.post(
        "/billing/webhook", headers={"x-stub-signature": "deadbeef"}, content=raw
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_signature"
    # signature failed => not upgraded
    me = await client.get("/me", headers=headers)
    assert me.json()["plan"] == "free"


async def test_free_monthly_lap_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "free_monthly_lap_limit", 2)
    headers = await _auth(client, email="capped@apexai.dev")

    first = await client.post("/laps", headers=headers, **_upload_payload(0, "cap-lap-001"))
    second = await client.post("/laps", headers=headers, **_upload_payload(1, "cap-lap-002"))
    third = await client.post("/laps", headers=headers, **_upload_payload(2, "cap-lap-003"))

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 402
    assert third.json()["error"]["code"] == "lap_limit_reached"

    me = await client.get("/me", headers=headers)
    assert me.json()["usage"]["laps_this_month"] == 2
