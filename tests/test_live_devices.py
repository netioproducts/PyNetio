"""
Tests that talk to the real NETIO demo devices over the internet.

These are skipped by default, because they need a working internet connection
and because the demo devices are not always up. Run them with:

    pytest -m live

The tests switch output 1 of each demo device off and on again.
"""

import time

import pytest

from Netio import Netio

from .conftest import DEMO_AUTH, DEMO_DEVICES

pytestmark = pytest.mark.live

# how long to wait for the device to carry out a switch, in seconds
SWITCH_DELAY = 2


def device_name(url: str) -> str:
    """Turn a demo URL into a short name, so test output stays readable."""
    return url.split('//')[1].split('.')[0]


@pytest.fixture(params=DEMO_DEVICES, ids=device_name)
def demo_device(request) -> Netio:
    return Netio(request.param, auth_rw=DEMO_AUTH, timeout=10)


def test_read_and_switch_a_real_device(demo_device: Netio):
    """Read the device, switch output 1 over, and put it back the way it was."""
    assert demo_device.SerialNumber != 'Unknown'
    assert demo_device.NumOutputs > 0

    info = demo_device.get_info()
    assert 'Outputs' not in info
    assert info['Agent']['Version'].startswith('5.'), 'expected firmware 5.x'

    outputs = demo_device.get_outputs()
    assert len(outputs) == demo_device.NumOutputs
    assert [output.ID for output in outputs] == list(range(1, demo_device.NumOutputs + 1))

    was_on = demo_device.get_output(1).State == 1
    try:
        demo_device.set_output(1, Netio.ACTION.OFF if was_on else Netio.ACTION.ON)
        time.sleep(SWITCH_DELAY)
        assert demo_device.get_output(1).State == (0 if was_on else 1), 'output did not switch'
    finally:
        # leave the demo device the way we found it
        demo_device.set_output(1, Netio.ACTION.ON if was_on else Netio.ACTION.OFF)
