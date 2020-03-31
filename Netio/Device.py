import collections
import requests
import logging
import json
from enum import IntEnum
from typing import List

from Netio.exceptions import CommunicationError, AuthError


class Device(object):
    """
    Template device with simple api. Provide _get_ouputs and _set_state functions
    """

    _write_access = False

    class ACTION(IntEnum):
        OFF = 0
        ON = 1
        SHORT_OFF = 2
        SHORT_ON = 3
        TOGGLE = 4
        NOCHANGE = 5
        IGNORED = 6

    DeviceName: str
    SerialNumber: str
    NumOutputs: int

    OUTPUT = collections.namedtuple(
        "Output", "ID Name State Action Delay Current PowerFactor Load Energy"
    )

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("The function has to be implemented")

    def _get_ouputs(self) -> List[OUTPUT]:
        """Return sorted list of all outputs in format of self.OUTPUT"""
        raise NotImplementedError("The function has to be implemented")

    def _set_state(self, id: int, action: ACTION) -> None:
        raise NotImplementedError("The function has to be implemented")

    def get_output(self, id: int) -> OUTPUT:
        response = self._get_ouputs()
        return list(response)[id]

    def set_output(self, id: int, action: ACTION = ACTION.NOCHANGE) -> None:
        if self._write_access:
            self._set_state(id, action)
        else:
            raise AuthError("cannot write, without write access")

    def __repr__(self):
        return f"<Netio {self.DeviceName} [{self.SerialNumber}]>"


class JsonDevice(Device):
    def __init__(self, url, auth_r=None, auth_rw=None):
        self._url = url

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

        # request information about the Device
        r_json = self._get()

        self.NumOutputs = r_json["Agent"]["NumOutputs"]
        self.DeviceName = r_json["Agent"]["DeviceName"]
        self.SerialNumber = r_json["Agent"]["SerialNumber"]

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
            raise AuthError('Read only credentials used')

        if not response.ok:
            raise CommunicationError("Communication with device failed")
        return rj

    def _post(self, body: dict) -> dict:
        response = requests.post(self._url,
                                 data=json.dumps(body),
                                 auth=requests.auth.HTTPBasicAuth(self._user, self._pass))

        return self._parse_response(response)


    def _get(self) -> dict:
        response = requests.get(self._url, auth=requests.auth.HTTPBasicAuth(self._user, self._pass))
        return self._parse_response(response)


    def _get_ouputs(self) -> List[Device.OUTPUT]:
        """
        Send empty GET request to the device.
        Parse out the output states according to specification.
        """

        r_json = self._get()

        outputs = list()

        for o_id in range(self.NumOutputs):
            output = r_json.get("Outputs")[o_id]
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

    def _set_state(self, id: int, action) -> dict:

        body = {"Outputs": [{"ID": id, "Action": action}]}

        return self._post(body)

        # TODO verify response action
