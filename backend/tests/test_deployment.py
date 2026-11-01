"""Regressions for releases that previously became healthy, empty deployments."""

from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import duckdb
import httpx
import pytest

from app.schemas import ALL_TABLES
from app.snapshot import validate_snapshot
from prepare_database import prepare_database
from verify_deployment import deployment_matches


@pytest.fixture
def snapshot(tmp_path):
    path = tmp_path / "source.duckdb"
    with duckdb.connect(str(path)) as conn:
        for sql in ALL_TABLES:
            conn.execute(sql)
        conn.execute("INSERT INTO crls (id, text) VALUES ('letter', 'Letter text')")
        conn.execute("""INSERT INTO crl_summaries (id, crl_id, summary)
                        VALUES ('summary', 'letter', 'Summary text')""")
        conn.execute("""INSERT INTO processing_metadata (key, value)
                        VALUES ('last_data_update', '2026-10-31')""")
    return path


def test_valid_snapshot_is_read_without_changes(snapshot):
    before = snapshot.read_bytes()
    report = validate_snapshot(snapshot)
    assert report["total_crls"] == report["total_summaries"] == 1
    assert report["last_data_update"] == "2026-10-31"
    assert snapshot.read_bytes() == before


def test_missing_database_is_not_created(tmp_path):
    missing = tmp_path / "missing.duckdb"
    with pytest.raises(ValueError, match="missing or empty"):
        prepare_database(str(missing))
    assert not missing.exists()


@pytest.mark.parametrize("invalid", ["empty", "html", "no_records", "no_summaries", "no_metadata", "wal"])
def test_invalid_snapshot_is_rejected(snapshot, invalid):
    if invalid == "empty":
        snapshot.write_bytes(b"")
    elif invalid == "html":
        snapshot.write_text("<html>Download unavailable</html>")
    elif invalid == "wal":
        Path(f"{snapshot}.wal").write_bytes(b"uncheckpointed data")
    else:
        table = {"no_records": "crls", "no_summaries": "crl_summaries",
                 "no_metadata": "processing_metadata"}[invalid]
        with duckdb.connect(str(snapshot)) as conn:
            conn.execute(f"DELETE FROM {table}")
    with pytest.raises((ValueError, duckdb.Error)):
        validate_snapshot(snapshot)


def test_successful_download_replaces_only_after_validation(snapshot, tmp_path, monkeypatch):
    destination = tmp_path / "volume" / "database.duckdb"
    destination.parent.mkdir()
    destination.write_bytes(b"old database")

    def download(command, check):
        assert check
        assert "--retry-all-errors" in command
        assert destination.read_bytes() == b"old database"
        target = Path(command[command.index("--output") + 1])
        assert target.parent == destination.parent
        assert target != destination
        shutil.copyfile(snapshot, target)

    monkeypatch.setattr("prepare_database.subprocess.run", download)
    assert prepare_database(str(destination), "https://example.test/db")["total_crls"] == 1
    assert destination.read_bytes() == snapshot.read_bytes()
    assert not list(destination.parent.glob(".crl-download-*"))


@pytest.mark.parametrize("failure", ["network", "invalid", "incompatible", "existing_wal"])
@pytest.mark.parametrize("existing", [True, False])
def test_failed_download_does_not_destroy_or_create_database(snapshot, tmp_path, monkeypatch, failure, existing):
    destination = tmp_path / "destination.duckdb"
    if existing:
        shutil.copyfile(snapshot, destination)
    original = destination.read_bytes() if existing else None
    if failure == "existing_wal":
        Path(f"{destination}.wal").write_bytes(b"pending writes")

    def download(command, check):
        target = Path(command[command.index("--output") + 1])
        if failure in ("network", "invalid"):
            target.write_bytes(b"partial download")
        else:
            shutil.copyfile(snapshot, target)
        if failure == "network":
            raise subprocess.CalledProcessError(22, command)

    monkeypatch.setattr("prepare_database.subprocess.run", download)
    if failure == "incompatible":
        monkeypatch.setattr("prepare_database.validate_snapshot",
                            lambda path: (_ for _ in ()).throw(duckdb.IOException("Unsupported storage version")))
    with pytest.raises((ValueError, duckdb.Error, subprocess.CalledProcessError)):
        prepare_database(str(destination), "https://example.test/db")
    if existing:
        assert destination.read_bytes() == original
    else:
        assert not destination.exists()
    assert not list(tmp_path.glob(".crl-download-*"))


@pytest.mark.parametrize("endpoint", ["/health", "/api/health"])
def test_empty_database_is_http_503(client, test_db, endpoint):
    test_db.execute("DELETE FROM crl_embeddings")
    test_db.execute("DELETE FROM crl_summaries")
    test_db.execute("DELETE FROM crls")
    response = client.get(endpoint)
    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["total_crls"] == 0


def test_missing_summaries_are_unhealthy(client, test_db):
    test_db.execute("DELETE FROM crl_summaries")
    assert client.get("/health").status_code == 503


def test_database_error_is_http_503(client):
    with patch("app.main.get_db", side_effect=duckdb.IOException("Cannot read database")):
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["database"] == "error"


async def test_api_startup_refuses_empty_database(test_db):
    from app.main import app, lifespan

    test_db.execute("DELETE FROM crl_summaries")
    with patch("app.main.init_db"), patch("app.main.get_db", return_value=test_db):
        with pytest.raises(RuntimeError, match="refusing to serve"):
            async with lifespan(app):
                pytest.fail("An empty database reached serving state")


@pytest.mark.parametrize("failure", [None, "empty", "stale", "no_items", "wrong_total"])
def test_deployment_check_requires_expected_data(failure):
    expected = {"total_crls": 458, "total_summaries": 457, "last_data_update": "2026-10-31"}
    health = dict(expected, status="healthy")
    listing = {"total": 458, "items": [{"id": "letter"}]}
    if failure == "empty":
        health["total_crls"] = 0
    elif failure == "stale":
        health["last_data_update"] = "2026-10-30"
    elif failure == "no_items":
        listing["items"] = []
    elif failure == "wrong_total":
        listing["total"] = 0

    def respond(request):
        return httpx.Response(200, json=health if request.url.path == "/health" else listing)

    with httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(respond)) as client:
        assert deployment_matches(client, expected) is (failure is None)
