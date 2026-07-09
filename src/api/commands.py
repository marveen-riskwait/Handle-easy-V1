"""CLI commands. `flask seed` builds a demo restaurant to click through."""
import click

from api.models import (
    db, Company, User, RestaurantTable, TableSession, Customer,
)
from api.services.qr.generator import new_token
from api.services.odoo.sync import sync_products, import_order_into_session


def setup_commands(app):

    @app.cli.command("seed")
    def seed():
        """Create a demo company, admin, tables, products and one open session."""
        if User.query.filter_by(email="admin@demo.com").first():
            click.echo("Seed already present — skipping.")
            return

        company = Company(name="Le Bistrot Démo", email="contact@bistrot-demo.com",
                          phone="+33123456789")
        db.session.add(company)
        db.session.flush()

        admin = User(company_id=company.id, firstname="Admin", lastname="Démo",
                     email="admin@demo.com", role="ADMIN")
        admin.set_password("demo1234")
        db.session.add(admin)

        tables = []
        for n in range(1, 9):
            t = RestaurantTable(company_id=company.id, table_number=str(n),
                                qr_token=new_token(), status="free")
            db.session.add(t)
            tables.append(t)
        db.session.flush()

        # Mirror the mock Odoo catalog.
        sync_products(company)

        # Open a session on table 8 and import the mock Odoo order 9001.
        table8 = next(t for t in tables if t.table_number == "8")
        session = TableSession(table_id=table8.id, status="open")
        db.session.add(session)
        table8.status = "occupied"
        db.session.flush()
        import_order_into_session(company, session, 9001)

        # A couple of guests already seated.
        db.session.add(Customer(session_id=session.id, name="Thomas", seat_number=1))
        db.session.add(Customer(session_id=session.id, name="Marie", seat_number=2))
        db.session.commit()

        click.echo("Seed created:")
        click.echo("  Login    → admin@demo.com / demo1234")
        click.echo(f"  Table 8 QR token → {table8.qr_token}")
        click.echo(f"  Guest URL → /table/{table8.qr_token}")
