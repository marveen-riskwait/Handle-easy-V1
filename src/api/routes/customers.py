"""Guests joining a session. Public (guarded by the session/qr flow)."""
from flask import Blueprint, request, jsonify

from api.models import db, Customer
from api.utils import APIException
from ._helpers import get_session_or_404

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/sessions/<int:session_id>/customers", methods=["POST"])
def join_session(session_id):
    """A guest joins the seating. Name is optional → 'Invité N'."""
    session = get_session_or_404(session_id)
    if session.status == "closed":
        raise APIException("Cette session est clôturée", status_code=409)

    body = request.get_json(silent=True) or {}
    seat = len(session.customers) + 1
    customer = Customer(
        session_id=session.id,
        name=(body.get("name") or "").strip() or None,
        seat_number=seat,
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify(customer.serialize()), 201


@customers_bp.route("/sessions/<int:session_id>/customers", methods=["GET"])
def list_customers(session_id):
    session = get_session_or_404(session_id)
    return jsonify([c.serialize() for c in session.customers])
