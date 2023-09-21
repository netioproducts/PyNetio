import pytest

from Netio.Device import Device


@pytest.fixture
def device():
    return Device("https://")


def test_get_output(device, requests_mock):
    raise NotImplementedError()
