# Netio

Python bindings and a command line tool for NETIO Products power sockets.

Works with firmware 5.x (JSON API 2.6) and with older 3.x and 4.x devices.
Needs Python 3.11 or newer.

```bash
pip install Netio --upgrade
```

With poetry or uv instead of pip:

```bash
poetry add Netio        # as a project dependency
uv add Netio            # as a project dependency
uv tool install Netio   # just the Netio command, globally
```

Log in to your device and switch on the JSON API. Allow write access if you
want to switch outputs and not just read them.

![Configure Interface](docs/NetioIface.png)

# API

```python
from Netio import Netio

n = Netio('http://powerpdu-8qs.netio-products.com/netio.json', auth_rw=('netio', 'netio'))
```

Pass `auth_rw` for a user that may switch outputs, or `auth_r` for one that may
only read — switching with `auth_r` raises `AuthError` before anything is sent
to the device. `timeout=10` sets how long to wait for a reply.

## Outputs

```pydocstring
>>> n.set_output(1, n.ACTION.ON)   # ON OFF TOGGLE SHORT_ON SHORT_OFF NOCHANGE IGNORED
>>> n.set_outputs({1: n.ACTION.ON, 2: n.ACTION.OFF})
>>> n.get_output(1)
Device.OUTPUT(ID=1, Name='Dream Machine', State=1, Action=<ACTION.IGNORED: 6>, Delay=5000, Current=0, PowerFactor=1.0, Phase=0.0, Energy=43078, EnergyNR=154263, ReverseEnergy=646, ReverseEnergyNR=66452, Load=0)
```

Outputs are counted from 1. `get_outputs()` returns them all, and `get_output`
raises `UnknownOutputId` for a number the device does not have.

**Not every device measures power.** The PowerCable 2PZ and the PowerPDU 4PS
report only `ID`, `Name`, `State`, `Action` and `Delay`, and leave the rest
`None`. It can also differ per output: on the 8QS above only output 1 measures.

## Inputs

Some models, such as the PowerDIN 4PZ, have digital inputs. They work like
outputs but are read only: `get_inputs()`, `get_input(id)`, `NumInputs`.

```pydocstring
>>> n.get_input(1)
Device.INPUT(ID=1, Name='Input 1', State=0, S0Counter=0, TemperatureC=None, TemperatureF=None, Humidity=None)
```

`State` is 0 for an open contact and 1 for a closed one. Temperature and
humidity need a sensor: the device sends `999` when none is connected, and this
package reports that as `None`.

## HTTPS

Pass the device's certificate as `verify`, or `verify=False` to skip the check.
Reaching the device by IP address always needs `verify=False`, because the
certificate will not match the address.

```python
n = Netio('https://netio.local/netio.json', auth_rw=('admin', 'password'), verify='/path/to/cert.pem')
```

To get a certificate: set the hostname and domain under `Settings->Network
Configuration`, then *Generate new certificate* under `Settings->Security
Settings`, and
[download it from your browser](https://docs.digicert.com/manage-certificates/client-certificates-guide/manage-your-personal-id-certificate/windows-export-your-personal-id-certificate/).

# CLI

```
Netio [-u USER] [-p PASSWORD] [-c CFG] [-C] [--no-cert-warning] [-v] DEVICE COMMAND
```

| Command | Aliases | Does |
|---|---|---|
| `get` | `GET G g` | print output state |
| `set` | `SET S s` | switch outputs |
| `info` | `INFO I i` | print everything the device reports about itself |
| `inputs` | `INPUTS DI di` | print input state |

`Netio DEVICE COMMAND --help` describes each one.

## GET and INPUTS

Both print a table of everything, or of the ids you name. `None` is a value the
device does not report.

```
$ NETIO_PASSWORD=netio Netio -u netio http://powerpdu-8qs.netio-products.com/netio.json GET
id      State   Action  Delay   Current PFactor Load    Energy  Name
1       1       IGNORED 5000    0       1.0     0       43078   Dream Machine
2       1       IGNORED 5000    None    None    None    None    Power output 2

$ NETIO_PASSWORD=netio Netio -u netio http://powerdin-4pz.netio-products.com:22888/netio.json DI 1
id      State   S0Counter       TempC   TempF   Humidity        Name
1       0       0               None    None    None            Input 1
```

`--no-header` drops the header row, `--delimiter ';'` changes the separator, and
`--action-int` prints the action as a number. Asking for the inputs of a device
that has none exits 1 with a message.

## SET

Takes pairs of output number and action, or `ALL` in place of a number. Exits
non zero when the request does not succeed.

```
$ NETIO_PASSWORD=secretPass Netio -u write http://netio.local SET 1 ON 2 OFF
$ NETIO_PASSWORD=secretPass Netio -u write http://netio.local SET ALL TOGGLE
```

**Warning**: switching all outputs at once leaves no delay between them. With
heavy loads that can spike the current and trip your breakers.

## INFO

Which sections appear depends on the model: no `GlobalMeasure` on devices that
do not measure power, no `Inputs` on devices without them. `Inputs`, `PAB`,
`Watchdogs` and `Rules` are lists, so their items are numbered.

```
$ Netio -u netio -p netio http://powerpdu-8qs.netio-products.com/netio.json INFO
Agent
   Model         8QS
   DeviceName    PowerPDU-EB
   SerialNumber  24A42C3992EB
   Version       5.3.1
   NumOutputs    8
   NumInputs     1
   ...
Inputs
   [1]
      ID            1
      Name          Input 1
      State         1
      S0Counter     1246811
      ...
```

## Credentials

Passing the password on the command line lets anyone on the system see it. Use
`NETIO_USER` and `NETIO_PASSWORD` instead, or a config file given with
`--config` or `NETIO_CONFIG` — see [netio.example.ini](examples/netio.example.ini).

Each value is looked up in this order: command line argument, environment
variable, the config file section for that device, its `DEFAULT` section, built
in default.

# Trying it out

NETIO offers public demo devices, so you do not need your own hardware. These 6
were up when last checked (2026-08-12), all on firmware 5.3.1, and accept
`netio`/`netio` or `demo`/`demo`. They are real devices other people are also
using, and no sensor is connected to any of their inputs.

| Device | URL | Inputs |
|---|---|---|
| PowerPDU 8QS | `http://powerpdu-8qs.netio-products.com/netio.json` | 1 |
| PowerDIN 4PZ | `http://powerdin-4pz.netio-products.com:22888/netio.json` | 2 |
| PowerCable 2KZ | `http://powercable-2kz.netio-products.com:22888/netio.json` | 1 |
| PowerCable 2PZ | `http://powercable-2pz.netio-products.com/netio.json` | none |
| PowerPDU 4PS | `http://powerpdu-4ps.netio-products.com:22888/netio.json` | none |
| PowerBOX 4KX | `http://powerbox-4kx.netio-products.com/netio.json` | none |

# Development

```bash
poetry install
poetry run pytest          # offline tests, no network needed
poetry run pytest -m live  # tests against the demo devices above
```

The live tests switch output 1 of each demo device over and then put it back.
