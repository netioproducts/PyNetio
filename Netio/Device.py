import dataclasses
import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from enum import IntEnum

import requests

from Netio.exceptions import AuthError, CommunicationError, NetioException, UnknownInputId, UnknownOutputId

SENSOR_NOT_CONNECTED = 999
"""
Value the device sends for a measurement it cannot make.

A temperature or humidity input reports 999 when no sensor is connected or when
the sensor failed. `get_inputs` turns that into None, so an unread value looks
the same as a value the device does not report at all. `get_info` returns the
device's data untranslated, so 999 passes through there.
"""


class Device(ABC):
    """
    A NETIO device.

    A subclass talks to the hardware and provides `init`, `get_info`,
    `get_outputs`, `get_inputs` and `_set_outputs`. Everything that does not
    depend on the protocol lives here: picking single outputs out of the list,
    and refusing to write without write access.
    """

    class ACTION(IntEnum):
        """
        Device output action
        https://www.netio-products.com/files/NETIO-M2M-API-Protocol-JSON.pdf
        """

        OFF = 0
        ON = 1
        SHORT_OFF = 2
        SHORT_ON = 3
        TOGGLE = 4
        NOCHANGE = 5
        IGNORED = 6

    @dataclasses.dataclass
    class OUTPUT:
        """
        One power output of the device.

        A field is None when the device does not report it. Only some models
        measure power, and on some of those only the first output does.
        """

        ID: int
        """Output ID"""

        Name: str
        """Output name"""

        State: int
        """Output state, 0 for off and 1 for on"""

        Action: "Device.ACTION"
        """Last action carried out on the output"""

        Delay: int | None
        """[ms] Output delay for short On/Off"""

        Current: float | None
        """[mA] Electric current for the output"""

        PowerFactor: float | None
        """[-] TPF True Power Factor for the output"""

        Phase: float | None
        """[°] Phase for the specific power output"""

        Energy: float | None
        """[Wh] Counter of Energy consumed per output (resettable)"""

        EnergyNR: float | None
        """[Wh] Not Resettable counter of output consumed Energy"""

        ReverseEnergy: float | None
        """[Wh] Counter of Energy produced per output (resettable)"""

        ReverseEnergyNR: float | None
        """[Wh] Not Resettable counter of Reversed (produced) Energy"""

        Load: float | None
        """[W] Instantaneous load (power) for the specific power output"""

    @dataclasses.dataclass
    class INPUT:
        """
        One digital input (DI) of the device.

        Inputs can only be read. Which fields hold a value depends on what is
        connected: a field is None when the device does not send it, and also
        when it sends 999 to say that no sensor is connected.
        """

        ID: int
        """Input ID"""

        Name: str
        """Input name"""

        State: int
        """State of the contact, 0 for open and 1 for closed"""

        S0Counter: int | None
        """[-] Number of S0 pulses counted on the input (resettable)"""

        TemperatureC: float | None
        """[°C] Temperature, None when no sensor is connected"""

        TemperatureF: float | None
        """[°F] Temperature, None when no sensor is connected"""

        Humidity: float | None
        """[%] Relative humidity, None when no sensor is connected"""

    def __init__(self) -> None:
        self.DeviceName: str = ""
        self.SerialNumber: str = "Unknown"
        self.NumOutputs: int = 0
        self.NumInputs: int = 0
        self._write_access: bool = False

    @abstractmethod
    def init(self) -> None:
        """Read the device description and fill in DeviceName, NumOutputs and the rest"""

    @abstractmethod
    def get_info(self) -> dict:
        """Return everything the device reports about itself, without the output list"""

    @abstractmethod
    def get_outputs(self) -> list[OUTPUT]:
        """Return the state of every output"""

    @abstractmethod
    def get_inputs(self) -> list[INPUT]:
        """Return the state of every input. Empty on a device that has none."""

    @abstractmethod
    def _set_outputs(self, actions: dict[int, ACTION]) -> None:
        """
        Carry out one action per output.

        Called by `set_outputs`, which is what checks that we may write at all.
        """

    @staticmethod
    def _pick(
        items: Iterable[OUTPUT] | Iterable[INPUT],
        ids: Iterable[int],
        name: str,
        missing: type[NetioException],
    ) -> Iterator:
        """
        Yield the items with the given ids, in the order asked for.

        `missing` is raised for an id the device does not have, and `name` is
        the word used in that message.
        """
        by_id = {item.ID: item for item in items}
        for id in ids:
            try:
                yield by_id[id]
            except KeyError:
                raise missing(f"Invalid {name} ID '{id}'") from None

    def get_outputs_filtered(self, ids: Iterable[int]) -> Iterator[OUTPUT]:
        """Yield only the outputs with the given ids, in the order asked for"""
        return self._pick(self.get_outputs(), ids, "output", UnknownOutputId)

    def get_output(self, id: int) -> OUTPUT:
        """Get state of single socket by its id"""
        return next(self._pick(self.get_outputs(), [id], "output", UnknownOutputId))

    def get_inputs_filtered(self, ids: Iterable[int]) -> Iterator[INPUT]:
        """Yield only the inputs with the given ids, in the order asked for"""
        return self._pick(self.get_inputs(), ids, "input", UnknownInputId)

    def get_input(self, id: int) -> INPUT:
        """Get state of single input by its id"""
        return next(self._pick(self.get_inputs(), [id], "input", UnknownInputId))

    def set_outputs(self, actions: dict[int, ACTION]) -> None:
        """
        Set state of multiple outputs at once
        >>> n.set_outputs({1: n.ACTION.ON, 2:n.ACTION.OFF})
        """
        # TODO verify if socket id's are in range
        if not self._write_access:
            raise AuthError("cannot write, without write access")

        self._set_outputs(actions)

    def set_output(self, id: int, action: ACTION) -> None:
        self.set_outputs({id: action})

    def __repr__(self):
        return f"<Netio {self.DeviceName} [{self.SerialNumber}]>"


class JsonDevice(Device):
    """
    A device reached over the JSON API.

    https://www.netio-products.com/files/NETIO-M2M-API-Protocol-JSON.pdf
    """

    def __init__(self, url, auth_r=None, auth_rw=None, verify=None, skip_init=False, timeout=None):
        """
        :param url: url to device
        :param auth_r: tuple of (username, password) for read-only access
        :param auth_rw: tuple of (username, password) for read-write access
        :param verify: verify ssl certificate
        :param skip_init: skip initialization of device
        :param timeout: timeout for requests (in seconds)
        """
        super().__init__()

        self._url = url
        self._verify = verify
        self._timeout = timeout

        # read-write can do read, so we don't need read-only permission
        if auth_rw:
            self._user, self._pass = auth_rw
            self._write_access = True
        elif auth_r:
            self._user, self._pass = auth_r
        else:
            raise AuthError("No auth provided.")

        if not skip_init:
            self.init()

    def init(self) -> None:
        agent = self._request()["Agent"]

        self.DeviceName = agent["DeviceName"]
        self.SerialNumber = agent["SerialNumber"]
        self.NumOutputs = agent["NumOutputs"]
        # Devices without inputs still report NumInputs, but older firmware
        # leaves the field out.
        self.NumInputs = agent.get("NumInputs", 0)

    def get_info(self) -> dict:
        """
        Return everything the device reports about itself, without the output list.

        Which sections are present depends on the device. Devices that do not
        measure power leave out GlobalMeasure, and devices without inputs leave
        out Inputs.

        Values are returned as the device sent them: a measurement it cannot
        make is 999 here, not None.
        """
        r_json = self._request()
        r_json.pop("Outputs", None)
        return r_json

    def get_outputs(self) -> list[Device.OUTPUT]:
        return [
            self.OUTPUT(
                ID=output.get("ID"),
                Name=output.get("Name"),
                State=output.get("State"),
                Action=self.ACTION(output.get("Action")),
                Delay=output.get("Delay"),
                Current=output.get("Current"),
                PowerFactor=output.get("PowerFactor"),
                Phase=output.get("Phase"),
                Energy=output.get("Energy"),
                # Firmware up to 4.x spells these with an underscore
                EnergyNR=output.get("EnergyNR", output.get("Energy_NR")),
                ReverseEnergy=output.get("ReverseEnergy"),
                ReverseEnergyNR=output.get("ReverseEnergyNR", output.get("ReverseEnergy_NR")),
                Load=output.get("Load"),
            )
            for output in self._request().get("Outputs") or []
        ]

    def get_inputs(self) -> list[Device.INPUT]:
        return [
            self.INPUT(
                ID=input.get("ID"),
                Name=input.get("Name"),
                State=input.get("State"),
                S0Counter=input.get("S0Counter"),
                # Firmware up to 5.0.x spells this "TempertureC"
                TemperatureC=self._measured(input, "TemperatureC", "TempertureC"),
                TemperatureF=self._measured(input, "TemperatureF"),
                Humidity=self._measured(input, "Humidity"),
            )
            for input in self._request().get("Inputs") or []
        ]

    def _set_outputs(self, actions: dict[int, Device.ACTION]) -> None:
        self._request({"Outputs": [{"ID": id, "Action": action} for id, action in actions.items()]})

        # TODO verify response action

    @staticmethod
    def _measured(input: dict, *names: str) -> float | None:
        """
        Read a measured value from an input.

        The device sends 999 when no sensor is connected, which we report as
        None. Some firmware versions misspell the temperature field, so more
        than one name can be given.
        """
        for name in names:
            if name in input:
                value = input[name]
                return None if value == SENSOR_NOT_CONNECTED else value
        return None

    def _request(self, body: dict | None = None) -> dict:
        """Talk to the device. A body makes it a write, no body a read."""
        try:
            response = requests.request(
                "POST" if body is not None else "GET",
                self._url,
                data=json.dumps(body) if body is not None else None,
                auth=requests.auth.HTTPBasicAuth(self._user, self._pass),
                verify=self._verify,
                timeout=self._timeout,
            )
        except requests.exceptions.SSLError:
            raise AuthError("Invalid certificate") from None

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        """
        Parse JSON response according to
        https://www.netio-products.com/files/NETIO-M2M-API-Protocol-JSON.pdf
        """

        if response.status_code == 400:
            raise CommunicationError("Control command syntax error")

        if response.status_code == 401:
            raise AuthError("Invalid Username or Password")

        if response.status_code == 403:
            raise AuthError("Insufficient permissions to write")

        if not response.ok:
            raise CommunicationError("Communication with device failed")

        try:
            return response.json()
        except ValueError:
            raise CommunicationError("Response does not contain valid json") from None
