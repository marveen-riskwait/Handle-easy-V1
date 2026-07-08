"""Sessions.

Staff (JWT) open/close a seating and pull the Odoo order into it.
Guests reach a session anonymously through the table's qr_token.
"""
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from api.models import db, RestaurantTable, TableSession
from api.utils import APIException
from api.services.odoo.sync import import_order_into_session
from api.services.odoo.client import OdooClient
from api.services.billing import compute_split
from ._helpers import current_user, get_table_or_404, get_session_or_404

sessions_bp = Blueprint("sessions", __name__)


# ── Staff ───────────────────────────────────────────────
@sessions_bp.route("/tables/<int:table_id>/session", methods=["POST"])
@jwt_required()
def open_session(table_id):
    """Open a new seating on a table and import its Odoo order (if any)."""
    user = current_user()
    table = get_table_or_404(table_id)
    if table.company_id != user.company_id:
        raise APIException("Accès refusé", status_code=403)
    if table.active_session():
        raise APIException("Une session est déjà ouverte sur cette table", status_code=409)

    body = request.get_json(silent=True) or {}
    session = TableSession(table_id=table.id, status="open")
    db.session.add(session)
    table.status = "occupied"
    db.session.flush()

    # Optionally bind an Odoo order and pull its lines right away.
    odoo_order_id = body.get("odoo_order_id")
    imported = 0
    if odoo_order_id:
        imported = import_order_into_session(table.company, session, odoo_order_id)
    db.session.commit()

    data = session.serialize()
    data["imported_items"] = imported
    return jsonify(data), 201


@sessions_bp.route("/sessions/<int:session_id>/import", methods=["POST"])
@jwt_required()
def import_order(session_id):
    """(Re)import an Odoo order's lines into an existing session."""
    user = current_user()
    session = get_session_or_404(session_id)
    if session.table.company_id != user.company_id:
        raise APIException("Accès refusé", status_code=403)

    body = request.get_json(silent=True) or {}
    odoo_order_id = body.get("odoo_order_id") or session.odoo_order_id
    if not odoo_order_id:
        raise APIException("odoo_order_id requis", status_code=422)
    imported = import_order_into_session(session.table.company, session, odoo_order_id)
    return jsonify({"imported_items": imported, "session": session.serialize()})


@sessions_bp.route("/sessions/<int:session_id>/close", methods=["POST"])
@jwt_required()
def close_session(session_id):
    """Force-close a session (e.g. guests left)."""
    user = current_user()
    session = get_session_or_404(session_id)
    if session.table.company_id != user.company_id:
        raise APIException("Accès refusé", status_code=403)
    session.status = "closed"
    session.closed_at = datetime.utcnow()
    session.table.status = "free"
    db.session.commit()
    return jsonify(session.serialize())


# ── Odoo open orders (staff) ────────────────────────────
@sessions_bp.route("/odoo/open-orders", methods=["GET"])
@jwt_required()
def odoo_open_orders():
    """List the restaurant's open POS orders so staff can bind one."""
    user = current_user()
    client = OdooClient(user.company)
    client.authenticate()
    return jsonify(client.get_open_orders())


# ── Public (guest) ──────────────────────────────────────
@sessions_bp.route("/table/<qr_token>", methods=["GET"])
def public_table(qr_token):
    """Guest landing: resolve a QR token to its table + live split state."""
    table = RestaurantTable.query.filter_by(qr_token=qr_token).first()
    if table is None:
        raise APIException("QR code invalide", status_code=404)

    # Prefer the live seating; fall back to the most recent one so a guest
    # who reloads right after paying still sees the "bill settled" screen.
    session = table.active_session()
    if session is None and table.sessions:
        session = max(table.sessions, key=lambda s: s.opened_at)
    payload = {
        "table": {"id": table.id, "table_number": table.table_number},
        "company": {"id": table.company_id, "name": table.company.name},
        "session": session.serialize() if session else None,
        "split": compute_split(session) if session else None,
    }
    if session:
        payload["customers"] = [c.serialize() for c in session.customers]
    return jsonify(payload)
