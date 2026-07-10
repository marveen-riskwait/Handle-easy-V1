"""SQLAlchemy models for RDV Cycles — bike-rental booking platform.

Design notes
------------
* Money is stored in **integer cents** (never floats) to avoid rounding drift.
* Datetimes are **timezone-aware UTC**; the API converts to Europe/Paris at
  the edges.
* A reservation books a **bike model + size**, not a specific physical unit.
  A concrete ``BikeUnit`` is only assigned at check-out. Availability is the
  count of units of a (model, size, station) minus the reservations that
  overlap the requested window — see ``services/availability.py``.
* Pricing is driven by a **price_category** (the 5 columns of the tariff
  grid), not by the individual model, so several models can share one rate.
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    String, Boolean, Integer, ForeignKey, Text, DateTime, JSON,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def utcnow() -> datetime:
    """Timezone-aware "now" — use everywhere instead of datetime.utcnow()."""
    return datetime.now(timezone.utc)


# ── Controlled vocabularies ─────────────────────────────────────────
# Kept as plain tuples (validated in schemas/services). Cheap to evolve,
# and avoids native DB enums that are painful to migrate.
ROLES = ("customer", "staff", "admin")

# The 5 columns of the tariff grid.
PRICE_CATEGORIES = (
    "vtt_elec",        # VTT électrique
    "vtc_elec",        # VTC électrique
    "premium",         # VTT tout suspendu alu / Route ou Gravel carbone
    "enfant",          # VTT enfant musculaire
    "route_alu_semi",  # Route alu / VTT semi-rigide
)
ELECTRIC_CATEGORIES = ("vtt_elec", "vtc_elec")  # +35 €/extra day, vs +25 € muscular

# Rate "kinds" = the rows of the grid, plus the hourly & marginal-day rates
# that the pricing engine combines to price any duration.
RATE_KINDS = ("hour", "h2", "half_day", "day1", "day2", "day3", "day4", "extra_day")

BIKE_UNIT_STATUS = ("available", "rented", "maintenance", "retired")
RESERVATION_STATUS = (
    "pending",     # created, stock held, awaiting payment
    "confirmed",   # paid
    "active",      # bikes picked up
    "completed",   # returned
    "cancelled",
    "no_show",
)
PAYMENT_TYPES = ("deposit", "balance", "full", "refund")
PAYMENT_STATUS = ("pending", "succeeded", "failed", "refunded")
OPTION_PRICE_TYPES = ("per_rental", "per_day")


# ── Accounts ────────────────────────────────────────────────────────
class User(db.Model):
    """A registered account. Guests can book without one (see Reservation)."""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str] = mapped_column(String(80), nullable=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)

    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
    locale: Mapped[str] = mapped_column(String(5), nullable=False, default="fr")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reservations = relationship("Reservation", back_populates="user")

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def is_staff(self) -> bool:
        return self.role in ("staff", "admin")

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "role": self.role,
            "locale": self.locale,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TokenBlocklist(db.Model):
    """Revoked JWT ids (logout / refresh rotation). Checked on every request."""
    __tablename__ = "token_blocklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(16), nullable=False)  # access | refresh
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Catalogue ───────────────────────────────────────────────────────
class Station(db.Model):
    """A pickup / return point (Le Bosc shop, Baie des Vailhés seasonal…)."""
    __tablename__ = "station"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(12), nullable=True)
    lat: Mapped[float] = mapped_column(nullable=True)
    lng: Mapped[float] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=True)
    is_seasonal: Mapped[bool] = mapped_column(Boolean, default=False)
    opening_hours: Mapped[dict] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    units = relationship("BikeUnit", back_populates="station")

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "address": self.address,
            "city": self.city,
            "postal_code": self.postal_code,
            "lat": self.lat,
            "lng": self.lng,
            "phone": self.phone,
            "is_seasonal": self.is_seasonal,
            "opening_hours": self.opening_hours,
            "active": self.active,
        }


class BikeModel(db.Model):
    """A catalogue item shown to customers (e.g. 'Gitane G-One Redwood').

    Its price comes from ``price_category`` (a tariff-grid column); several
    models can share the same category and therefore the same rates.
    """
    __tablename__ = "bike_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    price_category: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=True)   # marketing label
    description: Mapped[str] = mapped_column(Text, nullable=True)
    specs: Mapped[dict] = mapped_column(JSON, nullable=True)
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    deposit_cents: Mapped[int] = mapped_column(Integer, default=0)   # caution (CB hold)
    is_electric: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    units = relationship("BikeUnit", back_populates="model")

    def serialize(self, with_units: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "price_category": self.price_category,
            "category": self.category,
            "description": self.description,
            "specs": self.specs,
            "image_url": self.image_url,
            "deposit_cents": self.deposit_cents,
            "is_electric": self.is_electric,
            "active": self.active,
        }
        if with_units:
            data["units_count"] = len(self.units)
        return data


class BikeUnit(db.Model):
    """A physical bike (inventory). Assigned to a reservation at check-out."""
    __tablename__ = "bike_unit"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("bike_model.id"), nullable=False)
    station_id: Mapped[int] = mapped_column(ForeignKey("station.id"), nullable=False)
    size: Mapped[str] = mapped_column(String(10), nullable=True)   # XS…XXL / kids
    serial: Mapped[str] = mapped_column(String(80), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    model = relationship("BikeModel", back_populates="units")
    station = relationship("Station", back_populates="units")

    __table_args__ = (
        Index("ix_bike_unit_model_station_size", "model_id", "station_id", "size"),
    )

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "station_id": self.station_id,
            "size": self.size,
            "serial": self.serial,
            "status": self.status,
        }


class RatePlan(db.Model):
    """One cell of the pricing model: (price_category, kind) → price_cents.

    ``kind`` is one of RATE_KINDS. 'hour' / 'extra_day' are the marginal
    rates the engine uses to price arbitrary durations.
    """
    __tablename__ = "rate_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    price_category: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("price_category", "kind", name="uq_rate_category_kind"),
    )

    def serialize(self) -> dict:
        return {
            "price_category": self.price_category,
            "kind": self.kind,
            "price_cents": self.price_cents,
        }


class Option(db.Model):
    """A rentable add-on: casque enfant, siège bébé, remorque, antivol…"""
    __tablename__ = "option"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    price_type: Mapped[str] = mapped_column(String(16), default="per_rental")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "price_cents": self.price_cents,
            "price_type": self.price_type,
            "active": self.active,
        }


# ── Reservations ────────────────────────────────────────────────────
class Reservation(db.Model):
    """A booking. May belong to a User or to a guest (email-only checkout)."""
    __tablename__ = "reservation"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    # Guest contact snapshot (also filled for logged-in users at booking time).
    guest_email: Mapped[str] = mapped_column(String(120), nullable=True)
    guest_first_name: Mapped[str] = mapped_column(String(80), nullable=True)
    guest_last_name: Mapped[str] = mapped_column(String(80), nullable=True)
    guest_phone: Mapped[str] = mapped_column(String(40), nullable=True)

    pickup_station_id: Mapped[int] = mapped_column(ForeignKey("station.id"), nullable=False)
    return_station_id: Mapped[int] = mapped_column(ForeignKey("station.id"), nullable=False)

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    subtotal_cents: Mapped[int] = mapped_column(Integer, default=0)   # bikes
    options_cents: Mapped[int] = mapped_column(Integer, default=0)    # add-ons
    total_cents: Mapped[int] = mapped_column(Integer, default=0)      # charged online
    deposit_cents: Mapped[int] = mapped_column(Integer, default=0)    # CB hold (not charged)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    hold_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="reservations")
    pickup_station = relationship("Station", foreign_keys=[pickup_station_id])
    return_station = relationship("Station", foreign_keys=[return_station_id])
    lines = relationship("ReservationLine", back_populates="reservation",
                         cascade="all, delete-orphan")
    options = relationship("ReservationOption", back_populates="reservation",
                           cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="reservation",
                            cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reservation_window", "start_at", "end_at"),
        Index("ix_reservation_status", "status"),
    )

    def serialize(self, full: bool = False) -> dict:
        data = {
            "id": self.id,
            "reference": self.reference,
            "status": self.status,
            "pickup_station_id": self.pickup_station_id,
            "return_station_id": self.return_station_id,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "subtotal_cents": self.subtotal_cents,
            "options_cents": self.options_cents,
            "total_cents": self.total_cents,
            "deposit_cents": self.deposit_cents,
            "currency": self.currency,
            "customer": {
                "email": self.guest_email,
                "first_name": self.guest_first_name,
                "last_name": self.guest_last_name,
                "phone": self.guest_phone,
            },
        }
        if full:
            data["lines"] = [l.serialize() for l in self.lines]
            data["options"] = [o.serialize() for o in self.options]
            data["payments"] = [p.serialize() for p in self.payments]
        return data


class ReservationLine(db.Model):
    """A bike (model + size + quantity) within a reservation."""
    __tablename__ = "reservation_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservation.id", ondelete="CASCADE"), nullable=False)
    bike_model_id: Mapped[int] = mapped_column(ForeignKey("bike_model.id"), nullable=False)
    size: Mapped[str] = mapped_column(String(10), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    duration_label: Mapped[str] = mapped_column(String(40), nullable=True)  # e.g. "1 jour"
    unit_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    assigned_unit_id: Mapped[int] = mapped_column(
        ForeignKey("bike_unit.id"), nullable=True)  # set at check-out

    reservation = relationship("Reservation", back_populates="lines")
    bike_model = relationship("BikeModel")

    def line_total_cents(self) -> int:
        return (self.unit_price_cents or 0) * (self.quantity or 0)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "bike_model_id": self.bike_model_id,
            "size": self.size,
            "quantity": self.quantity,
            "duration_label": self.duration_label,
            "unit_price_cents": self.unit_price_cents,
            "line_total_cents": self.line_total_cents(),
            "assigned_unit_id": self.assigned_unit_id,
        }


class ReservationOption(db.Model):
    """An add-on attached to a reservation."""
    __tablename__ = "reservation_option"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservation.id", ondelete="CASCADE"), nullable=False)
    option_id: Mapped[int] = mapped_column(ForeignKey("option.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_cents: Mapped[int] = mapped_column(Integer, default=0)

    reservation = relationship("Reservation", back_populates="options")
    option = relationship("Option")

    def line_total_cents(self) -> int:
        return (self.unit_price_cents or 0) * (self.quantity or 0)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "option_id": self.option_id,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "line_total_cents": self.line_total_cents(),
        }


class Payment(db.Model):
    """A payment against a reservation (Stripe-shaped, mock-first)."""
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservation.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[str] = mapped_column(String(16), default="full")
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    provider_ref: Mapped[str] = mapped_column(String(120), nullable=True)  # payment_intent id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reservation = relationship("Reservation", back_populates="payments")

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "type": self.type,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "status": self.status,
            "provider_ref": self.provider_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Review(db.Model):
    """A customer review, tied to a completed reservation and/or a model."""
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservation.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    bike_model_id: Mapped[int] = mapped_column(ForeignKey("bike_model.id"), nullable=True)

    author_name: Mapped[str] = mapped_column(String(80), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "bike_model_id": self.bike_model_id,
            "author_name": self.author_name,
            "rating": self.rating,
            "comment": self.comment,
            "published": self.published,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
