"""Flask-Admin: quick DB browser at /admin (dev convenience)."""
import os

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from api.models import (
    db, Company, User, RestaurantTable, TableSession,
    Customer, Product, OrderItem, Payment, Review,
)


def setup_admin(app):
    app.secret_key = os.getenv("FLASK_APP_KEY", "super-secret-change-me")
    admin = Admin(app, name="Handle Easy")
    for model in (Company, User, RestaurantTable, TableSession, Customer,
                  Product, OrderItem, Payment, Review):
        admin.add_view(ModelView(model, db.session))
