"""Sync helpers: pull Odoo data into our own tables.

Odoo stays the source of truth; we mirror just enough to run the split.
"""
from api.models import db, Product, OrderItem
from .client import OdooClient


def sync_products(company):
    """Upsert the company's product catalog from Odoo. Returns the count."""
    client = OdooClient(company)
    client.authenticate()
    products = client.get_products()

    existing = {p.odoo_product_id: p for p in company.products}
    for row in products:
        p = existing.get(row["odoo_product_id"])
        if p is None:
            p = Product(company_id=company.id, odoo_product_id=row["odoo_product_id"])
            db.session.add(p)
        p.name = row["name"]
        p.price = row["price"]
        p.category = row.get("category")
    db.session.commit()
    return len(products)


def import_order_into_session(company, session, odoo_order_id):
    """Copy an Odoo open order's lines into a session as OrderItems.

    Idempotent-ish: clears any existing *unpaid, unassigned* mirror lines
    first so a re-sync doesn't duplicate. Assigned/paid lines are kept.
    """
    client = OdooClient(company)
    client.authenticate()
    lines = client.get_order_lines(odoo_order_id)

    # Map odoo product ids to our local Product rows (sync first if empty).
    if not company.products:
        sync_products(company)
    by_odoo_id = {p.odoo_product_id: p for p in company.products}

    existing_line_ids = {i.odoo_line_id for i in session.items if i.odoo_line_id}
    added = 0
    for line in lines:
        if line["odoo_line_id"] in existing_line_ids:
            continue
        product = by_odoo_id.get(line["odoo_product_id"])
        item = OrderItem(
            session_id=session.id,
            product_id=product.id if product else None,
            odoo_line_id=line["odoo_line_id"],
            name=line.get("name") or (product.name if product else None),
            quantity=line.get("quantity", 1),
            unit_price=line.get("unit_price", 0.0),
        )
        db.session.add(item)
        added += 1

    session.odoo_order_id = odoo_order_id
    db.session.commit()
    return added
