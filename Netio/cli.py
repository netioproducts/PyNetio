#!/usr/bin/env python3
"""
Netio Command line interface
"""

import argparse
import configparser
from typing import List

import pkg_resources
import requests
import os
import sys
from urllib.parse import urlparse, urlunparse

from .exceptions import NetioException
from . import Netio


def str2action(s: str) -> Netio.ACTION:
    """Parse Device.ACTION, either by name or by integer representation """
    try:
        return Netio.ACTION[s.upper()]
    except KeyError or AttributeError:
        try:
            return Netio.ACTION(int(s))
        except ValueError:
            raise argparse.ArgumentTypeError(f"{s!r} is not a valid {Netio.ACTION.__name__}")


# all Device.ACTION choices, including INT
ACTION_CHOICES = [e.value for e in Netio.ACTION] + [e.name for e in Netio.ACTION]

EPILOG = """
Report bugs to: averner@netio.eu
project repository and documentation: https://github.com/netioproducts/PyNetio
released under MIT license by NETIO Products a.s.
"""


def get_arg(arg, config, name, env_name, section, default):
    """
    argument is looked up in this order:
     1. argument itself
     2. specified section
     3. DEFAULT section
     4. param default
    """
    if arg == default:
        if env_name and env_name in os.environ:
            return os.environ[env_name]
        if section in config.sections():
            return config[section].get(name, config['DEFAULT'].get(name, default))
    return arg


def get_ids(id: str, max_id: int) -> List[int]:
    if id.isdecimal() and int(id) in range(1, max_id + 1):
        return [int(id)]
    elif id.lower() == 'all':
        return list(range(1, max_id + 1))
    else:
        raise NetioException(f"Invalid output ID '{id}', valid range is {1}-{max_id} or 'ALL'")


def load_config(args):
    """ Load configuration file and other other configs """

    config = configparser.ConfigParser({'cert': 'True', 'user': '', 'password': '', 'no_cert_warning': ''})
    if not args.conf:
        args.conf = os.environ.get('NETIO_CONFIG')

    if args.conf:
        try:
            config.read(args.conf)
        except TypeError:
            raise NetioException('Failed reading config')

    u = urlparse(args.device)

    args.cert = get_arg(args.cert, config, 'cert', None, u.netloc, True)
    args.user = get_arg(args.user, config, 'user', 'NETIO_USERNAME', u.netloc, None)
    args.password = get_arg(args.password, config, 'password', 'NETIO_PASSWORD', u.netloc, None)
    args.no_cert_warning = get_arg(args.no_cert_warning, config, 'no_cert_warning', None, u.netloc, False)

    # resolve the path of cert relative to configuration path
    basedir = os.path.dirname(args.conf) if args.conf else os.path.dirname(os.path.curdir)
    args.cert = args.cert if isinstance(args.cert, bool) else os.path.join(basedir, args.cert)

    return args


def parse_args():
    parser = argparse.ArgumentParser(epilog=EPILOG)  # prog='netio')

    parser.add_argument('device', metavar='DEVICE', action='store', help='Netio device URL')

    parser.add_argument("-u", "--user", action="store", dest='user', metavar='U', help='M2M API username')
    parser.add_argument("-p", "--password", action="store", dest='password', metavar='P', help='M2M API password')

    parser.add_argument("-C", "--cert", action="store_false", dest='cert', default=True, help='HTTPS Certificate')
    parser.add_argument("-c", "--config", action="store", dest="conf", metavar='CFG', help='Configuration file')
    parser.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
    parser.add_argument(
        "--no-cert-warning",
        action="store_true",
        help="Disable warnings about certificate's subjectAltName versus commonName",
    )

    # TODO version from setup

    version = pkg_resources.require("Netio")[0].version
    parser.add_argument("--version", action="version", version=f"%(prog)s (version {version})")

    command_parser = parser.add_subparsers(metavar="COMMAND", help="device command", required=True)

    # GET command subparser
    get_parser = command_parser.add_parser("get", help="GET output state", aliases=['GET', 'G', 'g'])
    get_parser.add_argument('id', metavar='ID', nargs='?', default='ALL', help='Output ID. All if not specified')
    get_parser.set_defaults(func=command_get)
    get_parser.add_argument("-d", "--delimiter", action="store", dest="delim", default=";", help='')
    get_parser.add_argument("--no-header", action="store_true", help='don\'t print column description')
    get_parser.add_argument("--action-int", action="store_true", help='print action as integer')

    # SET command subparser
    set_parser = command_parser.add_parser("set", help="SET output state", aliases=['SET', 'S', 's'])
    set_parser.set_defaults(func=command_set)
    set_parser.add_argument('id', metavar='ID', help="Output ID. All to set action to all outputs at once")

    # TODO use argparse.Action so that we can display choices
    set_parser.add_argument(
        'action',
        metavar='ACTION',
        type=str2action,
        choices=ACTION_CHOICES,
        help=f"Output action. " f"Valid actions " f"are {[e.name for e in Netio.ACTION]}",
    )

    # INFO command subparser
    info_parser = command_parser.add_parser("info", help="show device info", aliases=['INFO', 'I', 'i'])
    info_parser.set_defaults(func=command_info)

    return parser.parse_args()


def main():
    """ Main entry point of the app """
    try:

        args = parse_args()
        args = load_config(args)

        if args.no_cert_warning:
            requests.packages.urllib3.disable_warnings()

        u = urlparse(args.device)
        u = u._replace(path='/netio.json') if not u.path else u  # no path specified

        # try to run the specified command, on fail print nice fail message
        device = Netio(urlunparse(u), auth_rw=(args.user, args.password), verify=args.cert, skip_init=True)
        args.func(device, args)
    except NetioException as e:
        print(e.args[0], file=sys.stderr)
    except Exception as e:
        print('Internal error: ', e, file=sys.stderr)


def command_set(device: Netio, args: argparse.Namespace) -> None:
    """ Set the output specified in args.id to args.action """

    device.init()

    ids = get_ids(args.id, device.NumOutputs)
    device.set_outputs(dict(zip(ids, [args.action] * device.NumOutputs)))


def command_get(device: Netio, args: argparse.Namespace) -> None:
    """ Print the state of the output and exit """

    # init because we need to know NumOutputs so we can generate id list for "ALL"
    # This initialization could be skipped, but that would require different handling for 'all' parameter
    device.init()

    ids = get_ids(args.id, device.NumOutputs)  # returns single or range
    outputs = list(device.get_outputs_filtered(ids))

    if not args.no_header:
        print('id', 'Name', 'State', 'Action', 'Delay', 'Current', 'PowerFactor', 'Load', 'Energy', sep=args.delim)
    for o in outputs:
        action = o.Action if not args.action_int else o.Action.value
        print(o.ID, o.Name, o.State, action, o.Delay, o.Current, o.PowerFactor, o.Load, o.Energy, sep=args.delim)


def command_info(device: Netio, args: argparse.Namespace) -> None:
    for key, data in device.get_info().items():
        print(key)
        for subkey, value in data.items():
            pad = 18 - len(subkey)
            print('  ', subkey, ' ' * pad, value)


if __name__ == "__main__":
    main()
