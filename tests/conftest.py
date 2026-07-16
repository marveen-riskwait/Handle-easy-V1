"""Pytest fixtures: a Flask test app on an isolated temp SQLite DB.

The app object is built at import time from env vars (see src/app.py), so we set
DATABASE_URL / FLASK_DEBUG *before* importing it.
"""
import os
import sys
import tempfile

import pytest

os.environ["FLASK_DEBUG"] = "1"                       # dev mode: no prod guards
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import app as flask_app          # noqa: E402
from api.models import db                 # noqa: E402


@pytest.fixture(scope="session")
def app():
    with flask_app.app_context():
        db.create_all()
    yield flask_app
    os.close(_DB_FD)
    os.unlink(_DB_PATH)


@pytest.fixture(scope="session")
def seeded(app):
    """Run the `seed` CLI command once, so the catalogue is populated."""
    app.test_cli_runner().invoke(args=["seed"])
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    """A test client already registered + logged in, with CSRF wired up.

    Returns (client, headers) where headers carry X-CSRF-TOKEN for writes.
    """
    import uuid
    email = f"t+{uuid.uuid4().hex[:8]}@demo.com"
    r = client.post("/api/auth/register", json={
        "email": email, "password": "password1",
        "first_name": "T", "last_name": "User"})
    csrf = r.get_json()["csrf_token"]
    return client, {"X-CSRF-TOKEN": csrf}, email
