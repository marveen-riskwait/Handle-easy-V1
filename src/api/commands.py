"""CLI commands. `flask seed` builds demo data to click through the app."""
import click

from api.models import (
    db, User, Station, BikeModel, BikeUnit, RatePlan, Option,
)

# ── Tariff grid, in cents (rows = rate kinds, cols = price categories) ──
# Source: RDV Cycles printed grid. 'hour' & 'extra_day' are the marginal
# rates the pricing engine combines to price any duration.
GRID = {
    #             vtt_elec vtc_elec premium enfant route_alu_semi
    "h2":       [  3000,   2800,   2500,   1700,   2000 ],
    "half_day": [  4000,   3500,   3500,   2000,   2800 ],
    "day1":     [  5500,   5000,   4000,   2200,   3300 ],
    "day2":     [  9000,   8000,   7000,   3800,   5200 ],
    "day3":     [ 12500,  11500,  11000,   5500,   7000 ],
    "day4":     [ 15500,  14500,  14000,   6700,   9000 ],
}
CATEGORIES = ("vtt_elec", "vtc_elec", "premium", "enfant", "route_alu_semi")
HOUR_RATE = 1500                       # 15 € flat, every category
EXTRA_DAY = {                          # marginal day beyond the grid
    "vtt_elec": 3500, "vtc_elec": 3500,          # electric  → +35 €
    "premium": 2500, "enfant": 2500, "route_alu_semi": 2500,  # muscular → +25 €
}


def _seed_rate_plans():
    for kind, row in GRID.items():
        for cat, cents in zip(CATEGORIES, row):
            db.session.add(RatePlan(price_category=cat, kind=kind, price_cents=cents))
    for cat in CATEGORIES:
        db.session.add(RatePlan(price_category=cat, kind="hour", price_cents=HOUR_RATE))
        db.session.add(RatePlan(price_category=cat, kind="extra_day",
                                price_cents=EXTRA_DAY[cat]))


def setup_commands(app):

    @app.cli.command("seed")
    def seed():
        """Create demo users, stations, catalogue, rates, options and stock."""
        if User.query.filter_by(email="admin@rdv-cycles.fr").first():
            click.echo("Seed already present — skipping.")
            return

        # ── Accounts ──
        admin = User(email="admin@rdv-cycles.fr", first_name="Admin",
                     last_name="RDV", role="admin", email_verified=True)
        admin.set_password("demo1234")
        client = User(email="client@demo.com", first_name="Camille",
                      last_name="Client", role="customer", email_verified=True)
        client.set_password("demo1234")
        db.session.add_all([admin, client])

        # ── Stations ──
        le_bosc = Station(
            name="RDV Cycles — Le Bosc", slug="le-bosc",
            address="Centre Commercial Leclerc, ZA La Méridienne",
            city="Le Bosc", postal_code="34700", is_seasonal=False, active=True)
        vailhes = Station(
            name="Base nautique — Baie des Vailhés", slug="baie-des-vailhes",
            address="Lac du Salagou", city="Celles", postal_code="34700",
            is_seasonal=True, active=True)
        db.session.add_all([le_bosc, vailhes])

        # ── Rate plans (the tariff grid) ──
        _seed_rate_plans()

        # ── Options / add-ons ──
        options = [
            Option(name="Casque", slug="casque", price_cents=0,
                   price_type="per_rental"),           # offert
            Option(name="Antivol", slug="antivol", price_cents=0,
                   price_type="per_rental"),
            Option(name="Siège enfant", slug="siege-enfant", price_cents=500,
                   price_type="per_day"),
            Option(name="Remorque enfant", slug="remorque-enfant", price_cents=1000,
                   price_type="per_day"),
            Option(name="Assurance casse/vol", slug="assurance", price_cents=800,
                   price_type="per_day"),
        ]
        db.session.add_all(options)

        # ── Bike models (one per price category to start) ──
        models = [
            BikeModel(name="VTT électrique", slug="vtt-electrique",
                      price_category="vtt_elec", category="vae_mtb",
                      is_electric=True, deposit_cents=30000, sort_order=1,
                      description="VTT à assistance électrique, moteur central."),
            BikeModel(name="VTC électrique", slug="vtc-electrique",
                      price_category="vtc_elec", category="vtc",
                      is_electric=True, deposit_cents=30000, sort_order=2,
                      description="Vélo tout chemin électrique, confort et autonomie."),
            BikeModel(name="VTT tout suspendu / Route·Gravel carbone",
                      slug="premium-carbone", price_category="premium",
                      category="premium", is_electric=False, deposit_cents=40000,
                      sort_order=3, description="Vélos haut de gamme musculaires."),
            BikeModel(name="VTT enfant", slug="vtt-enfant",
                      price_category="enfant", category="kids",
                      is_electric=False, deposit_cents=8000, sort_order=4,
                      description="VTT musculaire pour enfant."),
            BikeModel(name="Route alu / VTT semi-rigide", slug="route-alu-semi",
                      price_category="route_alu_semi", category="road_mtb",
                      is_electric=False, deposit_cents=15000, sort_order=5,
                      description="Vélo route alu ou VTT semi-rigide."),
        ]
        db.session.add_all(models)
        db.session.flush()

        # ── Stock: a few units per model, per station, across sizes ──
        sizes = ["S", "M", "L"]
        for m in models:
            unit_sizes = ["Enfant"] if m.category == "kids" else sizes
            for station in (le_bosc, vailhes):
                for size in unit_sizes:
                    for _ in range(3):
                        db.session.add(BikeUnit(
                            model_id=m.id, station_id=station.id,
                            size=size, status="available"))

        db.session.commit()

        click.echo("Seed created:")
        click.echo("  Admin  → admin@rdv-cycles.fr / demo1234")
        click.echo("  Client → client@demo.com / demo1234")
        click.echo(f"  {len(models)} modèles, "
                   f"{RatePlan.query.count()} tarifs, "
                   f"{BikeUnit.query.count()} vélos en stock.")
