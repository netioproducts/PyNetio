#!/usr/bin/env python3
"""
Netio Command line interface
"""

import argparse
import configparser
import os
import requests
import sys
import traceback

from . import Netio, __version__
from .exceptions import NetioException, UnknownInputId, UnknownOutputId
from typing import List
from urllib.parse import urlparse, urlunparse


def str2action(s: str) -> Netio.ACTION:
    """Parse Device.ACTION, either by name or by integer representation"""
    try:
        return Netio.ACTION[s.upper()]
    except (KeyError, AttributeError):
        try:
            return Netio.ACTION(int(s))
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"{s!r} is not a valid {Netio.ACTION.__name__}"
            )


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
     2. environment variable
     3. specified section
     4. DEFAULT section
     5. param default
    """
    if arg == default:
        if env_name and env_name in os.environ:
            return os.environ[env_name]
        if section and config.has_option(section, name):
            return config[section][name]
        return config["DEFAULT"].get(name, default)
    return arg


def get_ids(id_strs: List[str], count: int, name: str = "output") -> List[int]:
    """
    Generate a list of integer IDs from list of strings.
    The list can either contain one string "ALL" or an individual IDs

    `name` is the word used in error messages, so the same code can pick
    outputs and inputs.

    >> get_ids(["ALL"], 4)
    [1, 2, 3, 4]
    """
    if count == 0:
        raise NetioException(f"Device has no {name}s")

    all_ids = range(1, count + 1)
    all_mode = False
    individual_mode = False
    result = []

    for id_str in id_strs:
        if id_str.lower() == "all":
            if individual_mode:
                raise NetioException(f"Expecting either individual {name} IDs or 'ALL'")
            all_mode = True
            result = list(all_ids)
        elif id_str.isdecimal() and int(id_str) in all_ids:
            if all_mode:
                raise NetioException(f"Expecting either individual {name} IDs or 'ALL'")
            individual_mode = True
            result.append(int(id_str))
        else:
            raise NetioException(
                f"Invalid {name} ID '{id_str}', valid range is 1-{count} or 'ALL'"
            )

    return result


def get_output_actions(ids_and_actions, num_outputs):
    """
    Parse out pairs of ID + ACTION from iterable `ids_and_actions`
    parse 'all' keyword if present.
    input can't have combination of all and individual IDs

    return dictionary containing ID: ACTION pairs
    """
    all_ids = range(1, num_outputs + 1)
    all_mode = False
    individual_mode = False
    result = {}

    if len(ids_and_actions) % 2 != 0:
        raise NetioException(
            f"Expecting ID ACTION pairs but got an odd number of arguments ({len(ids_and_actions)})"
        )
    pairs = zip(ids_and_actions[::2], ids_and_actions[1::2])

    for pair in list(pairs):
        id_str, action_str = pair

        if id_str.lower() == "all":
            if individual_mode:
                raise NetioException("Expecting either individual output IDs or 'ALL'")
            all_mode = True
            action = str2action(action_str)
            result = dict.fromkeys(all_ids, action)
        elif id_str.isdecimal() and int(id_str) in all_ids:
            if all_mode:
                raise NetioException("Expecting either individual output IDs or 'ALL'")
            individual_mode = True
            id = int(id_str)
            if id in result:
                raise NetioException(
                    "Multiple actions given for id '{}' but expecting only one".format(
                        id
                    )
                )
            action = str2action(action_str)
            result[id] = action
        else:
            raise NetioException(
                f"Invalid output ID '{id_str}', valid range is 1-{num_outputs} or 'ALL'"
            )

    return result


def load_config(args):
    """Load configuration file and other other configs"""

    config = configparser.ConfigParser(
        {"user": "", "password": "", "no_cert_warning": ""}
    )
    if not args.conf:
        args.conf = os.environ.get("NETIO_CONFIG")

    if args.conf:
        try:
            with open(args.conf) as fp:
                config.read_file(fp, args.conf)
        except (TypeError, OSError, FileNotFoundError, configparser.Error) as e:
            raise NetioException(f"Failed reading config ({e.__class__.__name__})")

    # resolve the device alias
    if config.has_option(args.device, "url"):
        args.device = config[args.device]["url"]

    u = urlparse(args.device)

    args.cert = get_arg(args.cert, config, "cert", None, u.netloc, True)
    args.user = get_arg(args.user, config, "user", "NETIO_USER", u.netloc, None)
    args.password = get_arg(
        args.password, config, "password", "NETIO_PASSWORD", u.netloc, None
    )
    args.no_cert_warning = get_arg(
        args.no_cert_warning, config, "no_cert_warning", None, u.netloc, False
    )

    # resolve the path of cert relative to configuration path
    # an empty `cert =` in the config switches verification off
    basedir = (
        os.path.dirname(args.conf) if args.conf else os.path.dirname(os.path.curdir)
    )
    if not isinstance(args.cert, bool):
        args.cert = os.path.join(basedir, args.cert) if args.cert else False

    return args


def parse_args():
    parser = argparse.ArgumentParser(epilog=EPILOG)  # prog='netio')

    parser.add_argument(
        "device", metavar="DEVICE", action="store", help="Netio device URL"
    )

    parser.add_argument(
        "-u",
        "--user",
        action="store",
        dest="user",
        metavar="U",
        help="M2M API username",
    )
    parser.add_argument(
        "-p",
        "--password",
        action="store",
        dest="password",
        metavar="P",
        help="M2M API password",
    )

    parser.add_argument(
        "-C",
        "--cert",
        action="store_false",
        dest="cert",
        default=True,
        help="HTTPS Certificate",
    )
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        dest="conf",
        metavar="CFG",
        help="Configuration file",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="increase verbosity"
    )
    parser.add_argument(
        "--no-cert-warning",
        action="store_true",
        help="Disable warnings about certificate's subjectAltName versus commonName",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s (version {__version__})"
    )

    command_parser = parser.add_subparsers(metavar="COMMAND", help="device command")
    command_parser.required = True

    # options shared by the commands that print a table
    table_options = argparse.ArgumentParser(add_help=False)
    table_options.add_argument(
        "-d",
        "--delimiter",
        action="store",
        dest="delim",
        default="\t",
        help="column delimiter",
    )
    table_options.add_argument(
        "--no-header", action="store_true", help="don't print column description"
    )

    # GET command subparser
    get_parser = command_parser.add_parser(
        "get",
        help="GET output state",
        aliases=["GET", "G", "g"],
        parents=[table_options],
    )
    get_parser.add_argument(
        "id",
        metavar="ID",
        nargs="*",
        default=["ALL"],
        help="Output ID. All if not specified",
    )
    get_parser.set_defaults(func=command_get)
    get_parser.add_argument(
        "--action-int", action="store_true", help="print action as integer"
    )

    # SET command subparser
    set_parser = command_parser.add_parser(
        "set", help="SET output state", aliases=["SET", "S", "s"]
    )
    set_parser.set_defaults(func=command_set)
    # We are using a forged meta variable to get ID and action pairs into the
    # help. The actual result is still a list of individual parameters and
    # parsing the pairs is done later by get_output_actions.
    set_parser.add_argument(
        "id_and_action",
        metavar="ID ACTION",
        nargs="+",
        help=f"output ID and action pairs (valid actions: {[a.name for a in Netio.ACTION]})",
    )

    # INFO command subparser
    info_parser = command_parser.add_parser(
        "info", help="show device info", aliases=["INFO", "I", "i"]
    )
    info_parser.set_defaults(func=command_info)

    # INPUTS command subparser
    inputs_parser = command_parser.add_parser(
        "inputs",
        help="GET input state",
        aliases=["INPUTS", "DI", "di"],
        parents=[table_options],
    )
    inputs_parser.add_argument(
        "id",
        metavar="ID",
        nargs="*",
        default=["ALL"],
        help="Input ID. All if not specified",
    )
    inputs_parser.set_defaults(func=command_inputs)

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
    """Main entry point of the app"""
    args = None

    try:
        args = parse_args()
        args = load_config(args)

        if args.no_cert_warning:
            requests.packages.urllib3.disable_warnings()

        u = urlparse(args.device)
        u = u._replace(path="/netio.json") if not u.path else u  # no path specified

        # try to run the specified command, on fail print nice fail message
        device = Netio(
            urlunparse(u),
            auth_rw=(args.user, args.password),
            verify=args.cert,
            skip_init=True,
        )
        args.func(device, args)
    except NetioException as e:
        print(e.args[0], file=sys.stderr)
        print_traceback(args)
        sys.exit(1)
    except Exception as e:
        print("Internal error: ", e, file=sys.stderr)
        print_traceback(args)
        sys.exit(1)


def command_set(device: Netio, args: argparse.Namespace) -> None:
    """Set the output specified in args.id to args.action"""

    device.init()

    actions = get_output_actions(args.id_and_action, device.NumOutputs)
    device.set_outputs(actions)


def _print_table(header: tuple, rows: list, args: argparse.Namespace) -> None:
    """Print one row per item, with an optional header row"""
    if not args.no_header:
        print(*header, sep=args.delim)
    for row in rows:
        print(*row, sep=args.delim)


def command_get(device: Netio, args: argparse.Namespace) -> None:
    """Print the state of the output and exit"""

    # one read of the device gives both the id range for "ALL" and the states
    outputs = device.get_outputs()
    ids = get_ids(args.id, len(outputs))
    picked = device._pick(outputs, ids, "output", UnknownOutputId)

    rows = [
        (
            o.ID,
            o.State,
            o.Action.value if args.action_int else o.Action.name,
            o.Delay,
            o.Current,
            o.PowerFactor,
            o.Load,
            o.Energy,
            o.Name,
        )
        for o in picked
    ]
    _print_table(
        (
            "id",
            "State",
            "Action",
            "Delay",
            "Current",
            "PFactor",
            "Load",
            "Energy",
            "Name",
        ),
        rows,
        args,
    )


def command_inputs(device: Netio, args: argparse.Namespace) -> None:
    """Print the state of the inputs and exit"""

    # one read of the device gives both the id range for "ALL" and the states
    inputs = device.get_inputs()
    ids = get_ids(args.id, len(inputs), "input")
    picked = device._pick(inputs, ids, "input", UnknownInputId)

    rows = [
        (i.ID, i.State, i.S0Counter, i.TemperatureC, i.TemperatureF, i.Humidity, i.Name)
        for i in picked
    ]
    _print_table(
        ("id", "State", "S0Counter", "TempC", "TempF", "Humidity", "Name"), rows, args
    )


def _print_values(values: dict, indent: str) -> None:
    """Print name and value on one line each, with the values lined up"""
    width = max((len(name) for name in values), default=0)
    for name, value in values.items():
        print(f"{indent}{name:<{width}}  {value}")


def command_info(device: Netio, args: argparse.Namespace) -> None:
    """Print out all data from device info"""

    # A section is either a group of values, such as Agent, or a list of items,
    # such as Inputs, Watchdogs or Rules. Which sections the device sends
    # depends on the model and on the firmware version.
    for name, section in device.get_info().items():
        print(name)

        if isinstance(section, dict):
            _print_values(section, "   ")
        elif isinstance(section, list):
            for number, item in enumerate(section, start=1):
                print(f"   [{number}]")
                if isinstance(item, dict):
                    _print_values(item, "      ")
                else:
                    print(f"      {item}")
        else:
            print(f"   {section}")


if __name__ == "__main__":
    main()
