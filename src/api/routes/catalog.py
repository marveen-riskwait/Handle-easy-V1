"""Public catalogue endpoints (Lot 1) — read-only, no auth required.

Everything a visitor needs to browse before booking: pickup/return stations,
the bike models with their "from" price, the tariff grid, and the add-on
options. Availability for a given window is a later lot; here we just list the
offer.
"""
from flask import Blueprint, jsonify

from api.models import Station, BikeModel, Option, RatePlan, PRICE_CATEGORIES
from api.services.pricing import rates_for, from_price_cents
from api.utils import APIException

catalog_bp = Blueprint("catalog", __name__)


@catalog_bp.get("/stations")
def list_stations():
    stations = (Station.query.filter_by(active=True)
                .order_by(Station.is_seasonal, Station.name))
    return jsonify({"stations": [s.serialize() for s in stations]})


@catalog_bp.get("/bikes")
def list_bikes():
    """Active bike models, each with its cheapest bookable price (cents)."""
    models = (BikeModel.query.filter_by(active=True)
              .order_by(BikeModel.sort_order, BikeModel.name))
    out = []
    for m in models:
        data = m.serialize()
        data["from_price_cents"] = from_price_cents(m.price_category)
        out.append(data)
    return jsonify({"bikes": out})


@catalog_bp.get("/bikes/<slug>")
def get_bike(slug):
    m = BikeModel.query.filter_by(slug=slug, active=True).first()
    if m is None:
        raise APIException("Modèle introuvable", status_code=404)
    data = m.serialize(with_units=True)
    rates = rates_for(m.price_category)
    data["from_price_cents"] = from_price_cents(m.price_category, rates)
    data["rates"] = rates
    return jsonify({"bike": data})


@catalog_bp.get("/options")
def list_options():
    options = Option.query.filter_by(active=True).order_by(Option.name)
    return jsonify({"options": [o.serialize() for o in options]})


@catalog_bp.get("/rates")
def list_rates():
    """The full tariff grid, grouped by price category."""
    grid = {cat: {} for cat in PRICE_CATEGORIES}
    for rp in RatePlan.query:
        grid.setdefault(rp.price_category, {})[rp.kind] = rp.price_cents
    return jsonify({"rates": grid})
