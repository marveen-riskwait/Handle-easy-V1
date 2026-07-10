"""Flask-Admin: quick DB back-office at /admin (dev + staff convenience)."""
import os

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from api.models import (
    db, User, Station, BikeModel, BikeUnit, RatePlan, Option,
    Reservation, ReservationLine, ReservationOption, Payment, Review,
)


def setup_admin(app):
    app.secret_key = os.getenv("FLASK_APP_KEY", "super-secret-change-me")
    admin = Admin(app, name="RDV Cycles")
    for model in (User, Station, BikeModel, BikeUnit, RatePlan, Option,
                  Reservation, ReservationLine, ReservationOption,
                  Payment, Review):
        admin.add_view(ModelView(model, db.session))
