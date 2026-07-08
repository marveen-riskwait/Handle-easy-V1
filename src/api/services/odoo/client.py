"""OdooClient — the single gateway to Odoo.

The rest of the app only ever talks to Odoo through this class, so whether
we return mock fixtures or hit a real Odoo over XML-RPC is invisible to
callers. Toggle with the ODOO_MOCK env var (default: mock).

Real mode is stubbed (structure in place) and not exercised in the MVP —
it shows exactly where the XML-RPC calls go.
"""
import os

from .fixtures import MOCK_PRODUCTS, MOCK_OPEN_ORDERS


def _mock_enabled():
    return os.getenv("ODOO_MOCK", "1") == "1"


class OdooClient:
    def __init__(self, company=None):
        self.company = company
        self.mock = _mock_enabled()
        self._uid = None
        self._models = None

    # ── Auth ────────────────────────────────────────────
    def authenticate(self):
        if self.mock:
            self._uid = 1
            return self._uid
        # Real Odoo (not exercised in MVP):
        #   import xmlrpc.client
        #   common = xmlrpc.client.ServerProxy(f"{self.company.odoo_url}/xmlrpc/2/common")
        #   self._uid = common.authenticate(
        #       self.company.odoo_database, self.company.odoo_username,
        #       self.company.odoo_api_key, {})
        #   self._models = xmlrpc.client.ServerProxy(
        #       f"{self.company.odoo_url}/xmlrpc/2/object")
        #   return self._uid
        raise NotImplementedError("Live Odoo XML-RPC not wired yet — set ODOO_MOCK=1.")

    # ── Reads ───────────────────────────────────────────
    def get_products(self):
        if self.mock:
            return list(MOCK_PRODUCTS)
        raise NotImplementedError("Live Odoo XML-RPC not wired yet.")

    def get_open_orders(self):
        if self.mock:
            return [dict(o) for o in MOCK_OPEN_ORDERS.values()]
        raise NotImplementedError("Live Odoo XML-RPC not wired yet.")

    def get_order_lines(self, order_id):
        if self.mock:
            order = MOCK_OPEN_ORDERS.get(int(order_id))
            return list(order["lines"]) if order else []
        raise NotImplementedError("Live Odoo XML-RPC not wired yet.")

    def get_tables(self):
        if self.mock:
            return [{"table_number": o["table_number"], "odoo_order_id": o["odoo_order_id"]}
                    for o in MOCK_OPEN_ORDERS.values()]
        raise NotImplementedError("Live Odoo XML-RPC not wired yet.")

    # ── Writes ──────────────────────────────────────────
    def mark_order_paid(self, order_id):
        """Tell Odoo the POS order is fully settled."""
        if self.mock:
            # In mock mode we just log the intent; nothing to persist.
            print(f"[OdooClient:mock] mark_order_paid(order_id={order_id})", flush=True)
            return True
        raise NotImplementedError("Live Odoo XML-RPC not wired yet.")
