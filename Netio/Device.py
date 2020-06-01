import collections
from abc import abstractmethod

import requests
import logging
import json
from enum import IntEnum
from typing import Dict, List

from Netio.exceptions import CommunicationError, AuthError, UnknownOutputId


class Device(object):
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

    DeviceName: str = ''
    SerialNumber: str = 'Unknown'
    NumOutputs: int = 0

    OUTPUT = collections.namedtuple("Output", "ID Name State Action Delay Current PowerFactor Load Energy")

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def _get_outputs(self) -> List[OUTPUT]:
        """ Return list of all outputs in format of self.OUTPUT """

    @abstractmethod
    def _set_outputs(self, actions: Dict[int, ACTION]) -> None:
        """ Set multiple outputs. """

    def get_outputs(self) -> List[OUTPUT]:
        """ Returns list of available sockets and their state"""
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
        """ Get state of single socket by its id """
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
    def __init__(self, url, auth_r=None, auth_rw=None, verify=None, skip_init=False):
        self._url = url
        self._verify = verify

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
        r_json.pop('Outputs')
        return r_json

    @staticmethod
    def _parse_response(response: requests.Response) -> dict:
        """
        Parse JSON response according to
        https://www.netio-products.com/files/NETIO-M2M-API-Protocol-JSON.pdf
        """

        try:
            rj = response.json()
        except ValueError:
            raise CommunicationError("Response does not contain valid json")

        if response.status_code == 400:
            raise CommunicationError('Control command syntax error')

        if response.status_code == 401:
            raise AuthError('Invalid Username or Password')

        if response.status_code == 403:
            raise AuthError('Insufficient permissions to write')

        if not response.ok:
            raise CommunicationError("Communication with device failed")
        return rj

    def _post(self, body: dict) -> dict:
        try:
            response = requests.post(
                self._url,
                data=json.dumps(body),
                auth=requests.auth.HTTPBasicAuth(self._user, self._pass),
                verify=self._verify,
            )
        except requests.exceptions.SSLError:
            raise AuthError("Invalid certificate")

        return self._parse_response(response)

    def _get(self) -> dict:
        try:
            response = requests.get(
                self._url, auth=requests.auth.HTTPBasicAuth(self._user, self._pass), verify=self._verify
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

        for output in r_json.get('Outputs'):
            state = self.OUTPUT(
                ID=output["ID"],
                Name=output["Name"],
                State=output["State"],
                Action=self.ACTION(output["Action"]),
                Delay=output["Delay"],
                Current=output["Current"],
                PowerFactor=output["PowerFactor"],
                Load=output["Load"],
                Energy=output["Energy"],
            )
            outputs.append(state)
        return outputs

    def _set_outputs(self, actions: dict) -> dict:
        outputs = []
        for id, action in actions.items():
            outputs.append({'ID': id, 'Action': action})

        body = {"Outputs": outputs}

        return self._post(body)

        # TODO verify response action
