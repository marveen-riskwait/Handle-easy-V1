"""Staff authentication: register a restaurant, login, logout, me.

JWT lives in an httpOnly cookie; the CSRF token is returned in the body so
the SPA can echo it back in the X-CSRF-TOKEN header on writes.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, set_access_cookies, unset_jwt_cookies,
    get_csrf_token, jwt_required,
)

from api.models import db, Company, User
from api.utils import APIException
from ._helpers import current_user, require_fields

auth_bp = Blueprint("auth", __name__)


def _session_payload(user):
    token = create_access_token(identity=str(user.id))
    resp = jsonify({"user": user.serialize(), "csrf_token": get_csrf_token(token)})
    set_access_cookies(resp, token)
    return resp


@auth_bp.route("/register", methods=["POST"])
def register():
    """Create a company + its first ADMIN user, and log them in."""
    body = require_fields(request.get_json(silent=True),
                          "company_name", "email", "password")

    if User.query.filter_by(email=body["email"].lower()).first():
        raise APIException("Un compte existe déjà avec cet email", status_code=409)

    company = Company(
        name=body["company_name"],
        email=body.get("email"),
        phone=body.get("phone"),
        odoo_url=body.get("odoo_url"),
        odoo_database=body.get("odoo_database"),
        odoo_username=body.get("odoo_username"),
        odoo_api_key=body.get("odoo_api_key"),
    )
    db.session.add(company)
    db.session.flush()  # get company.id

    user = User(
        company_id=company.id,
        firstname=body.get("firstname"),
        lastname=body.get("lastname"),
        email=body["email"].lower(),
        role="ADMIN",
    )
    user.set_password(body["password"])
    db.session.add(user)
    db.session.commit()

    return _session_payload(user), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    body = require_fields(request.get_json(silent=True), "email", "password")
    user = User.query.filter_by(email=body["email"].lower()).first()
    if user is None or not user.check_password(body["password"]):
        raise APIException("Email ou mot de passe incorrect", status_code=401)
    return _session_payload(user)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"message": "Déconnecté"})
    unset_jwt_cookies(resp)
    return resp


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = current_user()
    return jsonify({"user": user.serialize(), "company": user.company.serialize()})
