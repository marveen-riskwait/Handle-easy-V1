"""Shared route helpers."""
from flask_jwt_extended import get_jwt_identity

from api.models import User
from api.utils import APIException


def current_user():
    """The logged-in User from the JWT, or raise 401."""
    uid = get_jwt_identity()
    user = User.query.get(int(uid)) if uid is not None else None
    if user is None or not user.is_active:
        raise APIException("Session invalide", status_code=401)
    return user


def require_staff():
    """current_user() but also enforce a staff/admin role."""
    user = current_user()
    if not user.is_staff:
        raise APIException("Accès réservé au personnel", status_code=403)
    return user


def get_or_404(model, obj_id, label="Ressource"):
    obj = model.query.get(obj_id)
    if obj is None:
        raise APIException(f"{label} introuvable", status_code=404)
    return obj


def require_fields(body, *fields):
    body = body or {}
    missing = [f for f in fields if body.get(f) in (None, "")]
    if missing:
        raise APIException(
            f"Champs requis manquants: {', '.join(missing)}", status_code=422)
    return body
