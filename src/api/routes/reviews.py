"""Guest reviews of products. Public."""
from flask import Blueprint, request, jsonify

from api.models import db, Review, Product
from api.utils import APIException
from ._helpers import get_customer_or_404

reviews_bp = Blueprint("reviews", __name__)


@reviews_bp.route("/reviews", methods=["POST"])
def create_review():
    body = request.get_json(silent=True) or {}
    for f in ("customer_id", "product_id", "rating"):
        if body.get(f) in (None, ""):
            raise APIException(f"{f} requis", status_code=422)

    customer = get_customer_or_404(body["customer_id"])
    product = Product.query.get(body["product_id"])
    if product is None:
        raise APIException("Produit introuvable", status_code=404)

    rating = int(body["rating"])
    if not 1 <= rating <= 5:
        raise APIException("La note doit être entre 1 et 5", status_code=422)

    review = Review(
        customer_id=customer.id,
        product_id=product.id,
        rating=rating,
        comment=(body.get("comment") or "").strip() or None,
    )
    db.session.add(review)
    db.session.commit()
    return jsonify(review.serialize()), 201


@reviews_bp.route("/products/<int:product_id>/reviews", methods=["GET"])
def list_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id) \
        .order_by(Review.created_at.desc()).all()
    return jsonify([r.serialize() for r in reviews])
