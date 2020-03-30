import collections
import requests
import logging
import json
from enum import IntEnum
from typing import List


class CommunicationError(Exception):
    """Communication with Device failed"""


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

    def _get_ouputs(self) -> List[ACTION]:
        """Return sorted list of all outputs in format of self.OUTPUT"""
        raise NotImplementedError("The function has to be implemented")

    def _set_state(self, id: int, action: ACTION) -> None:
        raise NotImplementedError("The function has to be implemented")

    def get_output(self, id: int) -> OUTPUT:
        response = self._get_ouputs()
        return list(response)[id]

    def set_output(self, id: int, action: int = ACTION.NOCHANGE) -> None:
        if self._write_access:
            self._set_state(id, action)
        else:
            raise Exception("cannot write, without write access")

    def __repr__(self):
        return f"<Netio {self.DeviceName} [{self.SerialNumber}]>"


class JsonDevice(Device):
    def __init__(self, url, auth_r=None, auth_rw=None):
        self._url = url

        # read-write can do read, so we don't need read-only permission
        if auth_rw:
            self._user = auth_rw[0]
            self._pass = auth_rw[1]
            _write_access = True
        elif auth_r:
            self._user = auth_r[0]
            self._pass = auth_r[1]
        else:
            raise TypeError("No auth provided.")

        # request information about the Device

        response = requests.get(self._url)

        json = response.json()

        self.NumOutputs = json["Agent"]["NumOutputs"]
        self.DeviceName = json["Agent"]["DeviceName"]
        self.SerialNumber = json["Agent"]["SerialNumber"]

    def _get_ouputs(self) -> list:
        """
        Send empty GET request to the device.
        Parse out the output states according to specification.
        """

        response = requests.get(self._url)

        if not response.ok:
            raise CommunicationError("Response is not ok.")

        outputs = list()

        for o_id in range(self.NumOutputs):
            output = response.json().get("Outputs")[o_id]
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

    def _set_state(self, id: int, action) -> None:

        body = {"Outputs": [{"ID": id, "Action": action}]}

        response = requests.post(self._url, data=json.dumps(body))

        if not response.ok:
            raise CommunicationError("Response is not ok.")

        # TODO verify reponse action
        response.json()
