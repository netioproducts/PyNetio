from . import Netio
from pathlib import Path
import argparse
import itertools
import os
import requests
import sys
import yaml


def add_output_actions_for_arg(actions, arg, action):
    if arg:
        for item in flatten(arg):
            actions[item] = action


def create_argument_parser():
    default_config = os.getenv('NETIO_CONFIG', 'netio.yml')

    parser = argparse.ArgumentParser(description='NETIO command line tool',
        epilog='There is explicitly no support for specifying the device password '
            'via command line arguments for not having it ending up in history '
            'and process listings. Please use a configuration file. See '
            '\'netio.yml.example\' for an example.'
            'You may specify the default configuration file in the environment '
            'variable NETIO_CONFIG.')
    parser.add_argument('--config', type=Path, default=default_config,
        help='YAML configuration for device name, certificate and password (default is {})'.format(default_config))
    parser.add_argument('--verbose', action='store_true',
        help='be verbose (e.g. print column headers)')
    subparsers = parser.add_subparsers(metavar='COMMAND', help='sub commands')

    get_parser = subparsers.add_parser('get', help='get outputs')
    get_parser.set_defaults(function=get_command)
    get_parser.add_argument('outputs', metavar='OUTPUTS', type=int,
        action='append', nargs='+',
        help='outputs to get status for')

    set_parser = subparsers.add_parser('set', help='set outputs')
    set_parser.set_defaults(function=set_command)
    set_parser.add_argument('--off', metavar='OUTPUT', type=int,
        action='append', nargs='+',
        help='outputs to turn off')
    set_parser.add_argument('--on', metavar='OUTPUT', type=int,
        action='append', nargs='+',
        help='outputs to turn on')
    set_parser.add_argument('--short-off', metavar='OUTPUT', type=int,
        action='append', nargs='+',
        help='outputs to turn off for a short period')
    set_parser.add_argument('--short-on', metavar='OUTPUT', type=int,
        action='append', nargs='+',
        help='outputs to turn on for a short period')
    set_parser.add_argument('--toggle', metavar='OUTPUT', type=int,
        action='append', nargs='+',
        help='outputs to toggle')

    return parser


def create_output_actions(args):
    actions = {}

    add_output_actions_for_arg(actions, args.off, Netio.ACTION.OFF)
    add_output_actions_for_arg(actions, args.on, Netio.ACTION.ON)
    add_output_actions_for_arg(actions, args.short_off, Netio.ACTION.SHORT_OFF)
    add_output_actions_for_arg(actions, args.short_on, Netio.ACTION.SHORT_ON)
    add_output_actions_for_arg(actions, args.toggle, Netio.ACTION.TOGGLE)

    return actions


def flatten(iterable):
    return itertools.chain.from_iterable(iterable)


def program_name():
    return os.path.basename(sys.argv[0])




def get_command(device, args):
    """
    Prints output state information for the requested outputs in a tabular form
    suitable for further processing in a pipe (grep, awk, ...).
    """
    requested_ids = set(flatten(args.outputs))
    all_outputs = device.get_outputs()
    requested_outputs = [o for o in all_outputs if o.ID in requested_ids]
    line_format = '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'

    if args.verbose:
        print(line_format.format('id', 'name', 'state', 'action', 'delay',
            'current', 'pf', 'load', 'energy'))

    for output in requested_outputs:
        print(line_format.format(output.ID, output.Name, output.State,
            output.Action, output.Delay, output.Current, output.PowerFactor,
            output.Load, output.Energy))


def set_command(device, args):
    actions = create_output_actions(args)

    # All action arguments are optional at the time of argument parsing. So we
    # could end up with an empty action list which gets sorted out here because
    # setting outputs fails at parsing the response in this situation.
    if len(actions) == 0:
        print('{}: at least one output required.'.format(program_name()),
            file=sys.stderr)
        sys.exit(1)

    device.set_outputs(actions)




def main():
    netio_cli(sys.argv)


def netio_cli(argv):
    parser = create_argument_parser()
    args = parser.parse_args(argv[1:])

    # TOOD: Is there some config-ish format supported by Python's standard
    # library?
    with args.config.open() as f:
        config = yaml.load(f)

    if config.get('disable_urllib_warnings', False):
        # Disable warnings about certificate's subjectAltName versus commonName
        # entry.
        requests.packages.urllib3.disable_warnings()


    protocol = config.get('protocol', 'https')
    cert = None

    if protocol == 'https':
        # If the certificate is given as a relative path. Its position is assumed
        # relative to the config file.
        cert = Path(config['cert'])
        if not cert.is_absolute():
            cert = args.config.parent / cert

    url = '{}://{}/netio.json'.format(protocol, config['device'])
    auth = (config.get('user', 'write'), config['password'])
    device = Netio(url, auth_rw=auth, verify=cert)


    if hasattr(args, 'function'):
        args.function(device, args)
    else:
        parser.print_usage(file=sys.stderr)


if __name__ == '__main__':
    main()
