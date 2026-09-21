import ipaddress

import pytest

from app import create_app
from app import routes


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        routes,
        "resolved_allowed_networks",
        [ipaddress.ip_network("127.0.0.0/8")],
    )
    return create_app().test_client()
