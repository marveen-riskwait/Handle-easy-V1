"""Assemble every sub-blueprint under a single `api` blueprint.

app.py registers this with url_prefix="/api", so final paths look like
/api/auth/login, /api/stations, /api/reservations, etc.

Catalogue / availability / reservations / payments blueprints are added in
the following lots.
"""
from flask import Blueprint, jsonify

from .auth import auth_bp

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "rdv-cycles"})


api.register_blueprint(auth_bp, url_prefix="/auth")
