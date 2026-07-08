"""Staff: manage tables and their QR codes (all JWT-protected)."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from api.models import db, RestaurantTable
from api.utils import APIException
from api.services.qr.generator import new_token, qr_data_uri
from ._helpers import current_user, get_table_or_404

tables_bp = Blueprint("tables", __name__)


@tables_bp.route("", methods=["GET"])
@jwt_required()
def list_tables():
    user = current_user()
    tables = RestaurantTable.query.filter_by(company_id=user.company_id) \
        .order_by(RestaurantTable.id).all()
    return jsonify([t.serialize() for t in tables])


@tables_bp.route("", methods=["POST"])
@jwt_required()
def create_table():
    user = current_user()
    body = request.get_json(silent=True) or {}
    number = body.get("table_number")
    if not number:
        raise APIException("table_number requis", status_code=422)
    table = RestaurantTable(
        company_id=user.company_id,
        table_number=str(number),
        qr_token=new_token(),
        status="free",
    )
    db.session.add(table)
    db.session.commit()
    return jsonify(table.serialize()), 201


@tables_bp.route("/<int:table_id>", methods=["GET"])
@jwt_required()
def get_table(table_id):
    user = current_user()
    table = get_table_or_404(table_id)
    if table.company_id != user.company_id:
        raise APIException("Accès refusé", status_code=403)
    data = table.serialize()
    data["qr"] = qr_data_uri(table.qr_token)
    return jsonify(data)


@tables_bp.route("/<int:table_id>", methods=["DELETE"])
@jwt_required()
def delete_table(table_id):
    user = current_user()
    table = get_table_or_404(table_id)
    if table.company_id != user.company_id:
        raise APIException("Accès refusé", status_code=403)
    db.session.delete(table)
    db.session.commit()
    return jsonify({"message": "Table supprimée"})
