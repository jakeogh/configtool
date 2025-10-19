#!/usr/bin/env python3
# -*- coding: utf8 -*-

from __future__ import annotations

import configparser
import errno
import os
from pathlib import Path
from signal import SIG_DFL
from signal import SIGPIPE
from signal import signal

import click
from asserttool import ic
from click_auto_help import AHGroup
from clicktool import click_add_options
from clicktool import click_global_options
from clicktool import tvicgvd
from globalverbose import gvd
from retry_on_exception import retry_on_exception
from timetool import get_mtime

signal(SIGPIPE, SIG_DFL)

APP_NAME = "configtool"


class ConfigUnchangedError(ValueError):
    pass


def get_config_directory(
    *,
    click_instance,
    app_name: str,
):
    # ic(click_instance, click_instance.get_app_dir(app_name))
    assert len(app_name) > 0
    result = Path(click_instance.get_app_dir(app_name))
    # ic(result)
    return result


def get_config_ini_path(
    *,
    click_instance,
    app_name: str,
):
    cfg_dir = get_config_directory(
        click_instance=click_instance,
        app_name=app_name,
    )

    cfg = cfg_dir / Path("config.ini")
    return cfg


def get_data_dir(
    *,
    click_instance,
    app_name: str,
):
    cfg_dir = get_config_directory(
        click_instance=click_instance,
        app_name=app_name,
    )

    data_dir = cfg_dir / Path("data")
    os.makedirs(data_dir, exist_ok=True)

    return data_dir


def read_config(
    *,
    path: Path,
    keep_case: bool,
):
    parser = configparser.RawConfigParser(delimiters=("\t",))
    if keep_case:
        parser.optionxform = str
    parser.read([path])
    rv = {}
    if gvd:
        ic(parser.sections())
    for section in parser.sections():
        rv[section] = {}
        for key, value in parser.items(section):
            rv[section][key] = value
    if gvd:
        ic(rv)

    return rv


def click_read_config(
    *,
    click_instance,
    app_name: str,
    last_mtime=None,
    keep_case: bool = True,
):
    cfg = get_config_ini_path(
        click_instance=click_instance,
        app_name=app_name,
    )

    try:
        config_mtime = get_mtime(cfg)
    except FileNotFoundError:
        config_mtime = None

    if config_mtime:
        if config_mtime == last_mtime:
            raise ConfigUnchangedError

    cfg.parent.mkdir(exist_ok=True)
    if gvd:
        ic(cfg)

    rv = read_config(path=cfg, keep_case=keep_case)

    return rv, config_mtime


@retry_on_exception(
    exception=OSError,
    errno=errno.ENOSPC,
)
def write_config_entry(
    *,
    path: Path,
    section: str,
    keep_case: bool = True,
    key: None | str = None,
    value: None | str = None,
) -> None:
    parser = configparser.RawConfigParser(delimiters=("\t",))
    if keep_case:
        parser.optionxform = str

    if value:
        assert isinstance(value, str)
        assert len(value) > 0
        assert value != " "
    else:
        value = "None"

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
    keep_case: bool = True,
    key: None | str = None,
    value: None | str = None,
):
    if gvd:
        ic(
            app_name,
            section,
            key,
            value,
        )

    assert isinstance(section, str)
    if key:
        assert isinstance(key, str)
    if value:
        assert isinstance(value, str)
        assert len(value) > 0
        assert value != " "
        assert value != ""
    cfg = get_config_ini_path(
        click_instance=click_instance,
        app_name=app_name,
    )
    if gvd:
        ic(cfg)

    cfg.parent.mkdir(exist_ok=True)
    write_config_entry(
        path=cfg,
        section=section,
        key=key,
        keep_case=keep_case,
        value=value,
    )

    config, config_mtime = click_read_config(
        click_instance=click_instance,
        app_name=app_name,
    )
    return config, config_mtime


def click_remove_config_entry(
    *,
    click_instance,
    app_name: str,
    section: str,
    key: str,
    value: str,
):
    cfg = Path(os.path.join(click_instance.get_app_dir(app_name), "config.ini"))
    parser = configparser.RawConfigParser(delimiters=("\t",))
    parser.read([cfg])

    assert parser[section][key] == value
    del parser[section][key]

    with open(cfg, "w", encoding="utf8") as configfile:
        parser.write(configfile)

    config, config_mtime = click_read_config(
        click_instance=click_instance,
        app_name=app_name,
    )
    return config, config_mtime


@click.group(no_args_is_help=True, cls=AHGroup)
@click_add_options(click_global_options)
@click.pass_context
def cli(
    ctx,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    ctx.ensure_object(dict)
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
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
    value: None | str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    # ic(dir(ctx))

    global APP_NAME
    config, config_mtime = click_read_config(
        click_instance=click,
        app_name=APP_NAME,
    )

    # ic(config, config_mtime)

    section = "test_section"
    key = "test_key"
    value = "test_value"
    config, config_mtime = click_write_config_entry(
        click_instance=click,
        app_name=APP_NAME,
        section=section,
        key=key,
        value=value,
    )
    # ic(config)


@cli.command("list")
@click.argument("section", required=False)
@click_add_options(click_global_options)
@click.pass_context
def show(
    ctx,
    section: None | str,
    verbose_inf: bool,
    dict_output: bool,
    verbose: bool = False,
):
    tty, verbose = tvicgvd(
        ctx=ctx,
        verbose=verbose,
        verbose_inf=verbose_inf,
        ic=ic,
        gvd=gvd,
    )

    # ic(dir(ctx))

    global APP_NAME
    config, config_mtime = click_read_config(
        click_instance=click,
        app_name=APP_NAME,
    )
    # ic(config, config_mtime)
