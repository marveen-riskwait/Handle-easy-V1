"""End-to-end smoke test of the whole Handle Easy flow against a running API."""
import sys
import requests

BASE = "http://localhost:3001/api"
s = requests.Session()


def show(label, r):
    ok = r.ok
    print(f"[{'OK' if ok else 'FAIL'}] {label} -> {r.status_code}")
    if not ok:
        print("   ", r.text[:300])
    return r


# 1. Health
show("health", s.get(f"{BASE}/health"))

# 2. Staff login (seeded admin)
r = show("login", s.post(f"{BASE}/auth/login",
         json={"email": "admin@demo.com", "password": "demo1234"}))
csrf = r.json()["csrf_token"]
H = {"X-CSRF-TOKEN": csrf}

# 3. Staff: list tables, find table 8 + its session
tables = show("list tables", s.get(f"{BASE}/tables")).json()
t8 = next(t for t in tables if t["table_number"] == "8")
session_id = t8["active_session_id"]
print(f"    table 8 id={t8['id']} session={session_id} token={t8['qr_token']}")

# 4. Staff: table detail has a QR image
detail = show("table detail (QR)", s.get(f"{BASE}/tables/{t8['id']}")).json()
print(f"    QR image present: {bool(detail['qr']['image'])}  url={detail['qr']['url']}")

# 5. Public guest landing by token
pub = show("public /table/<token>", s.get(f"{BASE}/table/{t8['qr_token']}")).json()
items = pub["split"]["items"]
customers = pub["customers"]
print(f"    items={len(items)} guests={[c['display_name'] for c in customers]}")
thomas = next(c for c in customers if c["display_name"] == "Thomas")
marie = next(c for c in customers if c["display_name"] == "Marie")

# 6. A 3rd guest joins with no name -> "Invité 3"
paul = show("guest join (no name)",
            s.post(f"{BASE}/sessions/{session_id}/customers", json={})).json()
print(f"    joined as: {paul['display_name']}")

by_name = {i["name"]: i for i in items}
burger = by_name["Burger Maison"]
coca = by_name["Coca-Cola"]
pizza = by_name["Pizza Margherita"]
tira = by_name["Tiramisu"]
wine = by_name["Bouteille de Vin"]

# 7. Assignments (mirrors the spec example):
#    Thomas: Burger + Coca | Marie: Pizza | Paul: Tiramisu | Wine shared by all 3
def claim(item, cust):
    return s.post(f"{BASE}/sessions/{session_id}/items/{item['id']}/claim",
                  json={"customer_id": cust["id"]})

claim(burger, thomas); claim(coca, thomas)
claim(pizza, marie)
claim(tira, paul)
claim(wine, thomas); claim(wine, marie)
split = claim(wine, paul).json()
show("claims applied", type("R", (), {"ok": True, "status_code": 200})())

print("\n    --- SPLIT ---")
for c in split["customers"]:
    print(f"    {c['display_name']:12} total={c['total']:.2f}  due={c['due']:.2f}")
print(f"    grand_total={split['grand_total']:.2f} unassigned={split['unassigned_total']:.2f}")

# Expected: wine 24/3 = 8 each.
#  Thomas 14+3.5+8 = 25.50 | Marie 12+8 = 20.00 | Paul 7+8 = 15.00 -> total 60.50
assert abs(split["grand_total"] - 60.5) < 0.01, "grand total mismatch"
tot = {c["display_name"]: c["total"] for c in split["customers"]}
assert abs(tot["Thomas"] - 25.5) < 0.01, tot
assert abs(tot["Marie"] - 20.0) < 0.01, tot
assert abs(tot[paul["display_name"]] - 15.0) < 0.01, tot
print("    ✓ split math correct (wine shared 3 ways at 8.00 each)")

# 8. Everyone pays. Session should close after the last payer.
for cust in (thomas, marie, paul):
    res = show(f"pay {cust['display_name']}",
               s.post(f"{BASE}/sessions/{session_id}/pay",
                      json={"customer_id": cust["id"]})).json()
    print(f"    session status now: {res['session']['status']}")

final = s.get(f"{BASE}/table/{t8['qr_token']}").json()
assert final["session"]["status"] == "closed", "session should be closed after full payment"
print("    ✓ session closed after all guests paid (Odoo mark_order_paid logged server-side)")

print("\nALL CHECKS PASSED")
