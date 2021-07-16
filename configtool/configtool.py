#!/usr/bin/env python3
# -*- coding: utf8 -*-

# flake8: noqa           # flake8 has no per file settings :(
# pylint: disable=C0111  # docstrings are always outdated and wrong
# pylint: disable=C0114  #      Missing module docstring (missing-module-docstring)
# pylint: disable=W0511  # todo is encouraged
# pylint: disable=C0301  # line too long
# pylint: disable=R0902  # too many instance attributes
# pylint: disable=C0302  # too many lines in module
# pylint: disable=C0103  # single letter var names, func name too descriptive
# pylint: disable=R0911  # too many return statements
# pylint: disable=R0912  # too many branches
# pylint: disable=R0915  # too many statements
# pylint: disable=R0913  # too many arguments
# pylint: disable=R1702  # too many nested blocks
# pylint: disable=R0914  # too many local variables
# pylint: disable=R0903  # too few public methods
# pylint: disable=E1101  # no member for base
# pylint: disable=W0201  # attribute defined outside __init__
# pylint: disable=R0916  # Too many boolean expressions in if statement
# pylint: disable=C0305  # Trailing newlines editor should fix automatically, pointless warning

import os
import sys
import time
from signal import SIG_DFL
from signal import SIGPIPE
from signal import signal

import click
import sh

signal(SIGPIPE, SIG_DFL)
import configparser
import errno
import os
from pathlib import Path
from typing import ByteString
from typing import Generator
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

#from with_chdir import chdir
from asserttool import eprint
from asserttool import ic
from asserttool import nevd
from asserttool import validate_slice
from enumerate_input import enumerate_input
from retry_on_exception import retry_on_exception
from timetool import get_mtime

global APP_NAME
APP_NAME = 'configtool'


class ConfigUnchangedError(ValueError):
    pass


def get_config_directory(*,
                         click_instance,
                         app_name: str,
                         verbose: bool,
                         debug: bool,
                         ):
    if verbose:
        ic(click_instance, click_instance.get_app_dir(app_name))
    assert len(app_name) > 0
    result = Path(click_instance.get_app_dir(app_name))
    if verbose:
        ic(result)
    return result


def get_config_ini_path(*,
                        click_instance,
                        app_name: str,
                        verbose: bool,
                        debug: bool,
                        ):

    cfg_dir = get_config_directory(click_instance=click_instance,
                                   app_name=app_name,
                                   verbose=verbose,
                                   debug=debug,)

    cfg = cfg_dir / Path('config.ini')
    return cfg


def get_data_dir(*,
                 click_instance,
                 app_name: str,
                 verbose: bool,
                 debug: bool,
                 ):

    cfg_dir = get_config_directory(click_instance=click_instance,
                                   app_name=app_name,
                                   verbose=verbose,
                                   debug=debug,)

    data_dir = cfg_dir / Path('data')
    os.makedirs(data_dir, exist_ok=True)

    return data_dir


def click_read_config(*,
                      click_instance,
                      app_name: str,
                      verbose: bool,
                      debug: bool,
                      last_mtime=None,
                      keep_case: bool = True,
                      ):

    cfg = get_config_ini_path(click_instance=click_instance,
                              app_name=app_name,
                              verbose=verbose,
                              debug=debug,)

    try:
        config_mtime = get_mtime(cfg)
    except FileNotFoundError:
        config_mtime = None

    if config_mtime:
        if config_mtime == last_mtime:
            raise ConfigUnchangedError

    cfg.parent.mkdir(exist_ok=True)
    if debug:
        ic(cfg)
    parser = configparser.RawConfigParser()
    if keep_case:
        parser.optionxform = str
    parser.read([cfg])
    rv = {}
    if debug:
        ic(parser.sections())
    for section in parser.sections():
        rv[section] = {}
        for key, value in parser.items(section):
            rv[section][key] = value
    if debug:
        ic(rv)

    return rv, config_mtime


@retry_on_exception(exception=OSError,
                    errno=errno.ENOSPC,)
def click_write_config_entry(*,
                             click_instance,
                             app_name: str,
                             section: str,
                             key: str,
                             value: str,
                             verbose: bool,
                             debug: bool,
                             keep_case: bool = True,
                             ):
    if debug:
        ic(app_name, section, key, value)
    cfg = get_config_ini_path(click_instance=click_instance,
                              app_name=app_name,
                              verbose=verbose,
                              debug=debug,)

    cfg.parent.mkdir(exist_ok=True)
    parser = configparser.RawConfigParser()
    if keep_case:
        parser.optionxform = str
    parser.read([cfg])
    try:
        parser[section][key] = value
    except KeyError:
        parser[section] = {}
        parser[section][key] = value

    with open(cfg, 'w') as configfile:
        parser.write(configfile)

    config, config_mtime = click_read_config(click_instance=click_instance,
                                             app_name=app_name,
                                             verbose=verbose,
                                             debug=debug,)
    return config, config_mtime


def _click_remove_config_entry(*,
                               click_instance,
                               app_name: str,
                               section: str,
                               key: str,
                               value: str,
                               verbose: bool,
                               debug: bool,
                               keep_case: bool = True,
                               ):
    cfg = Path(os.path.join(click_instance.get_app_dir(app_name), 'config.ini'))
    parser = configparser.RawConfigParser()
    parser.read([cfg])
    if keep_case:
        parser.optionxform = str
    try:
        parser[section][key] = value
    except KeyError:
        parser[section] = {}
        parser[section][key] = value

    with open(cfg, 'w') as configfile:
        parser.write(configfile)

    config, config_mtime = click_read_config(click_instance=click_instance,
                                             app_name=app_name,
                                             verbose=verbose,
                                             debug=debug,)
    return config, config_mtime


@click.command()
@click.option('--add', is_flag=True)
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
@click.pass_context
def cli(ctx,
        add: bool,
        verbose: bool,
        debug: bool,
        ):

    null, end, verbose, debug = nevd(ctx=ctx,
                                     printn=False,
                                     ipython=False,
                                     verbose=verbose,
                                     debug=debug,)
    if verbose:
        ic(dir(ctx))

    global APP_NAME
    config, config_mtime = click_read_config(click_instance=click,
                                             app_name=APP_NAME,
                                             verbose=verbose,
                                             debug=debug,)
    if verbose:
        ic(config, config_mtime)

    if add:
        section = "test_section"
        key = "test_key"
        value = "test_value"
        config, config_mtime = click_write_config_entry(click_instance=click,
                                                        app_name=APP_NAME,
                                                        section=section,
                                                        key=key,
                                                        value=value,
                                                        verbose=verbose,
                                                        debug=debug,)
        if verbose:
            ic(config)

