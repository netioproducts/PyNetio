from Netio import Netio
n = Netio('http://192.168.137.174/netio.json', auth_rw=('admin', 'adminadmin'))

print(n.get_output(3))
print(n.set_output(2, Netio.ACTION.TOGGLE))
