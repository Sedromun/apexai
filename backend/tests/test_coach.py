import json

from app.telemetry.synth import SIM_CIRCUIT, generate_lap, lap_time_ms

REG = {"email": "coach@apexai.dev", "password": "supersecret1"}


async def _auth(client) -> dict[str, str]:
    reg = await client.post("/auth/register", json=REG)
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


def _multipart(seed: int, client_lap_uuid: str) -> dict:
    trace = generate_lap(SIM_CIRCUIT.name, seed=seed)
    meta = {
        "client_lap_uuid": client_lap_uuid,
        "client_session_uuid": "coach-session-01",
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


async def _upload(client, headers, seed: int, client_lap_uuid: str) -> dict:
    resp = await client.post("/laps", headers=headers, **_multipart(seed, client_lap_uuid))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_analyze_produces_grounded_report(client):
    headers = await _auth(client)
    await _upload(client, headers, seed=0, client_lap_uuid="coach-fast-01")
    slow = await _upload(client, headers, seed=3, client_lap_uuid="coach-slow-01")

    resp = await client.post("/coach/analyze", headers=headers, json={"lap_id": slow["id"]})
    assert resp.status_code == 201, resp.text
    report = resp.json()
    assert report["lap_id"] == slow["id"]
    assert report["body"]
    assert report["summary"]["summary_text"]

    detail = (await client.get(f"/laps/{slow['id']}", headers=headers)).json()
    corner_numbers = {c["number"] for c in detail["metrics"]["corners"]}
    for mistake in report["summary"]["top_mistakes"]:
        if mistake.get("corner") is not None:
            assert mistake["corner"] in corner_numbers  # advice grounded in real corners


async def test_analyze_is_cached(client):
    headers = await _auth(client)
    lap = await _upload(client, headers, seed=0, client_lap_uuid="coach-cache-01")
    first = await client.post("/coach/analyze", headers=headers, json={"lap_id": lap["id"]})
    second = await client.post("/coach/analyze", headers=headers, json={"lap_id": lap["id"]})
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    by_lap = await client.get(f"/laps/{lap['id']}/coach", headers=headers)
    assert by_lap.status_code == 200
    assert by_lap.json()["id"] == first.json()["id"]


async def test_free_trial_limit_enforced(client):
    headers = await _auth(client)
    lap1 = await _upload(client, headers, seed=0, client_lap_uuid="trial-lap-01")
    lap2 = await _upload(client, headers, seed=3, client_lap_uuid="trial-lap-02")

    ok = await client.post("/coach/analyze", headers=headers, json={"lap_id": lap1["id"]})
    assert ok.status_code == 201

    blocked = await client.post("/coach/analyze", headers=headers, json={"lap_id": lap2["id"]})
    assert blocked.status_code == 402
    assert blocked.json()["error"]["code"] == "upgrade_required"

    # re-fetching the already-analyzed lap stays free (cached, no new spend)
    again = await client.post("/coach/analyze", headers=headers, json={"lap_id": lap1["id"]})
    assert again.status_code == 201
