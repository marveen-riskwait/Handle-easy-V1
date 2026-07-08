"""Shared route helpers."""
from flask_jwt_extended import get_jwt_identity

from api.models import User, RestaurantTable, TableSession, Customer
from api.utils import APIException


def current_user():
    """The logged-in staff User from the JWT, or raise 401."""
    uid = get_jwt_identity()
    user = User.query.get(int(uid)) if uid is not None else None
    if user is None:
        raise APIException("Session invalide", status_code=401)
    return user


def get_table_or_404(table_id):
    t = RestaurantTable.query.get(table_id)
    if t is None:
        raise APIException("Table introuvable", status_code=404)
    return t


def get_session_or_404(session_id):
    s = TableSession.query.get(session_id)
    if s is None:
        raise APIException("Session introuvable", status_code=404)
    return s


def get_customer_or_404(customer_id):
    c = Customer.query.get(customer_id)
    if c is None:
        raise APIException("Client introuvable", status_code=404)
    return c


def require_fields(body, *fields):
    body = body or {}
    missing = [f for f in fields if body.get(f) in (None, "")]
    if missing:
        raise APIException(f"Champs requis manquants: {', '.join(missing)}", status_code=422)
    return body
