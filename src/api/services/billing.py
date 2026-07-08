"""Bill-splitting core.

This is where the magic happens (see the workflow in the project spec):
every order line is split equally among the guests who claimed it, so a
shared bottle of wine costs each of its three drinkers a third.
"""


def compute_split(session):
    """Return the full split state for a session.

    Shape::

        {
          "items": [ {id, name, line_total, assignee_ids, paid, share} ... ],
          "customers": [ {id, display_name, total, paid, due} ... ],
          "unassigned_total": float,   # lines nobody has claimed yet
          "grand_total": float,
          "paid_total": float,
          "fully_paid": bool,
        }
    """
    # Per-customer accumulator.
    totals = {c.id: 0.0 for c in session.customers}
    names = {c.id: c.display_name() for c in session.customers}

    unassigned_total = 0.0
    grand_total = 0.0
    items_out = []

    for item in session.items:
        line_total = item.line_total()
        grand_total += line_total
        assignees = list(item.assignees)
        share = round(line_total / len(assignees), 2) if assignees else 0.0

        if assignees:
            for c in assignees:
                totals[c.id] = totals.get(c.id, 0.0) + share
        else:
            unassigned_total += line_total

        items_out.append({
            "id": item.id,
            "name": item.name or (item.product.name if item.product else "Article"),
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": line_total,
            "assignee_ids": [c.id for c in assignees],
            "paid": item.paid,
            "share": share,
        })

    # How much each customer has already paid.
    paid_by_customer = {c.id: 0.0 for c in session.customers}
    paid_total = 0.0
    for p in session.payments:
        if p.status == "paid":
            paid_by_customer[p.customer_id] = paid_by_customer.get(p.customer_id, 0.0) + p.amount
            paid_total += p.amount

    customers_out = []
    for c in session.customers:
        total = round(totals.get(c.id, 0.0), 2)
        paid = round(paid_by_customer.get(c.id, 0.0), 2)
        customers_out.append({
            "id": c.id,
            "display_name": names[c.id],
            "total": total,
            "paid": paid,
            "due": round(max(total - paid, 0.0), 2),
        })

    fully_paid = session_fully_paid(session)

    return {
        "items": items_out,
        "customers": customers_out,
        "unassigned_total": round(unassigned_total, 2),
        "grand_total": round(grand_total, 2),
        "paid_total": round(paid_total, 2),
        "fully_paid": fully_paid,
    }


def session_fully_paid(session):
    """True when every assigned item is marked paid and nothing is left unclaimed."""
    if not session.items:
        return False
    for item in session.items:
        if not item.assignees:
            return False  # something still unclaimed
        if not item.paid:
            return False
    return True
