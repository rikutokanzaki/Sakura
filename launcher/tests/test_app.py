import builtins
import json
from unittest.mock import mock_open

from app import routes


def test_index_returns_launcher_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Blossom launcher" in response.data


def test_openresty_logs_are_flattened(client, monkeypatch):
    log_data = json.dumps(
        {"request": {"method": "GET"}, "tags": ["web", "json"]}
    )
    monkeypatch.setattr(builtins, "open", mock_open(read_data=log_data + "\n"))

    response = client.get("/api/logs/openresty")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "request.method": "GET",
            "tags[0]": "web",
            "tags[1]": "json",
        }
    ]


def test_missing_log_returns_not_found(client, monkeypatch):
    def raise_not_found(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(routes, "open", raise_not_found, raising=False)

    response = client.get("/api/logs/paramiko")

    assert response.status_code == 404
    assert response.get_json() == {"error": "paramiko.log not found"}


def test_requests_from_disallowed_network_are_rejected(client, monkeypatch):
    monkeypatch.setattr(routes, "resolved_allowed_networks", [])

    response = client.get("/")

    assert response.status_code == 403
