import pytest

from Netio import Netio

ONLINE_DEMOS = [
    ("http://powerpdu-8qs.netio-products.com/netio.json", ("netio", "netio")),
    ("http://netio-4c.netio-products.com:8080/netio.json", ("", "")),
    #    ("http://powerdin-4pz.netio-products.com:22888/netio.json", ("netio", "netio")),  # json not enabled
    ("http://powercable-2kz.netio-products.com/netio.json", ("netio", "netio")),
    ("http://powercable-2pz.netio-products.com/netio.json", ("netio", "netio")),
    ("http://pc-rest.netio-products.com:22888/netio.json", ("netio", "netio")),
    ("http://powerpdu-4ps.netio-products.com:22888/netio.json", ("netio", "netio")),
    ("http://powerbox-3px.netio-products.com:22888/netio.json", ("netio", "netio")),
    ("http://powerbox-4kx.netio-products.com/netio.json", ("netio", "netio")),
    # ("http://pc-mqtt.netio-products.com:22888/netio.json", ("netio", "netio")),  # Obsolete
    # ("http://pc-modbus.netio-products.com:22888/netio.json", ("netio", "netio")),  # Obsolete
    # ("http://netio-4all.netio-products.com/netio.json", ("netio", "netio")),  # Obsolete
    # ("http://netio-4.netio-products.com/netio.json", ("netio", "netio")),  # Obsolete
]


def ids(param):
    return param[0].split(".")[0].split("/")[-1]


@pytest.fixture
def netio_device(request):
    url, auth = request.param
    return Netio(url, auth_rw=auth, timeout=5)


@pytest.mark.parametrize("netio_device", ONLINE_DEMOS, indirect=True, ids=ids)
def test_get_output(netio_device: Netio):
    print(netio_device)
    netio_device.get_outputs()
    netio_device.set_output(1, 0)
    netio_device.set_output(1, netio_device.ACTION.ON)
    netio_device.get_output(1)
