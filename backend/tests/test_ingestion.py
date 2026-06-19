import json

from app.telemetry.synth import SIM_CIRCUIT, generate_lap, lap_time_ms

REG = {"email": "ingest@apexai.dev", "password": "supersecret1"}


async def _auth_header(client) -> dict[str, str]:
    reg = await client.post("/auth/register", json=REG)
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


def _payload(seed: int = 0, client_lap_uuid: str = "lap-0001") -> tuple[dict, bytes]:
    trace = generate_lap(SIM_CIRCUIT.name, seed=seed)
    meta = {
        "client_lap_uuid": client_lap_uuid,
        "client_session_uuid": "sess-0001",
        "game": "f1_25",
        "track": SIM_CIRCUIT.name,
        "car_or_team": "Demo",
        "session_type": "practice",
        "lap_time_ms": lap_time_ms(trace),
        "valid": True,
        "recorded_at": "2026-06-17T10:00:00Z",
        "sample_count": trace.points,
    }
    return meta, trace.to_gzip()


def _multipart(meta: dict, blob: bytes) -> dict:
    return {
        "data": {"meta": json.dumps(meta)},
        "files": {"trace": ("lap.json.gz", blob, "application/gzip")},
    }


async def test_upload_lists_and_fetches_trace(client):
    headers = await _auth_header(client)
    meta, blob = _payload()

    created = await client.post("/laps", headers=headers, **_multipart(meta, blob))
    assert created.status_code == 201, created.text
    lap = created.json()
    assert lap["sample_count"] == meta["sample_count"]
    assert lap["has_metrics"] is True  # layer-1 metrics are computed on ingest

    sessions = await client.get("/sessions", headers=headers)
    assert sessions.status_code == 200
    body = sessions.json()
    assert len(body) == 1
    assert body[0]["lap_count"] == 1
    assert body[0]["best_lap_time_ms"] == meta["lap_time_ms"]

    detail = await client.get(f"/laps/{lap['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["track"] == SIM_CIRCUIT.name
    assert detail.json()["trace"]["points"] == meta["sample_count"]

    trace = await client.get(f"/laps/{lap['id']}/trace", headers=headers)
    assert trace.status_code == 200
    payload = trace.json()
    assert payload["hz"] == 60
    assert "speed_kmh" in payload["channels"]
    assert len(payload["channels"]["t_ms"]) == meta["sample_count"]


async def test_upload_is_idempotent(client):
    headers = await _auth_header(client)
    meta, blob = _payload(client_lap_uuid="dup-00001")

    first = await client.post("/laps", headers=headers, **_multipart(meta, blob))
    second = await client.post("/laps", headers=headers, **_multipart(meta, blob))
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    sessions = await client.get("/sessions", headers=headers)
    assert sessions.json()[0]["lap_count"] == 1


async def test_unsupported_game_rejected(client):
    headers = await _auth_header(client)
    meta, blob = _payload()
    meta["game"] = "f1_23"  # out of MVP scope
    resp = await client.post("/laps", headers=headers, **_multipart(meta, blob))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_meta"


async def test_corrupt_trace_rejected(client):
    headers = await _auth_header(client)
    meta, _ = _payload(client_lap_uuid="bad-00001")
    resp = await client.post(
        "/laps",
        headers=headers,
        data={"meta": json.dumps(meta)},
        files={"trace": ("lap.json.gz", b"not-gzip", "application/gzip")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_trace"


async def test_upload_requires_auth(client):
    meta, blob = _payload()
    resp = await client.post("/laps", **_multipart(meta, blob))
    assert resp.status_code == 401


async def test_compare_endpoint_and_reference_lap(client):
    headers = await _auth_header(client)
    fast_meta, fast_blob = _payload(seed=0, client_lap_uuid="cmp-fast-01")
    slow_meta, slow_blob = _payload(seed=2, client_lap_uuid="cmp-slow-01")
    fast = (await client.post("/laps", headers=headers, **_multipart(fast_meta, fast_blob))).json()
    slow = (await client.post("/laps", headers=headers, **_multipart(slow_meta, slow_blob))).json()

    # the slower lap's reference (overlay) is the faster lap
    detail = await client.get(f"/laps/{slow['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["reference_lap_id"] == fast["id"]

    compared = await client.get(f"/laps/compare?a={slow['id']}&b={fast['id']}", headers=headers)
    assert compared.status_code == 200
    body = compared.json()
    assert body["a"]["id"] == slow["id"]
    assert body["b"]["id"] == fast["id"]
    assert body["total_delta_s"] > 0
    assert len(body["distance_m"]) == len(body["delta_s"]) > 0


async def test_list_all_laps(client):
    headers = await _auth_header(client)
    m1, b1 = _payload(seed=0, client_lap_uuid="list-lap-0001")
    m2, b2 = _payload(seed=1, client_lap_uuid="list-lap-0002")
    await client.post("/laps", headers=headers, **_multipart(m1, b1))
    await client.post("/laps", headers=headers, **_multipart(m2, b2))

    resp = await client.get("/laps", headers=headers)
    assert resp.status_code == 200
    laps = resp.json()
    assert len(laps) == 2
    assert all(lap["track"] == SIM_CIRCUIT.name for lap in laps)
    assert all(lap["game"] == "f1_25" for lap in laps)


async def test_cannot_read_another_users_lap(client):
    owner = await _auth_header(client)
    meta, blob = _payload(client_lap_uuid="owned-0001")
    lap = (await client.post("/laps", headers=owner, **_multipart(meta, blob))).json()

    other = await client.post(
        "/auth/register", json={"email": "intruder@apexai.dev", "password": "supersecret1"}
    )
    intruder = {"Authorization": f"Bearer {other.json()['access_token']}"}
    resp = await client.get(f"/laps/{lap['id']}", headers=intruder)
    assert resp.status_code == 404
