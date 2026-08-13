import json
from pathlib import Path

import pytest

from Netio import Netio

FIXTURES = Path(__file__).parent / "fixtures"

URL = "http://device.example.com/netio.json"

# Demo devices offered by NETIO.
DEMO_DEVICES = [
    "http://powerpdu-8qs.netio-products.com/netio.json",
    "http://powerdin-4pz.netio-products.com:22888/netio.json",
    "http://powercable-2kz.netio-products.com:22888/netio.json",
    "http://powercable-2pz.netio-products.com/netio.json",
    "http://powerpdu-4ps.netio-products.com:22888/netio.json",
    "http://powerbox-4kx.netio-products.com/netio.json",
]

DEMO_AUTH = ("netio", "netio")


def load_response(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """
    Hide the NETIO_ environment variables from the tests.
    """
    for name in ("NETIO_USER", "NETIO_PASSWORD", "NETIO_CONFIG"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def response_8qs() -> dict:
    return load_response("powerpdu_8qs")


@pytest.fixture
def response_2pz() -> dict:
    return load_response("powercable_2pz")


@pytest.fixture
def response_4pz() -> dict:
    """A PowerDIN 4PZ, the demo device with two inputs."""
    return load_response("powerdin_4pz")


@pytest.fixture
def make_device(requests_mock):
    """
    Build a Netio device that talks to a mocked response instead of a real one.

    >>> device = make_device(response_8qs)
    """

    def _make(response: dict, auth_rw=("user", "pass"), **kwargs) -> Netio:
        requests_mock.get(URL, json=response)
        return Netio(URL, auth_rw=auth_rw, **kwargs)

    return _make
