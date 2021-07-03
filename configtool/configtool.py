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
from asserttool import nevd
from asserttool import validate_slice
from enumerate_input import enumerate_input
from epochfilter import get_mtime
from retry_on_exception import retry_on_exception


def eprint(*args, **kwargs):
    if 'file' in kwargs.keys():
        kwargs.pop('file')
    print(*args, file=sys.stderr, **kwargs)


try:
    from icecream import ic  # https://github.com/gruns/icecream
    from icecream import icr  # https://github.com/jakeogh/icecream
except ImportError:
    ic = eprint
    icr = eprint


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
# import pdb; pdb.set_trace()
# #set_trace(term_size=(80, 24))
# from pudb import set_trace; set_trace(paused=False)

##def log_uncaught_exceptions(ex_cls, ex, tb):
##   eprint(''.join(traceback.format_tb(tb)))
##   eprint('{0}: {1}'.format(ex_cls, ex))
##
##sys.excepthook = log_uncaught_exceptions

def get_timestamp():
    timestamp = str("%.22f" % time.time())
    return timestamp


#@with_plugins(iter_entry_points('click_command_tree'))
#@click.group()
#@click.option('--verbose', is_flag=True)
#@click.option('--debug', is_flag=True)
#@click.pass_context
#def cli(ctx,
#        verbose: bool,
#        debug: bool,
#        ):
#
#    ctx.ensure_object(dict)
#    ctx.obj['verbose'] = verbose
#    ctx.obj['debug'] = debug




# DONT CHANGE FUNC NAME
@click.command()
@click.argument("paths", type=str, nargs=-1)
@click.argument("sysskel",
                type=click.Path(exists=False,
                                dir_okay=True,
                                file_okay=False,
                                path_type=str,
                                allow_dash=False,),
                nargs=1,
                required=True,)
@click.argument("slice_syntax", type=validate_slice, nargs=1)
#@click.option('--add', is_flag=True)
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
@click.option('--simulate', is_flag=True)
@click.option('--ipython', is_flag=True)
@click.option('--count', is_flag=True)
@click.option('--skip', type=int, default=False)
@click.option('--head', type=int, default=False)
@click.option('--tail', type=int, default=False)
@click.option("--printn", is_flag=True)
#@click.option("--progress", is_flag=True)
@click.pass_context
def cli(ctx,
        paths,
        sysskel: str,
        slice_syntax: str,
        verbose: bool,
        debug: bool,
        simulate: bool,
        ipython: bool,
        count: bool,
        skip: int,
        head: int,
        tail: int,
        printn: bool,
        ):

    ctx.ensure_object(dict)
    null, end, verbose, debug = nevd(ctx=ctx,
                                     printn=printn,
                                     ipython=False,
                                     verbose=verbose,
                                     debug=debug,)

    #progress = False
    #if (verbose or debug):
    #    progress = False

    #ctx.obj['end'] = end
    #ctx.obj['null'] = null
    #ctx.obj['progress'] = progress
    ctx.obj['count'] = count
    ctx.obj['skip'] = skip
    ctx.obj['head'] = head
    ctx.obj['tail'] = tail

    #global APP_NAME
    #config, config_mtime = click_read_config(click_instance=click,
    #                                         app_name=APP_NAME,
    #                                         verbose=verbose,
    #                                         debug=debug,)
    #if verbose:
    #    ic(config, config_mtime)

    #if add:
    #    section = "test_section"
    #    key = "test_key"
    #    value = "test_value"
    #    config, config_mtime = click_write_config_entry(click_instance=click,
    #                                                    app_name=APP_NAME,
    #                                                    section=section,
    #                                                    key=key,
    #                                                    value=value,
    #                                                    verbose=verbose,
    #                                                    debug=debug,)
    #    if verbose:
    #        ic(config)

    iterator = paths

    index = 0
    for index, path in enumerate_input(iterator=iterator,
                                       dont_decode=True,  # paths are bytes
                                       null=null,
                                       progress=False,
                                       skip=skip,
                                       head=head,
                                       tail=tail,
                                       debug=debug,
                                       verbose=verbose,):
        path = Path(os.fsdecode(path))

        if verbose:  # or simulate:
            ic(index, path)
        #if count:
        #    if count > (index + 1):
        #        ic(count)
        #        sys.exit(0)

        #if simulate:
        #    continue

        with open(path, 'rb') as fh:
            path_bytes_data = fh.read()

        if not count:
            print(path, end=end)

    if count:
        print(index + 1, end=end)

#        if ipython:
#            import IPython; IPython.embed()

#@cli.command()
#@click.argument("urls", type=str, nargs=-1)
#@click.option('--verbose', is_flag=True)
#@click.option('--debug', is_flag=True)
#@click.pass_context
#def some_command(ctx,
#                 urls,
#                 verbose: bool,
#                 debug: bool,
#                 ):
#    if verbose:
#        ctx.obj['verbose'] = verbose
#    verbose = ctx.obj['verbose']
#    if debug:
#        ctx.obj['debug'] = debug
#    debug = ctx.obj['debug']
#
#    iterator = urls
#    for index, url in enumerate_input(iterator=iterator,
#                                      null=ctx.obj['null'],
#                                      progress=ctx.obj['progress'],
#                                      skip=ctx.obj['skip'],
#                                      head=ctx.obj['head'],
#                                      tail=ctx.obj['tail'],
#                                      debug=ctx.obj['debug'],
#                                      verbose=ctx.obj['verbose'],):
#
#        if ctx.obj['verbose']:
#            ic(index, url)



