"""Tests for the command line interface."""

import argparse
from pathlib import Path

import pytest

from Netio import Netio
from Netio.cli import command_info, get_ids, get_output_actions, str2action
from Netio.exceptions import NetioException

EXAMPLE_CONFIG = Path(__file__).parents[1] / 'examples' / 'netio.example.ini'


@pytest.mark.parametrize(
    'text, expected',
    [
        ('ON', Netio.ACTION.ON),
        ('on', Netio.ACTION.ON),
        ('toggle', Netio.ACTION.TOGGLE),
        ('0', Netio.ACTION.OFF),
        ('4', Netio.ACTION.TOGGLE),
    ],
)
def test_an_action_can_be_given_by_name_or_by_number(text, expected):
    assert str2action(text) == expected


@pytest.mark.parametrize('text', ['sideways', '99', ''])
def test_an_action_that_makes_no_sense_is_rejected(text):
    # argparse turns this into a usage message for the user
    with pytest.raises(Exception):
        str2action(text)


@pytest.mark.parametrize(
    'given, expected',
    [
        (['ALL'], [1, 2, 3, 4]),
        (['all'], [1, 2, 3, 4]),
        (['2'], [2]),
        (['3', '1'], [3, 1]),  # the order the user asked for is kept
        (['1', '1'], [1, 1]),
    ],
)
def test_choosing_which_outputs_to_read(given, expected):
    assert get_ids(given, 4) == expected


def test_choosing_what_to_do_with_each_output():
    assert get_output_actions(['1', 'ON', '3', 'OFF'], 4) == {
        1: Netio.ACTION.ON,
        3: Netio.ACTION.OFF,
    }


def test_doing_the_same_thing_to_every_output():
    assert get_output_actions(['ALL', 'TOGGLE'], 2) == {
        1: Netio.ACTION.TOGGLE,
        2: Netio.ACTION.TOGGLE,
    }


@pytest.mark.parametrize(
    'given',
    [
        ['1'],  # an output with no action
        ['1', 'ON', '2'],  # odd number of words
        ['1', 'ON', '1', 'OFF'],  # two actions for the same output
        ['ALL', 'ON', '1', 'OFF'],  # mixing ALL with single outputs
        ['9', 'ON'],  # this device only has 4 outputs
    ],
)
def test_output_and_action_pairs_that_are_not_allowed(given):
    with pytest.raises(NetioException):
        get_output_actions(given, 4)


def test_the_info_command_prints_every_kind_of_section(make_device, response_8qs, capsys):
    """
    Firmware 5.x sends PAB, Watchdogs and Rules as lists.

    The command used to treat every section as name and value pairs, so it
    failed on all current devices.
    """
    command_info(make_device(response_8qs), args=None)

    printed = capsys.readouterr().out

    # a section of name and value pairs
    assert 'Version' in printed
    assert '5.3.1' in printed
    # a section that is a list
    assert 'google_pinger' in printed  # the name of watchdog 1


def test_the_info_command_on_a_device_with_fewer_sections(make_device, response_2pz, capsys):
    command_info(make_device(response_2pz), args=None)

    printed = capsys.readouterr().out

    assert 'PowerCable-2PZ' in printed
    assert 'GlobalMeasure' not in printed


def config_args(device: str) -> argparse.Namespace:
    """Build the arguments the way the command line parser would."""
    return argparse.Namespace(
        device=device,
        conf=str(EXAMPLE_CONFIG),
        cert=True,
        user=None,
        password=None,
        no_cert_warning=False,
    )


def test_the_example_config_file_can_be_read():
    """
    The config file we ship as an example has to be a valid one.

    It used to end with a `password` line that had no value, so anyone who
    followed the README got 'Failed reading config' and nothing else.
    """
    args = load_config(config_args('http://powerpdu-8qs.netio-products.com/netio.json'))

    # picked up from the section named after the host
    assert args.user == 'netio'
    assert args.password == 'netio'
