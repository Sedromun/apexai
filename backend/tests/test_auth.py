REG = {"email": "racer@apexai.dev", "password": "supersecret1"}


async def test_register_login_me_refresh_flow(client):
    reg = await client.post("/auth/register", json=REG)
    assert reg.status_code == 201, reg.text
    tokens = reg.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["expires_in"] > 0

    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = await client.get("/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["email"] == REG["email"]
    assert me.json()["plan"] == "free"

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    login = await client.post("/auth/login", json=REG)
    assert login.status_code == 200
    assert login.json()["access_token"]


async def test_duplicate_register_conflicts(client):
    await client.post("/auth/register", json=REG)
    again = await client.post("/auth/register", json=REG)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "email_taken"


async def test_login_with_wrong_password_rejected(client):
    await client.post("/auth/register", json=REG)
    bad = await client.post("/auth/login", json={"email": REG["email"], "password": "nope12345"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_credentials"


async def test_me_requires_token(client):
    assert (await client.get("/me")).status_code == 401


async def test_refresh_rejects_access_token(client):
    tokens = (await client.post("/auth/register", json=REG)).json()
    # an access token must not be accepted where a refresh token is required
    bad = await client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


async def test_short_password_rejected(client):
    weak = await client.post("/auth/register", json={"email": "weak@apexai.dev", "password": "short"})
    assert weak.status_code == 422
