"""Assemble every sub-blueprint under a single `api` blueprint.

app.py registers this with url_prefix="/api", so final paths look like
/api/auth/login, /api/tables, /api/sessions/<id>/pay, etc.
"""
from flask import Blueprint, jsonify

from .auth import auth_bp
from .tables import tables_bp
from .sessions import sessions_bp
from .customers import customers_bp
from .items import items_bp
from .payments import payments_bp
from .reviews import reviews_bp

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "handle-easy"})


api.register_blueprint(auth_bp, url_prefix="/auth")
api.register_blueprint(tables_bp, url_prefix="/tables")
# sessions/customers/items/payments/reviews declare their own full sub-paths
# (they span /sessions, /tables/.../session, /table/<token>, /odoo, ...), so
# they mount at the api root rather than under a shared prefix.
api.register_blueprint(sessions_bp)
api.register_blueprint(customers_bp)
api.register_blueprint(items_bp)
api.register_blueprint(payments_bp)
api.register_blueprint(reviews_bp)
