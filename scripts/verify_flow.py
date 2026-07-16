"""End-to-end smoke test of the RDV Cycles API against a running backend.

Covers what Lot 0 actually ships: health check and the full cookie-based auth
flow (register → me → logout, then login with the seeded admin → refresh
rotation). Run the backend first (`pipenv run start`), optionally `flask seed`.

    python scripts/verify_flow.py
"""
import sys
import uuid

import requests

BASE = "http://localhost:3001/api"
s = requests.Session()

failures = 0


def show(label, r, expect=200):
    global failures
    ok = r.status_code == expect
    if not ok:
        failures += 1
    print(f"[{'OK' if ok else 'FAIL'}] {label} -> {r.status_code} (expected {expect})")
    if not ok:
        print("   ", r.text[:300])
    return r


def csrf_from(resp):
    """Access CSRF token echoed back in the login/register JSON body."""
    return resp.json().get("csrf_token")


# 1. Health
show("health", s.get(f"{BASE}/health"))

# 1b. Public catalogue (Lot 1) — needs `flask seed` to be non-empty.
bikes = show("catalogue vélos", s.get(f"{BASE}/bikes"))
if bikes.ok and bikes.json()["bikes"]:
    first = bikes.json()["bikes"][0]
    print(f"    {len(bikes.json()['bikes'])} modèles, "
          f"1er = {first['name']} dès {first['from_price_cents']} c")
show("stations", s.get(f"{BASE}/stations"))
show("options", s.get(f"{BASE}/options"))
show("tarifs", s.get(f"{BASE}/rates"))

# 2. Register a throwaway customer (unique email each run) and get a session.
email = f"smoke+{uuid.uuid4().hex[:8]}@demo.com"
reg = show("register", s.post(f"{BASE}/auth/register", json={
    "email": email, "password": "password1",
    "first_name": "Smoke", "last_name": "Test"}), expect=201)
csrf = csrf_from(reg)
H = {"X-CSRF-TOKEN": csrf} if csrf else {}

# 3. /me reflects the logged-in user (cookie sent automatically).
me = show("me", s.get(f"{BASE}/auth/me"))
if me.ok:
    assert me.json()["user"]["email"] == email, me.text

# 4. Weak password is rejected (422).
show("register weak password", s.post(f"{BASE}/auth/register", json={
    "email": f"weak+{uuid.uuid4().hex[:6]}@demo.com", "password": "short"}),
    expect=422)

# 5. Duplicate email is rejected (409).
show("register duplicate", s.post(f"{BASE}/auth/register", json={
    "email": email, "password": "password1"}), expect=409)

# 6. Logout clears the session; /me then 401s.
show("logout", s.post(f"{BASE}/auth/logout", headers=H))
show("me after logout (401)", s.get(f"{BASE}/auth/me"), expect=401)

# 7. Login with the seeded admin, if present.
admin = s.post(f"{BASE}/auth/login",
               json={"email": "admin@rdv-cycles.fr", "password": "demo1234"})
if admin.status_code == 200:
    show("admin login", admin)
    assert admin.json()["user"]["role"] == "admin", admin.text

    # Refresh rotation: the refresh endpoint wants the *refresh* CSRF token,
    # which flask-jwt-extended puts in a readable cookie.
    refresh_csrf = s.cookies.get("csrf_refresh_token")
    show("refresh token", s.post(f"{BASE}/auth/refresh",
         headers={"X-CSRF-TOKEN": refresh_csrf} if refresh_csrf else {}))
else:
    print("[SKIP] admin login — seed not present (run `flask seed`).")

print()
if failures:
    print(f"{failures} CHECK(S) FAILED")
    sys.exit(1)
print("ALL CHECKS PASSED")
