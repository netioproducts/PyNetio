#!/usr/bin/env python3
"""
Netio Command line interface
"""

import argparse
import configparser
import os
import pkg_resources
import requests
import sys
import traceback

from . import Netio
from .exceptions import NetioException
from typing import List
from urllib.parse import urlparse, urlunparse


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
        if section and config.has_option(section, name):
            return config[section][name]
        return config['DEFAULT'].get(name, default)
    return arg


def get_ids(id_strs: List[str], num_outputs: int) -> List[int]:
    """
    Generate a list of integer IDs from list of strings.
    The list can either contain one string "ALL" or an individual IDs

    >> get_ids(["ALL"], 4)
    [1, 2, 3, 4]
    """
    all_ids = range(1, num_outputs + 1)
    all_outputs_mode = False
    individual_outputs_mode = False
    result = []

    for id_str in id_strs:
        if id_str.lower() == 'all':
            if individual_outputs_mode:
                raise NetioException("Expecting either individual outputs IDs or 'ALL'")
            all_outputs_mode = True
            result = list(all_ids)
        elif id_str.isdecimal() and int(id_str) in all_ids:
            if all_outputs_mode:
                raise NetioException("Expecting either individual outputs IDs or 'ALL'")
            individual_outputs_mode = True
            result.append(int(id_str))
        else:
            raise NetioException(f"Invalid output ID '{id_str}', valid range is {1}-{num_outputs + 1} or 'ALL'")

    return result


def get_output_actions(ids_and_actions, num_outputs):
    """
    Parse out pairs of ID + ACTION from iterable `ids_and_actions`
    parse 'all' keyword if present.
    input can't have combination of all and individual IDs

    return dictionary containing ID: ACTION pairs
    """
    max_id = num_outputs + 1
    all_ids = range(1, max_id)
    all_outputs_mode = False
    individual_outputs_mode = False
    result = {}

    if len(ids_and_actions) % 2 != 0:
        raise NetioException(f"Expecting ID ACTION pairs but got an odd number of arguments ({len(ids_and_actions)})")
    pairs = zip(ids_and_actions[::2], ids_and_actions[1::2])

    for pair in list(pairs):
        id_str, action_str = pair

        if id_str.lower() == "all":
            if individual_outputs_mode:
                raise NetioException("Expecting either individual outputs IDs or 'ALL'")
            all_outputs_mode = True
            action = str2action(action_str)
            result = dict(zip(all_ids, [action] * num_outputs))
        elif id_str.isdecimal() and int(id_str) in all_ids:
            if all_outputs_mode:
                raise NetioException("Expecting either individual outputs IDs or 'ALL'")
            individual_outputs_mode = True
            id = int(id_str)
            if id in result:
                raise NetioException("Multiple actions given for id '{}' but expecting only one".format(id))
            action = str2action(action_str)
            result[id] = action
        else:
            raise NetioException(f"Invalid output ID '{id_str}', valid range is {1}-{max_id} or 'ALL'")

    return result


def load_config(args):
    """ Load configuration file and other other configs """

    config = configparser.ConfigParser({'user': '', 'password': '', 'no_cert_warning': ''})
    if not args.conf:
        args.conf = os.environ.get('NETIO_CONFIG')

    if args.conf:
        try:
            with open(args.conf) as fp:
                config.read_file(fp, args.conf)
        except (TypeError, OSError, FileNotFoundError, configparser.Error) as e:
            raise NetioException(f'Failed reading config ({e.__class__.__name__})')

    # resolve the device alias
    if config.has_option(args.device, 'url'):
        args.device = config[args.device]['url']

    u = urlparse(args.device)

    args.cert = get_arg(args.cert, config, 'cert', None, u.netloc, True)
    args.user = get_arg(args.user, config, 'user', 'NETIO_USER', u.netloc, None)
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

    version = pkg_resources.require("Netio")[0].version
    parser.add_argument("--version", action="version", version=f"%(prog)s (version {version})")

    command_parser = parser.add_subparsers(metavar="COMMAND", help="device command", required=True)

    # GET command subparser
    get_parser = command_parser.add_parser("get", help="GET output state", aliases=['GET', 'G', 'g'])
    get_parser.add_argument('id', metavar='ID', nargs='*', default=['ALL'], help='Output ID. All if not specified')
    get_parser.set_defaults(func=command_get)
    get_parser.add_argument("-d", "--delimiter", action="store", dest="delim", default="\t", help='')
    get_parser.add_argument("--no-header", action="store_true", help='don\'t print column description')
    get_parser.add_argument("--action-int", action="store_true", help='print action as integer')

    # SET command subparser
    set_parser = command_parser.add_parser("set", help="SET output state", aliases=['SET', 'S', 's'])
    set_parser.set_defaults(func=command_set)
    # We are using a forged meta variable to get ID and action pairs into the
    # help. The actual result is still a list of individual parameters and
    # parsing the pairs is done later by get_output_actions.
    set_parser.add_argument("id_and_action", metavar="ID ACTION", nargs="+",
                            help=f"output ID and action pairs (valid actions: {[a.name for a in Netio.ACTION]})")

    # INFO command subparser
    info_parser = command_parser.add_parser("info", help="show device info", aliases=['INFO', 'I', 'i'])
    info_parser.set_defaults(func=command_info)

    return parser.parse_args()


def print_traceback(args, file=sys.stderr):
    """
    Print traceback if requested by argument '--verbose'. A traceback is also
    considered as requested if arguments have not been parsed yet (args are
    None).
    """
    if not args or (hasattr(args, "verbose") and args.verbose):
        traceback.print_exc(file=file)


def main():
    """ Main entry point of the app """
    args = None

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
        print_traceback(args)
        exit(1)
    except Exception as e:
        print('Internal error: ', e, file=sys.stderr)
        print_traceback(args)
        exit(1)


def command_set(device: Netio, args: argparse.Namespace) -> None:
    """ Set the output specified in args.id to args.action """

    device.init()

    actions = get_output_actions(args.id_and_action, device.NumOutputs)
    device.set_outputs(actions)


def command_get(device: Netio, args: argparse.Namespace) -> None:
    """ Print the state of the output and exit """

    # init because we need to know NumOutputs so we can generate id list for "ALL"
    # This initialization could be skipped, but that would require different handling for 'all' parameter
    device.init()

    ids = get_ids(args.id, device.NumOutputs)  # returns single or range
    outputs = list(device.get_outputs_filtered(ids))

    if not args.no_header:
        print('id', 'State', 'Action', 'Delay', 'Current', 'PFactor', 'Load', 'Energy', 'Name', sep=args.delim)
    for o in outputs:
        action = o.Action.name if not args.action_int else o.Action.value
        print(o.ID, o.State, action, o.Delay, o.Current, o.PowerFactor, o.Load, o.Energy, o.Name, sep=args.delim)


def command_info(device: Netio, args: argparse.Namespace) -> None:
    """ Print out all data from device info """
    for key, data in device.get_info().items():
        print(key)
        for subkey, value in data.items():
            pad = 18 - len(subkey)
            print('  ', subkey, ' ' * pad, value)


if __name__ == "__main__":
    main()
