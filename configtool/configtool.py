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

import configparser
import errno
import os
from math import inf
from pathlib import Path
from signal import SIG_DFL
from signal import SIGPIPE
from signal import signal
from typing import Optional
from typing import Union

import click
from asserttool import ic
from asserttool import validate_slice
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tv
from eprint import eprint
from retry_on_exception import retry_on_exception
from timetool import get_mtime

signal(SIGPIPE, SIG_DFL)
global APP_NAME
APP_NAME = "configtool"


class ConfigUnchangedError(ValueError):
    pass


def get_config_directory(
    *,
    click_instance,
    app_name: str,
    verbose: Union[bool, int, float],
):
    if verbose:
        ic(click_instance, click_instance.get_app_dir(app_name))
    assert len(app_name) > 0
    result = Path(click_instance.get_app_dir(app_name))
    if verbose:
        ic(result)
    return result


def get_config_ini_path(
    *,
    click_instance,
    app_name: str,
    verbose: Union[bool, int, float],
):

    cfg_dir = get_config_directory(
        click_instance=click_instance,
        app_name=app_name,
        verbose=verbose,
    )

    cfg = cfg_dir / Path("config.ini")
    return cfg


def get_data_dir(
    *,
    click_instance,
    app_name: str,
    verbose: Union[bool, int, float],
):

    cfg_dir = get_config_directory(
        click_instance=click_instance,
        app_name=app_name,
        verbose=verbose,
    )

    data_dir = cfg_dir / Path("data")
    os.makedirs(data_dir, exist_ok=True)

    return data_dir


def read_config(
    *,
    path: Path,
    keep_case: bool,
    verbose: Union[bool, int, float],
):

    parser = configparser.RawConfigParser(delimiters=("\t",))
    if keep_case:
        parser.optionxform = str
    parser.read([path])
    rv = {}
    if verbose == inf:
        ic(parser.sections())
    for section in parser.sections():
        rv[section] = {}
        for key, value in parser.items(section):
            rv[section][key] = value
    if verbose == inf:
        ic(rv)

    return rv


def click_read_config(
    *,
    click_instance,
    app_name: str,
    verbose: Union[bool, int, float],
    last_mtime=None,
    keep_case: bool = True,
):

    cfg = get_config_ini_path(
        click_instance=click_instance,
        app_name=app_name,
        verbose=verbose,
    )

    try:
        config_mtime = get_mtime(cfg)
    except FileNotFoundError:
        config_mtime = None

    if config_mtime:
        if config_mtime == last_mtime:
            raise ConfigUnchangedError

    cfg.parent.mkdir(exist_ok=True)
    if verbose == inf:
        ic(cfg)

    rv = read_config(path=cfg, keep_case=keep_case, verbose=verbose)

    return rv, config_mtime


@retry_on_exception(
    exception=OSError,
    errno=errno.ENOSPC,
)
def write_config_entry(
    *,
    path: Path,
    section: str,
    verbose: Union[bool, int, float],
    keep_case: bool = True,
    key: Optional[str] = None,
    value: Optional[str] = None,
) -> None:

    parser = configparser.RawConfigParser(delimiters=("\t",))
    if keep_case:
        parser.optionxform = str

    parser.read([path])
    if key:
        try:
            parser[section][key] = value
        except KeyError:
            parser[section] = {}
            parser[section][key] = value
    else:
        parser[section] = {}

    with open(path, "w") as fh:
        parser.write(fh)


@retry_on_exception(
    exception=OSError,
    errno=errno.ENOSPC,
)
def click_write_config_entry(
    *,
    click_instance,
    app_name: str,
    section: str,
    key: str,
    value: str,
    verbose: Union[bool, int, float],
    keep_case: bool = True,
):
    if verbose == inf:
        ic(app_name, section, key, value)

    assert isinstance(section, str)
    assert isinstance(key, str)
    assert isinstance(value, str)
    cfg = get_config_ini_path(
        click_instance=click_instance,
        app_name=app_name,
        verbose=verbose,
    )
    if verbose == inf:
        ic(cfg)

    cfg.parent.mkdir(exist_ok=True)
    write_config_entry(
        path=cfg,
        section=section,
        key=key,
        keep_case=keep_case,
        value=value,
        verbose=verbose,
    )

    config, config_mtime = click_read_config(
        click_instance=click_instance,
        app_name=app_name,
        verbose=verbose,
    )
    return config, config_mtime


def click_remove_config_entry(
    *,
    click_instance,
    app_name: str,
    section: str,
    key: str,
    value: str,
    verbose: Union[bool, int, float],
):

    cfg = Path(os.path.join(click_instance.get_app_dir(app_name), "config.ini"))
    parser = configparser.RawConfigParser()
    parser.read([cfg])

    assert parser[section][key] == value
    del parser[section][key]

    with open(cfg, "w") as configfile:
        parser.write(configfile)

    config, config_mtime = click_read_config(
        click_instance=click_instance,
        app_name=app_name,
        verbose=verbose,
    )
    return config, config_mtime


@click.group(no_args_is_help=True)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx,
    verbose: Union[bool, int, float],
    verbose_inf: bool,
):

    ctx.ensure_object(dict)
    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )


@cli.command()
@click.argument("section", nargs=1)
@click.argument("key", nargs=1)
@click.argument("value", nargs=1, required=False)
@click_add_options(click_global_options)
@click.pass_context
def add(
    ctx,
    section: str,
    key: str,
    value: Optional[str],
    verbose: Union[bool, int, float],
    verbose_inf: bool,
):

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    if verbose:
        ic(dir(ctx))

    global APP_NAME
    config, config_mtime = click_read_config(
        click_instance=click,
        app_name=APP_NAME,
        verbose=verbose,
    )
    if verbose:
        ic(config, config_mtime)

    section = "test_section"
    key = "test_key"
    value = "test_value"
    config, config_mtime = click_write_config_entry(
        click_instance=click,
        app_name=APP_NAME,
        section=section,
        key=key,
        value=value,
        verbose=verbose,
    )
    if verbose:
        ic(config)


@cli.command("list")
@click.argument("section", required=False)
@click_add_options(click_global_options)
@click.pass_context
def show(
    ctx,
    section: Optional[str],
    verbose: Union[bool, int, float],
    verbose_inf: bool,
):

    tty, verbose = tv(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
    )
    if verbose:
        ic(dir(ctx))

    global APP_NAME
    config, config_mtime = click_read_config(
        click_instance=click,
        app_name=APP_NAME,
        verbose=verbose,
    )
    if verbose:
        ic(config, config_mtime)
