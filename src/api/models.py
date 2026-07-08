"""SQLAlchemy models for Handle Easy.

Our app is an *overlay* on Odoo POS: Odoo owns the real orders/products, we
mirror what we need (products, order lines) and own everything about how a
table's guests split and pay their share. See services/odoo for the sync.
"""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    String, Boolean, Float, Integer, ForeignKey, Table, Column,
    Text, DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Roles a User can hold within a company.
ROLES = ("ADMIN", "MANAGER", "WAITER", "CLIENT")


# ── Association: which guests share a given order line ───────────────
# A line can be claimed by one guest (Burger → Thomas) or shared by
# several (Vin → Marie + Thomas + Paul). Each assignee owes an equal
# fraction of the line total — see services/billing.compute_split.
item_assignments = Table(
    "item_assignments",
    db.metadata,
    Column("order_item_id", ForeignKey("order_item.id", ondelete="CASCADE"), primary_key=True),
    Column("customer_id", ForeignKey("customer.id", ondelete="CASCADE"), primary_key=True),
)


class Company(db.Model):
    """A restaurant. Holds its own Odoo connection credentials."""
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)

    odoo_url: Mapped[str] = mapped_column(String(255), nullable=True)
    odoo_database: Mapped[str] = mapped_column(String(120), nullable=True)
    odoo_username: Mapped[str] = mapped_column(String(120), nullable=True)
    odoo_api_key: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    tables = relationship("RestaurantTable", back_populates="company", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "odoo_url": self.odoo_url,
            "odoo_database": self.odoo_database,
            "odoo_username": self.odoo_username,
            # api key never leaves the backend
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    """Staff account (ADMIN / MANAGER / WAITER). Guests are Customers, not Users."""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), nullable=False)

    firstname: Mapped[str] = mapped_column(String(80), nullable=True)
    lastname: Mapped[str] = mapped_column(String(80), nullable=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITER")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def serialize(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RestaurantTable(db.Model):
    """A physical table. Its qr_token is what the printed QR code points to."""
    __tablename__ = "restaurant_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), nullable=False)

    table_number: Mapped[str] = mapped_column(String(20), nullable=False)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="free")  # free | occupied

    company = relationship("Company", back_populates="tables")
    sessions = relationship("TableSession", back_populates="table", cascade="all, delete-orphan")

    def active_session(self):
        for s in self.sessions:
            if s.status != "closed":
                return s
        return None

    def serialize(self):
        active = self.active_session()
        return {
            "id": self.id,
            "company_id": self.company_id,
            "table_number": self.table_number,
            "qr_token": self.qr_token,
            "status": self.status,
            "active_session_id": active.id if active else None,
        }


class TableSession(db.Model):
    """One seating of guests at a table, mapped to one Odoo POS order."""
    __tablename__ = "table_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("restaurant_table.id"), nullable=False)
    odoo_order_id: Mapped[int] = mapped_column(Integer, nullable=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | settling | closed

    table = relationship("RestaurantTable", back_populates="sessions")
    customers = relationship("Customer", back_populates="session", cascade="all, delete-orphan")
    items = relationship("OrderItem", back_populates="session", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="session", cascade="all, delete-orphan")

    def serialize(self):
        return {
            "id": self.id,
            "table_id": self.table_id,
            "table_number": self.table.table_number if self.table else None,
            "odoo_order_id": self.odoo_order_id,
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class Customer(db.Model):
    """A guest at a session. No login — created when they scan the QR."""
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("table_session.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=True)  # null → "Invité N"
    seat_number: Mapped[int] = mapped_column(Integer, nullable=True)

    session = relationship("TableSession", back_populates="customers")
    items = relationship("OrderItem", secondary=item_assignments, back_populates="assignees")

    def display_name(self):
        return self.name or f"Invité {self.seat_number or self.id}"

    def serialize(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "display_name": self.display_name(),
            "seat_number": self.seat_number,
        }


class Product(db.Model):
    """A menu product mirrored from Odoo."""
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), nullable=False)
    odoo_product_id: Mapped[int] = mapped_column(Integer, nullable=True)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(80), nullable=True)

    company = relationship("Company", back_populates="products")

    def serialize(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "odoo_product_id": self.odoo_product_id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
        }


class OrderItem(db.Model):
    """One line of the table's order (mirrored from an Odoo order line)."""
    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("table_session.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=True)
    odoo_line_id: Mapped[int] = mapped_column(Integer, nullable=True)

    name: Mapped[str] = mapped_column(String(120), nullable=True)  # snapshot of product name
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    session = relationship("TableSession", back_populates="items")
    product = relationship("Product")
    assignees = relationship("Customer", secondary=item_assignments, back_populates="items")

    def line_total(self):
        return round(self.unit_price * self.quantity, 2)

    def serialize(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "product_id": self.product_id,
            "name": self.name or (self.product.name if self.product else None),
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "line_total": self.line_total(),
            "paid": self.paid,
            "assignee_ids": [c.id for c in self.assignees],
        }


class Payment(db.Model):
    """A guest paying their share of the session."""
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("table_session.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)

    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | paid
    stripe_payment_id: Mapped[str] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session = relationship("TableSession", back_populates="payments")
    customer = relationship("Customer")

    def serialize(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "status": self.status,
            "stripe_payment_id": self.stripe_payment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Review(db.Model):
    """A guest's rating of a product they consumed."""
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)

    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def serialize(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
