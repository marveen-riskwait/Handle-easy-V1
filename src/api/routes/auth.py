"""Customer & staff authentication.

Access + refresh JWTs live in **httpOnly cookies** with CSRF double-submit
protection, so the SPA never stores a raw token in JS. Logout and refresh
rotation revoke old tokens via the ``token_blocklist`` table.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
    get_csrf_token, get_jwt, jwt_required,
)

from api.models import db, User, TokenBlocklist
from api.utils import APIException
from ._helpers import current_user, require_fields

auth_bp = Blueprint("auth", __name__)


def _issue_session(user, status=200):
    """Set access+refresh cookies and return the user + CSRF token."""
    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))
    resp = jsonify({"user": user.serialize(), "csrf_token": get_csrf_token(access)})
    set_access_cookies(resp, access)
    set_refresh_cookies(resp, refresh)
    return resp, status


def _revoke(jwt_payload):
    """Add a decoded token's jti to the blocklist (idempotent-ish)."""
    jti = jwt_payload["jti"]
    if not TokenBlocklist.query.filter_by(jti=jti).first():
        db.session.add(TokenBlocklist(
            jti=jti,
            token_type=jwt_payload.get("type", "access"),
            user_id=int(jwt_payload["sub"]) if jwt_payload.get("sub") else None,
        ))


@auth_bp.route("/register", methods=["POST"])
def register():
    """Create a customer account and log them in."""
    body = require_fields(request.get_json(silent=True), "email", "password")
    email = body["email"].strip().lower()

    if User.query.filter_by(email=email).first():
        raise APIException("Un compte existe déjà avec cet email", status_code=409)
    if len(body["password"]) < 8:
        raise APIException("Le mot de passe doit faire au moins 8 caractères",
                           status_code=422)

    user = User(
        email=email,
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        phone=body.get("phone"),
        role="customer",
    )
    user.set_password(body["password"])
    db.session.add(user)
    db.session.commit()

    return _issue_session(user, status=201)


@auth_bp.route("/login", methods=["POST"])
def login():
    body = require_fields(request.get_json(silent=True), "email", "password")
    user = User.query.filter_by(email=body["email"].strip().lower()).first()
    if user is None or not user.check_password(body["password"]):
        raise APIException("Email ou mot de passe incorrect", status_code=401)
    if not user.is_active:
        raise APIException("Compte désactivé", status_code=403)
    return _issue_session(user)


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Rotate the refresh token and mint a fresh access token."""
    user = current_user()
    _revoke(get_jwt())            # invalidate the used refresh token
    db.session.commit()
    return _issue_session(user)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    """Revoke the presented token and clear cookies."""
    _revoke(get_jwt())
    db.session.commit()
    resp = jsonify({"message": "Déconnecté"})
    unset_jwt_cookies(resp)
    return resp


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    return jsonify({"user": current_user().serialize()})
