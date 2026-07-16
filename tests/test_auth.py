"""Cookie-based auth flow: register, me, guards, logout."""


def test_health(client):
    assert client.get("/api/health").get_json()["service"] == "rdv-cycles"


def test_register_then_me(auth_client):
    client, _headers, email = auth_client
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == email
    assert me.get_json()["user"]["role"] == "customer"


def test_register_rejects_short_password(client):
    r = client.post("/api/auth/register",
                    json={"email": "short@demo.com", "password": "abc"})
    assert r.status_code == 422


def test_register_rejects_duplicate(auth_client):
    client, _headers, email = auth_client
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "password1"})
    assert r.status_code == 409


def test_login_wrong_password_401(seeded, client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@rdv-cycles.fr", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    fresh = client.application.test_client()   # no cookies
    assert fresh.get("/api/auth/me").status_code == 401


def test_logout_clears_session(auth_client):
    client, headers, _email = auth_client
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
