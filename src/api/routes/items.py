"""Order items + live split. Public — this is the guest bill-splitting flow."""
from flask import Blueprint, request, jsonify

from api.models import db, OrderItem, Product
from api.utils import APIException
from api.services.billing import compute_split
from ._helpers import get_session_or_404, get_customer_or_404

items_bp = Blueprint("items", __name__)


@items_bp.route("/sessions/<int:session_id>/split", methods=["GET"])
def get_split(session_id):
    session = get_session_or_404(session_id)
    return jsonify(compute_split(session))


@items_bp.route("/sessions/<int:session_id>/items", methods=["GET"])
def list_items(session_id):
    session = get_session_or_404(session_id)
    return jsonify([i.serialize() for i in session.items])


@items_bp.route("/sessions/<int:session_id>/items", methods=["POST"])
def add_item(session_id):
    """Manually add a line (used when there's no Odoo order to import)."""
    session = get_session_or_404(session_id)
    body = request.get_json(silent=True) or {}

    product = None
    if body.get("product_id"):
        product = Product.query.get(body["product_id"])

    name = body.get("name") or (product.name if product else None)
    unit_price = body.get("unit_price")
    if unit_price is None and product:
        unit_price = product.price
    if not name or unit_price is None:
        raise APIException("name et unit_price requis", status_code=422)

    item = OrderItem(
        session_id=session.id,
        product_id=product.id if product else None,
        name=name,
        quantity=body.get("quantity", 1),
        unit_price=float(unit_price),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.serialize()), 201


def _get_item_in_session(session, item_id):
    item = OrderItem.query.get(item_id)
    if item is None or item.session_id != session.id:
        raise APIException("Article introuvable", status_code=404)
    return item


@items_bp.route("/sessions/<int:session_id>/items/<int:item_id>/claim", methods=["POST"])
def claim_item(session_id, item_id):
    """A guest claims (or shares) a line. Body: {customer_id}."""
    session = get_session_or_404(session_id)
    item = _get_item_in_session(session, item_id)
    body = request.get_json(silent=True) or {}
    if not body.get("customer_id"):
        raise APIException("customer_id requis", status_code=422)
    customer = get_customer_or_404(body["customer_id"])
    if customer.session_id != session.id:
        raise APIException("Ce client n'appartient pas à la session", status_code=422)

    if item.paid:
        raise APIException("Cet article est déjà payé", status_code=409)
    if customer not in item.assignees:
        item.assignees.append(customer)
        db.session.commit()
    return jsonify(compute_split(session))


@items_bp.route("/sessions/<int:session_id>/items/<int:item_id>/unclaim", methods=["POST"])
def unclaim_item(session_id, item_id):
    """A guest removes themselves from a line. Body: {customer_id}."""
    session = get_session_or_404(session_id)
    item = _get_item_in_session(session, item_id)
    body = request.get_json(silent=True) or {}
    if not body.get("customer_id"):
        raise APIException("customer_id requis", status_code=422)
    customer = get_customer_or_404(body["customer_id"])

    if item.paid:
        raise APIException("Cet article est déjà payé", status_code=409)
    if customer in item.assignees:
        item.assignees.remove(customer)
        db.session.commit()
    return jsonify(compute_split(session))
