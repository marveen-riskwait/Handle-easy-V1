"""Mock Odoo data used when ODOO_MOCK=1 (i.e. no live Odoo).

Shapes loosely mirror what Odoo's XML-RPC would return for pos.order,
pos.order.line and product.product, so the real client can drop in later.
"""

MOCK_PRODUCTS = [
    {"odoo_product_id": 101, "name": "Pizza Margherita", "price": 12.0, "category": "Plats"},
    {"odoo_product_id": 102, "name": "Burger Maison", "price": 14.0, "category": "Plats"},
    {"odoo_product_id": 103, "name": "Salade César", "price": 10.5, "category": "Entrées"},
    {"odoo_product_id": 104, "name": "Coca-Cola", "price": 3.5, "category": "Boissons"},
    {"odoo_product_id": 105, "name": "Verre de Vin Rouge", "price": 6.0, "category": "Boissons"},
    {"odoo_product_id": 106, "name": "Bouteille de Vin", "price": 24.0, "category": "Boissons"},
    {"odoo_product_id": 107, "name": "Tiramisu", "price": 7.0, "category": "Desserts"},
    {"odoo_product_id": 108, "name": "Café", "price": 2.5, "category": "Boissons"},
]

# One open order, keyed by odoo_order_id. Lines reference products above.
MOCK_OPEN_ORDERS = {
    9001: {
        "odoo_order_id": 9001,
        "table_number": "8",
        "lines": [
            {"odoo_line_id": 1, "odoo_product_id": 102, "name": "Burger Maison", "quantity": 1, "unit_price": 14.0},
            {"odoo_line_id": 2, "odoo_product_id": 104, "name": "Coca-Cola", "quantity": 1, "unit_price": 3.5},
            {"odoo_line_id": 3, "odoo_product_id": 101, "name": "Pizza Margherita", "quantity": 1, "unit_price": 12.0},
            {"odoo_line_id": 4, "odoo_product_id": 107, "name": "Tiramisu", "quantity": 1, "unit_price": 7.0},
            {"odoo_line_id": 5, "odoo_product_id": 106, "name": "Bouteille de Vin", "quantity": 1, "unit_price": 24.0},
        ],
    }
}
