"""OdooClient — the single gateway to Odoo.

The rest of the app only ever talks to Odoo through this class, so whether
we return mock fixtures or hit a real Odoo over XML-RPC is invisible to
callers. Toggle with the ODOO_MOCK env var (default: mock).

Real mode uses Odoo's standard external API (xmlrpc/2/common + object).
It is not exercised in the mocked MVP, but it is fully wired: point a
company at a live Odoo (odoo_url / odoo_database / odoo_username /
odoo_api_key) and set ODOO_MOCK=0.
"""
import os
import xmlrpc.client

from .fixtures import MOCK_PRODUCTS, MOCK_OPEN_ORDERS


def _mock_enabled():
    return os.getenv("ODOO_MOCK", "1") == "1"


# POS order states we treat as "still open" (not yet fully settled/closed).
OPEN_ORDER_STATES = ("draft", "paid", "done", "invoiced")


class OdooClient:
    def __init__(self, company=None):
        self.company = company
        self.mock = _mock_enabled()
        self._uid = None
        self._models = None

    # ── Internals ───────────────────────────────────────
    def _require_company(self):
        c = self.company
        if not c or not (c.odoo_url and c.odoo_database and c.odoo_username and c.odoo_api_key):
            raise RuntimeError(
                "Odoo credentials missing on company "
                "(odoo_url / odoo_database / odoo_username / odoo_api_key).")
        return c

    def _kw(self, model, method, args, kwargs=None):
        """Thin wrapper around Odoo's execute_kw."""
        c = self.company
        return self._models.execute_kw(
            c.odoo_database, self._uid, c.odoo_api_key,
            model, method, args, kwargs or {})

    # ── Auth ────────────────────────────────────────────
    def authenticate(self):
        if self.mock:
            self._uid = 1
            return self._uid
        c = self._require_company()
        base = c.odoo_url.rstrip("/")
        common = xmlrpc.client.ServerProxy(f"{base}/xmlrpc/2/common")
        self._uid = common.authenticate(
            c.odoo_database, c.odoo_username, c.odoo_api_key, {})
        if not self._uid:
            raise RuntimeError("Odoo authentication failed (check credentials).")
        self._models = xmlrpc.client.ServerProxy(f"{base}/xmlrpc/2/object")
        return self._uid

    # ── Reads ───────────────────────────────────────────
    def get_products(self):
        if self.mock:
            return list(MOCK_PRODUCTS)
        rows = self._kw(
            "product.product", "search_read",
            [[["sale_ok", "=", True]]],
            {"fields": ["id", "name", "list_price", "categ_id"]})
        return [{
            "odoo_product_id": r["id"],
            "name": r["name"],
            "price": r.get("list_price", 0.0),
            # categ_id comes back as [id, "Category Name"] or False
            "category": (r["categ_id"][1] if r.get("categ_id") else None),
        } for r in rows]

    def get_open_orders(self):
        if self.mock:
            return [dict(o) for o in MOCK_OPEN_ORDERS.values()]
        orders = self._kw(
            "pos.order", "search_read",
            [[["state", "in", list(OPEN_ORDER_STATES)]]],
            {"fields": ["id", "name", "table_id", "amount_total"]})
        return [{
            "odoo_order_id": o["id"],
            "table_number": (o["table_id"][1] if o.get("table_id") else None),
            "amount_total": o.get("amount_total"),
            "lines": self.get_order_lines(o["id"]),
        } for o in orders]

    def get_order_lines(self, order_id):
        if self.mock:
            order = MOCK_OPEN_ORDERS.get(int(order_id))
            return list(order["lines"]) if order else []
        rows = self._kw(
            "pos.order.line", "search_read",
            [[["order_id", "=", int(order_id)]]],
            {"fields": ["id", "product_id", "full_product_name", "qty", "price_unit"]})
        return [{
            "odoo_line_id": r["id"],
            "odoo_product_id": (r["product_id"][0] if r.get("product_id") else None),
            "name": r.get("full_product_name")
                    or (r["product_id"][1] if r.get("product_id") else None),
            "quantity": r.get("qty", 1),
            "unit_price": r.get("price_unit", 0.0),
        } for r in rows]

    def get_tables(self):
        if self.mock:
            return [{"table_number": o["table_number"], "odoo_order_id": o["odoo_order_id"]}
                    for o in MOCK_OPEN_ORDERS.values()]
        # restaurant.table ships with the pos_restaurant module.
        rows = self._kw(
            "restaurant.table", "search_read",
            [[]], {"fields": ["id", "name"]})
        return [{"odoo_table_id": r["id"], "table_number": r.get("name")} for r in rows]

    # ── Writes ──────────────────────────────────────────
    def mark_order_paid(self, order_id):
        """Tell Odoo the POS order is fully settled.

        Registering a real POS payment differs across Odoo versions, so we
        do the safe, version-tolerant thing: move the order to the 'paid'
        state. Swap this for a proper payment registration once the target
        Odoo version is known.
        """
        if self.mock:
            print(f"[OdooClient:mock] mark_order_paid(order_id={order_id})", flush=True)
            return True
        self._kw("pos.order", "write", [[int(order_id)], {"state": "paid"}])
        return True
