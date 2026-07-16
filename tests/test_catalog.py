"""Public catalogue endpoints (Lot 1)."""


def test_stations_listed(seeded, client):
    data = client.get("/api/stations").get_json()
    names = [s["name"] for s in data["stations"]]
    assert any("Le Bosc" in n for n in names)
    # Seasonal station sorts after the year-round one.
    assert data["stations"][0]["is_seasonal"] is False


def test_bikes_have_from_price(seeded, client):
    bikes = client.get("/api/bikes").get_json()["bikes"]
    assert bikes, "catalogue should not be empty after seeding"
    for b in bikes:
        assert b["from_price_cents"] is not None
        assert b["from_price_cents"] > 0
    # The kids bike (enfant) is the cheapest entry point: 2h rate = 1700.
    enfant = next(b for b in bikes if b["price_category"] == "enfant")
    assert enfant["from_price_cents"] == 1700


def test_bike_detail_includes_rate_grid(seeded, client):
    detail = client.get("/api/bikes/vtt-electrique").get_json()["bike"]
    assert detail["slug"] == "vtt-electrique"
    assert detail["rates"]["day1"] == 5500        # from the seeded grid
    assert detail["units_count"] > 0


def test_unknown_bike_is_404(seeded, client):
    assert client.get("/api/bikes/does-not-exist").status_code == 404


def test_rates_grid_grouped_by_category(seeded, client):
    grid = client.get("/api/rates").get_json()["rates"]
    assert grid["vtt_elec"]["hour"] == 1500       # flat hourly rate
    assert grid["vtt_elec"]["extra_day"] == 3500  # electric marginal day


def test_options_listed(seeded, client):
    options = client.get("/api/options").get_json()["options"]
    slugs = {o["slug"] for o in options}
    assert {"casque", "antivol", "assurance"} <= slugs
