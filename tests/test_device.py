"""Tests for the device class, using responses captured from real devices."""

import pytest

from Netio import Netio
from Netio.exceptions import (
    AuthError,
    CommunicationError,
    UnknownInputId,
    UnknownOutputId,
)

from .conftest import URL


def test_the_device_submodule_is_not_shadowed():
    """
    `Netio.Device` has to stay the module.

    Exporting the Device class from the package under the same name hides the
    submodule, and `Netio.Device.JsonDevice` then stops working.
    """
    import Netio as package
    import Netio.Device  # noqa: F401

    assert package.Device.JsonDevice is package.Netio


def test_read_a_device_that_measures_power(make_device, response_8qs):
    """
    Walk through reading a PowerPDU 8QS.

    On this device only output 1 reports power. Outputs 2 to 8 send nothing but
    ID, name, state, action and delay, so their power fields must come back
    empty instead of raising.
    """
    device = make_device(response_8qs)

    assert device.DeviceName == "PowerPDU-EB"
    assert device.SerialNumber == "24A42C3992EB"
    assert device.NumOutputs == 8

    outputs = device.get_outputs()
    assert [output.ID for output in outputs] == [1, 2, 3, 4, 5, 6, 7, 8]

    measured = device.get_output(1)
    assert measured.Name == "Dream Machine"
    assert measured.Action is Netio.ACTION.IGNORED
    assert measured.Energy == 43078
    # The device sends these as EnergyNR and ReverseEnergyNR, not Energy_NR.
    assert measured.EnergyNR == 154263
    assert measured.ReverseEnergyNR == 66452

    plain = device.get_output(2)
    assert plain.State == 1
    assert plain.Current is None
    assert plain.Energy is None


def test_read_a_device_without_power_measurement(make_device, response_2pz):
    """A PowerCable 2PZ leaves out GlobalMeasure completely."""
    device = make_device(response_2pz)

    assert device.NumOutputs == 2
    assert all(output.Load is None for output in device.get_outputs())

    info = device.get_info()
    assert "GlobalMeasure" not in info


def test_get_info_keeps_every_section_except_outputs(make_device, response_8qs):
    """
    Device info is everything the device says about itself, minus the outputs.

    Firmware 5.x sends PAB, Watchdogs and Rules as lists. Anything that
    reads this data has to cope with sections that are not name and value pairs.
    """
    info = make_device(response_8qs).get_info()

    assert "Outputs" not in info
    assert info["Agent"]["Version"] == "5.3.1"
    assert isinstance(info["Watchdogs"], list)


def test_asking_for_an_output_that_does_not_exist(make_device, response_2pz):
    device = make_device(response_2pz)

    with pytest.raises(UnknownOutputId):
        device.get_output(99)

    with pytest.raises(UnknownOutputId):
        list(device.get_outputs_filtered([1, 99]))


def test_switching_outputs_sends_the_expected_request(
    requests_mock, make_device, response_8qs
):
    """Setting outputs posts one entry per output, with the action as a number."""
    device = make_device(response_8qs)
    post = requests_mock.post(URL, json={})

    device.set_outputs({1: Netio.ACTION.ON, 3: Netio.ACTION.TOGGLE})

    assert post.last_request.json() == {
        "Outputs": [
            {"ID": 1, "Action": 1},
            {"ID": 3, "Action": 4},
        ]
    }

    device.set_output(2, Netio.ACTION.OFF)
    assert post.last_request.json() == {"Outputs": [{"ID": 2, "Action": 0}]}


def test_read_only_credentials_cannot_switch_outputs(requests_mock, response_8qs):
    """Read-only access must be refused before any request is sent."""
    requests_mock.get(URL, json=response_8qs)
    device = Netio(URL, auth_r=("reader", "pass"))

    with pytest.raises(AuthError):
        device.set_output(1, Netio.ACTION.ON)


def test_no_credentials_at_all_is_refused():
    with pytest.raises(AuthError):
        Netio(URL)


@pytest.mark.parametrize(
    "status, expected",
    [
        (400, CommunicationError),  # command syntax error
        (401, AuthError),  # wrong user or password
        (403, AuthError),  # not allowed to write
        (500, CommunicationError),  # anything else that went wrong
    ],
)
def test_error_replies_are_turned_into_exceptions(requests_mock, status, expected):
    requests_mock.get(URL, status_code=status, json={"errors": []})

    with pytest.raises(expected):
        Netio(URL, auth_rw=("user", "pass"))


def test_a_reply_that_is_not_json(requests_mock):
    """
    A device with the JSON API switched off answers with plain text.

    The status code is checked before the body is parsed, so this has to be a
    successful reply to reach the JSON parsing.
    """
    requests_mock.get(URL, status_code=200, text="<html>not json</html>")

    with pytest.raises(CommunicationError):
        Netio(URL, auth_rw=("user", "pass"))


def test_skip_init_does_not_talk_to_the_device(requests_mock):
    """The CLI builds the device first and connects later, so this must not fail."""
    requests_mock.get(URL, status_code=500)

    device = Netio(URL, auth_rw=("user", "pass"), skip_init=True)

    assert device.NumOutputs == 0
    assert device.NumInputs == 0
    assert not requests_mock.called


def test_read_the_inputs_of_a_device_that_has_them(make_device, response_4pz):
    """
    Walk through reading the two inputs of a PowerDIN 4PZ.

    No sensor is connected to either input, so the device sends 999 for the
    temperature and the humidity and we report nothing instead.
    """
    device = make_device(response_4pz)

    assert device.NumInputs == 2

    inputs = device.get_inputs()
    assert [input.ID for input in inputs] == [1, 2]

    first = device.get_input(1)
    assert first.Name == "Input 1"
    assert first.State == 0
    assert first.S0Counter == 0
    assert first.TemperatureC is None
    assert first.TemperatureF is None
    assert first.Humidity is None

    # the counter keeps its value, only measurements use 999
    assert device.get_input(2).S0Counter == 1


@pytest.mark.parametrize("field", ["TemperatureC", "TempertureC"])
def test_a_connected_sensor_reports_its_values(make_device, response_4pz, field):
    """
    Read an input that has a sensor on it.

    Firmware up to 5.0.x spells the field 'TempertureC', without the second
    'a'. Both spellings have to be understood, or the temperature is missing on
    whichever devices we fail to match.
    """
    sensor = {
        "ID": 1,
        "Name": "Temp_sensor",
        "State": 0,
        "S0Counter": 34,
        field: 26.3,
        "TemperatureF": 79.3,
        "Humidity": 47.5,
    }
    response_4pz["Inputs"] = [sensor]

    reading = make_device(response_4pz).get_input(1)

    assert reading.TemperatureC == 26.3
    assert reading.TemperatureF == 79.3
    assert reading.Humidity == 47.5


def test_a_device_without_inputs(make_device, response_2pz):
    """A PowerCable 2PZ has no inputs and sends no Inputs section at all."""
    device = make_device(response_2pz)

    assert device.NumInputs == 0
    assert device.get_inputs() == []


def test_asking_for_an_input_that_does_not_exist(make_device, response_4pz):
    device = make_device(response_4pz)

    with pytest.raises(UnknownInputId):
        device.get_input(99)

    with pytest.raises(UnknownInputId):
        list(device.get_inputs_filtered([1, 99]))
