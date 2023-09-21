import dataclasses
import json
from abc import abstractmethod, ABC
from enum import IntEnum
from typing import Dict, List

import requests

from Netio.exceptions import CommunicationError, AuthError, UnknownOutputId


class Device(ABC):
    """
    Template device with simple api. Provide _get_outputs and _set_outputs functions
    """

    _write_access = False

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

    DeviceName: str = ""
    SerialNumber: str = "Unknown"
    NumOutputs: int = 0

    @dataclasses.dataclass
    class OUTPUT:
        ID: int
        """Output ID"""

        Name: str
        """Output name"""

        State: int
        """Output state"""

        Action: "Device.ACTION"
        """"""

        Delay: int
        """[ms] Output delay for short On/Off"""

        Current: float
        """[mA] Electric current for the output"""

        PowerFactor: float
        """[-] TPF True Power Factor for the output"""

        Phase: float
        """[°] Phase for the specific power output"""

        Energy: float
        """[Wh] Counter of Energy consumed per output (resettable)"""

        Energy_NR: float
        """[Wh] Not Resettable counter of output consumed Energy"""

        ReverseEnergy: float
        """[Wh] Counter of Energy produced per output (resettable)"""

        ReverseEnergy_NR: float
        """[Wh] Not Resettable counter of Reversed (produced) Energy"""

        Load: float
        """[W] Instantaneous load (power) for the specific power output"""

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def _get_outputs(self) -> List[OUTPUT]:
        """Return list of all outputs in format of self.OUTPUT"""

    @abstractmethod
    def _set_outputs(self, actions: Dict[int, ACTION]) -> None:
        """Set multiple outputs."""

    def get_outputs(self) -> List[OUTPUT]:
        """Returns list of available sockets and their state"""
        return self._get_outputs()

    def get_outputs_filtered(self, ids):
        """ """
        outputs = self.get_outputs()
        for i in ids:
            try:
                yield next(filter(lambda output: output.ID == i, outputs))
            except StopIteration:
                raise UnknownOutputId("Invalid output ID")

    def get_output(self, id: int) -> OUTPUT:
        """Get state of single socket by its id"""
        outputs = self.get_outputs()
        try:
            return next(filter(lambda output: output.ID == id, outputs))
        except StopIteration:
            raise UnknownOutputId("Invalid output ID")

    def set_outputs(self, actions: Dict[int, ACTION]) -> None:
        """
        Set state of multiple outputs at once
        >>> n.set_outputs({1: n.ACTION.ON, 2:n.ACTION.OFF})
        """
        # TODO verify if socket id's are in range
        if self._write_access:
            self._set_outputs(actions)
        else:
            raise AuthError("cannot write, without write access")

    def set_output(self, id: int, action: ACTION) -> None:
        self.set_outputs({id: action})

    def __repr__(self):
        return f"<Netio {self.DeviceName} [{self.SerialNumber}]>"


class JsonDevice(Device):
    def __init__(
        self, url, auth_r=None, auth_rw=None, verify=None, skip_init=False, timeout=None
    ):
        """
        :param url: url to device
        :param auth_r: tuple of (username, password) for read-only access
        :param auth_rw: tuple of (username, password) for read-write access
        :param verify: verify ssl certificate
        :param skip_init: skip initialization of device
        :param timeout: timeout for requests (in seconds)
        """
        self._url = url
        self._verify = verify
        self._timeout = timeout

        # read-write can do read, so we don't need read-only permission
        if auth_rw:
            self._user = auth_rw[0]
            self._pass = auth_rw[1]
            self._write_access = True
        elif auth_r:
            self._user = auth_r[0]
            self._pass = auth_r[1]
        else:
            raise AuthError("No auth provided.")

        if not skip_init:
            self.init()

    def init(self):
        # request information about the Device
        r_json = self._get()

        self.NumOutputs = r_json["Agent"]["NumOutputs"]
        self.DeviceName = r_json["Agent"]["DeviceName"]
        self.SerialNumber = r_json["Agent"]["SerialNumber"]

    def get_info(self):
        r_json = self._get()
        r_json.pop("Outputs")
        return r_json

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
            rj = response.json()
        except ValueError:
            raise CommunicationError("Response does not contain valid json")

        return rj

    def _post(self, body: dict) -> dict:
        try:
            response = requests.post(
                self._url,
                data=json.dumps(body),
                auth=requests.auth.HTTPBasicAuth(self._user, self._pass),
                verify=self._verify,
                timeout=self._timeout,
            )
        except requests.exceptions.SSLError:
            raise AuthError("Invalid certificate")

        return self._parse_response(response)

    def _get(self) -> dict:
        try:
            response = requests.get(
                self._url,
                auth=requests.auth.HTTPBasicAuth(self._user, self._pass),
                verify=self._verify,
                timeout=self._timeout,
            )
        except requests.exceptions.SSLError:
            raise AuthError("Invalid certificate")

        return self._parse_response(response)

    def _get_outputs(self) -> List[Device.OUTPUT]:
        """
        Send empty GET request to the device.
        Parse out the output states according to specification.
        """

        r_json = self._get()

        outputs = list()

        for output in r_json.get("Outputs"):
            state = self.OUTPUT(
                ID=output.get("ID", None),
                Name=output.get("Name", None),
                State=output.get("State", None),
                Action=self.ACTION(output.get("Action")),
                Delay=output.get("Delay", None),
                Current=output.get("Current", None),
                PowerFactor=output.get("PowerFactor", None),
                Phase=output.get("Phase", None),
                Energy=output.get("Energy", None),
                Energy_NR=output.get("Energy_NR", None),
                ReverseEnergy=output.get("ReverseEnergy", None),
                ReverseEnergy_NR=output.get("ReverseEnergy_NR", None),
                Load=output.get("Load", None),
            )
            outputs.append(state)
        return outputs

    def _set_outputs(self, actions: dict) -> dict:
        outputs = []
        for id, action in actions.items():
            outputs.append({"ID": id, "Action": action})

        body = {"Outputs": outputs}

        return self._post(body)

        # TODO verify response action
