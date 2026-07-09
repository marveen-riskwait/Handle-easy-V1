"""Payments. Public — a guest settles their share of the session.

Mock gateway only (see services/payment/gateway). Paying settles a guest's
whole due; an item flips to paid once *every* guest sharing it has settled,
and when the last item is paid the session closes and Odoo is notified.
"""
from datetime import datetime

from flask import Blueprint, request, jsonify

from api.models import db, Payment
from api.utils import APIException
from api.services.billing import compute_split, session_fully_paid
from api.services.payment.gateway import charge
from api.services.odoo.client import OdooClient
from ._helpers import get_session_or_404, get_customer_or_404

payments_bp = Blueprint("payments", __name__)


def _customer_paid(session, customer_id):
    return sum(p.amount for p in session.payments
               if p.customer_id == customer_id and p.status == "paid")


def _settle_items_and_maybe_close(session):
    """Flip items to paid when all their assignees have settled; close if done."""
    split = compute_split(session)
    totals = {c["id"]: c["total"] for c in split["customers"]}

    def is_settled(cid):
        paid = _customer_paid(session, cid)
        return paid + 0.001 >= totals.get(cid, 0.0)

    for item in session.items:
        if item.assignees and all(is_settled(c.id) for c in item.assignees):
            item.paid = True

    if session_fully_paid(session):
        session.status = "closed"
        session.closed_at = datetime.utcnow()
        session.table.status = "free"
        if session.odoo_order_id:
            OdooClient(session.table.company).mark_order_paid(session.odoo_order_id)
    db.session.commit()


@payments_bp.route("/sessions/<int:session_id>/pay", methods=["POST"])
def pay(session_id):
    """A guest pays their outstanding share. Body: {customer_id}."""
    session = get_session_or_404(session_id)
    if session.status == "closed":
        raise APIException("Session déjà clôturée", status_code=409)

    body = request.get_json(silent=True) or {}
    if not body.get("customer_id"):
        raise APIException("customer_id requis", status_code=422)
    customer = get_customer_or_404(body["customer_id"])
    if customer.session_id != session.id:
        raise APIException("Ce client n'appartient pas à la session", status_code=422)

    split = compute_split(session)
    due = next((c["due"] for c in split["customers"] if c["id"] == customer.id), 0.0)
    if due <= 0:
        raise APIException("Rien à payer pour ce client", status_code=409)

    # Optional tip, charged on top of the bill share.
    try:
        tip = round(float(body.get("tip") or 0), 2)
    except (TypeError, ValueError):
        tip = 0.0
    if tip < 0:
        tip = 0.0

    receipt = charge(due + tip, customer.display_name())
    payment = Payment(
        customer_id=customer.id,
        amount=due,
        tip=tip,
        status="paid",
        stripe_payment_id=receipt["id"],
    )
    # Append to the relationship (not just db.session.add) so the already
    # loaded session.payments collection sees it when we recompute below.
    session.payments.append(payment)
    db.session.flush()

    _settle_items_and_maybe_close(session)

    return jsonify({
        "payment": payment.serialize(),
        "split": compute_split(session),
        "session": session.serialize(),
    })


@payments_bp.route("/sessions/<int:session_id>/payments", methods=["GET"])
def list_payments(session_id):
    session = get_session_or_404(session_id)
    return jsonify([p.serialize() for p in session.payments])
