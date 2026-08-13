"""
A short example you can run as it is.

It talks to a public NETIO demo device, so you do not need your own hardware.
To use your own device, change URL and AUTH below.
"""

from Netio import Netio

URL = 'http://powerpdu-8qs.netio-products.com/netio.json'
AUTH = ('netio', 'netio')

# For your own device over HTTPS, add a certificate or switch the check off:
#   n = Netio(URL, auth_rw=AUTH, verify='/path/to/cert.pem')
#   n = Netio(URL, auth_rw=AUTH, verify=False)
n = Netio(URL, auth_rw=AUTH, timeout=10)

print(n)  # <Netio PowerPDU-EB [24A42C3992EB]>
print(f'outputs: {n.NumOutputs}, inputs: {n.NumInputs}')

# Read every output. Devices that do not measure power leave those fields empty,
# so always check for None before using them.
for output in n.get_outputs():
    state = 'on' if output.State == 1 else 'off'
    load = f'{output.Load} W' if output.Load is not None else 'not measured'
    print(f'  output {output.ID}: {state:3s}  {load:12s}  {output.Name}')

# Read a single output. Outputs are counted from 1.
first = n.get_output(1)

# Switch output 1 over and then put it back the way it was.
n.set_output(1, Netio.ACTION.TOGGLE)
n.set_output(1, Netio.ACTION.ON if first.State == 1 else Netio.ACTION.OFF)

# Several outputs at once. There is no delay between them, so be careful with
# heavy loads.
n.set_outputs({1: Netio.ACTION.NOCHANGE, 2: Netio.ACTION.NOCHANGE})

# Inputs are read the same way as outputs, but they cannot be switched. Only
# some models have them, and the list is empty on the models that do not.
# Temperature and humidity are empty unless a sensor is connected.
for input in n.get_inputs():
    contact = 'closed' if input.State == 1 else 'open'
    pulses = f'{input.S0Counter:>8} pulses' if input.S0Counter is not None else 'no counter'
    temperature = f'{input.TemperatureC} C' if input.TemperatureC is not None else 'no sensor'
    print(f'  input {input.ID}: {contact:6s}  {pulses}  {temperature:10s}  {input.Name}')
