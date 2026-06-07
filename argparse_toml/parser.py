#!/usr/bin/env python3
'''
An argparse.ArgumentParser extension that can read TOML configuration file
and apply the data recursively as defaults for the parser and it's subparsers.
'''

from argparse import ArgumentParser, ArgumentError, FileType
from argparse import _SubParsersAction, _AppendAction
import tomllib
from pathlib import Path

class ListDefaultAction(_AppendAction):
    """An argparse append-style action that silently converts single default to an one-element list."""
    def __init__(self, option_strings, dest, default=None, **kwargs):
        if default and not isinstance(default, list):
            default = [default]
        super().__init__(option_strings, dest, default=default, **kwargs)

class TOMLConfigAction(ListDefaultAction):
    """An argparse Action that registers a TOML config file(s) to load defaults from."""

def TOMLLoader(filename):
    """"Converts" TOML file name to dict by loading file's content.

    Use 'type=TOMLLoader' in pargs_args() to instantly load TOML content from specified file.
    """
    with Path(filename).open("rb") as f:
        return tomllib.load(f)

class TOMLArgumentParser(ArgumentParser):
    """An argparse.ArgumentParser subclass supporting nested subparser defaults and TOML configs.

    During the actual argument parsing, the specified TOML config files are
    read and joined into the single dict. The dict is passed to recursive
    set_defaults(). If default config file name is set, but the file is not
    found, it is silently skipped. Otherwise, the default config file is always
    read first.
    """

    def set_defaults(self, **kwargs):
        """Set default values for parser arguments and recursively for subparsers.

        If a keyword argument is a dictionary, its key is checked against the list
        of defined subparser names. If found, the dictionary is passed recursively
        to the subparser's set_defaults() method.
        """

        normal_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, dict) and (subparser := self._find_subparser(k)):
                subparser.set_defaults(**v)
            else:
                normal_kwargs[k] = v
        super().set_defaults(**normal_kwargs)

    def _find_subparser(self, name):
        """Find a direct subparser by its choice name."""
        for action in self._actions:
            if isinstance(action, _SubParsersAction):
                if isinstance(sub := action.choices.get(name, None), ArgumentParser):
                    return sub
        return None

    def parse_known_args(self, args, namespace):
        """Parse arguments, pre-loading any TOML configuration files transparently first.

        The configuration file specified as "default=" argument can be non-existent.
        In this case it is omitted silently. Explicitly defined files should exit.
        """
        if args is None:
            import sys
            args = sys.argv[1:]
        else:
            args = list(args)

        config_parser = ArgumentParser(add_help=False)
        for action in self._actions:
            if isinstance(action, TOMLConfigAction):
                default = [TOMLLoader(d) for d in (action.default or []) if Path(d).exists()]
                vs = {k: v for k, v in action._get_kwargs() if k not in {"required"}}
                vs["type"], vs["default"] = TOMLLoader, default
                config_parser.add_argument(*action.option_strings, action=TOMLConfigAction, **vs)
                # config_parser._actions.append(action)
        configs, _ = config_parser.parse_known_args(args)
        config_data = {}
        for files in vars(configs).values():
            for file in files:
                config_data |= file
        self.set_defaults(**config_data)
        return super().parse_known_args(args, namespace)
