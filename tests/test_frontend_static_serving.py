import shutil
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module


def test_frontend_assets_are_served(monkeypatch):
    temp_root = Path("tests/.tmp/frontend-static")
    if temp_root.exists():
        shutil.rmtree(temp_root)

    dist_dir = temp_root / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)

    (dist_dir / "index.html").write_text(
        '<!doctype html><html><body><script type="module" src="/assets/index.js"></script></body></html>',
        encoding="utf-8",
    )
    (assets_dir / "index.js").write_text('console.log("ok");', encoding="utf-8")

    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist_dir)
    monkeypatch.setattr(main_module, "FRONTEND_ASSETS_DIR", assets_dir)

    client = TestClient(main_module.app)

    response = client.get("/assets/index.js")

    assert response.status_code == 200
    assert "console.log" in response.text


def test_frontend_spa_routes_fallback_to_index(monkeypatch):
    temp_root = Path("tests/.tmp/frontend-spa")
    if temp_root.exists():
        shutil.rmtree(temp_root)

    dist_dir = temp_root / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<!doctype html><html><body>dashboard</body></html>", encoding="utf-8")

    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist_dir)
    monkeypatch.setattr(main_module, "FRONTEND_ASSETS_DIR", dist_dir / "assets")

    client = TestClient(main_module.app)

    response = client.get("/portfolio")

    assert response.status_code == 200
    assert "dashboard" in response.text


def test_assets_options_api_route_still_wins():
    client = TestClient(main_module.app)

    response = client.get("/assets/options")

    assert response.status_code == 200
    assert "items" in response.json()


def test_portfolio_api_route_still_wins():
    client = TestClient(main_module.app)

    response = client.post("/portfolio/recommend", json={})

    assert response.status_code != 200


def test_assets_options_prefers_local_artifacts(monkeypatch):
    monkeypatch.setattr(main_module, "_fallback_symbol_to_ticker_map", lambda: {"BTC": "BTC-USD", "ETH": "ETH-USD"})

    def fail_if_called():
        raise AssertionError("database should not be queried when artifact options are available")

    monkeypatch.setattr(main_module, "get_coin_repository", fail_if_called)

    client = TestClient(main_module.app)
    response = client.get("/assets/options")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"symbol": "BTC", "yahoo_ticker": "BTC-USD"},
            {"symbol": "ETH", "yahoo_ticker": "ETH-USD"},
        ]
    }
