from Netio import Netio

n = Netio('https://192.168.137.227/netio.json', auth_rw=('admin', 'superSecret'), verify=False)

print(n.get_output(3))
print(n.set_output(2, Netio.ACTION.TOGGLE))
