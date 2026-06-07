import argparse
import tempfile
import unittest
from argparse_toml import TOMLArgumentParser, TOMLConfigAction


class TestArgparseTOML(unittest.TestCase):

    def test_standard_defaults(self):
        """Test that regular key-value defaults are preserved."""
        parser = TOMLArgumentParser()
        parser.add_argument("--foo", type=str)
        parser.set_defaults(foo="bar")

        args = parser.parse_args([])
        self.assertEqual(args.foo, "bar")

    def test_nested_subparser_defaults(self):
        """Test that dictionary argument values are treated as subparser defaults."""
        parser = TOMLArgumentParser()
        parser.add_argument("--global-opt", type=str)

        subparsers = parser.add_subparsers(dest="subcommand")
        sub_foo = subparsers.add_parser("foo")
        sub_foo.add_argument("--bar", type=int)

        sub_baz = subparsers.add_parser("baz")
        sub_baz.add_argument("--qux", type=str)

        # set defaults recursively:
        # foo has bar=42, baz has qux="hello", and main has global_opt="world"
        parser.set_defaults(global_opt="world", foo={"bar": 42}, baz={"qux": "hello"})

        # Parse foo
        args1 = parser.parse_args(["foo"])
        self.assertEqual(args1.global_opt, "world")
        self.assertEqual(args1.subcommand, "foo")
        self.assertEqual(args1.bar, 42)

        # Parse baz (qux should be "hello")
        args2 = parser.parse_args(["baz"])
        self.assertEqual(args2.global_opt, "world")
        self.assertEqual(args2.subcommand, "baz")
        self.assertEqual(args2.qux, "hello")

    def test_dictionary_non_subparser_key(self):
        """Test that key-value dict default is set normally if not matching a subparser name."""
        parser = TOMLArgumentParser()
        parser.add_argument("--dict-arg", type=dict)

        # 'dict_arg' is not defined as a subparser name, so it sets a normal default
        parser.set_defaults(dict_arg={"key": "val"})

        args = parser.parse_args([])
        self.assertEqual(args.dict_arg, {"key": "val"})

    def test_toml_default_config_absent(self):
        parser = TOMLArgumentParser()
        parser.add_argument("--config", action=TOMLConfigAction, default="non_existent_file_path_12345.toml")
        args = parser.parse_args([])
        self.assertEqual(args.config, ["non_existent_file_path_12345.toml"])

    def test_toml_config_action_flat(self):
        """Test transparently applying flat defaults from a TOML file."""
        parser = TOMLArgumentParser()
        parser.add_argument("--config", action=TOMLConfigAction)
        parser.add_argument("--host", type=str, default="localhost")
        parser.add_argument("--port", type=int, default=8080)

        # Create a temp TOML file
        with tempfile.NamedTemporaryFile("w+", suffix=".toml") as f:
            f.write("host = '127.0.0.1'\nport = 9000\n")
            f.flush()
            temp_path = f.name

            # Parse command line pointing to the config file
            args = parser.parse_args(["--config", temp_path])
            self.assertEqual(args.host, "127.0.0.1")
            self.assertEqual(args.port, 9000)
            self.assertEqual(args.config, [temp_path])

            # Test that command-line options override TOML defaults
            args_override = parser.parse_args(["--config", temp_path, "--port", "1111"])
            self.assertEqual(args_override.host, "127.0.0.1")
            self.assertEqual(args_override.port, 1111)

    def test_toml_config_action_nested(self):
        """Test transparently applying nested (subparser) defaults from a TOML file."""
        parser = TOMLArgumentParser()
        parser.add_argument("--config", action=TOMLConfigAction)
        parser.add_argument("--timeout", type=int, default=10)

        subparsers = parser.add_subparsers(dest="command")
        run_parser = subparsers.add_parser("run")
        run_parser.add_argument("--port", type=int, default=3000)
        run_parser.add_argument("--workers", type=int, default=1)

        # Create a temp TOML file representing nested dictionary defaults
        with tempfile.NamedTemporaryFile("w+", suffix=".toml") as f:
            f.write("""
timeout = 30

[run]
port = 5000
workers = 4
""")
            f.flush()
            temp_path = f.name

            # Parse command line without overriding subparser commands
            args_main = parser.parse_args(["--config", temp_path, "run"])
            self.assertEqual(args_main.timeout, 30)
            self.assertEqual(args_main.command, "run")
            self.assertEqual(args_main.port, 5000)
            self.assertEqual(args_main.workers, 4)

            # Parse with command-line overrides
            args_override = parser.parse_args(["--config", temp_path, "run", "--port", "7000"])
            self.assertEqual(args_override.timeout, 30)
            self.assertEqual(args_override.command, "run")
            self.assertEqual(args_override.port, 7000)
            self.assertEqual(args_override.workers, 4)

    def test_missing_toml_config_file(self):
        """Test that a missing TOML file correctly reports an argparse error."""
        parser = TOMLArgumentParser()
        parser.add_argument("--config", action=TOMLConfigAction)

        # Mock or use standard argparse Error handling (raises SystemExit)
        with self.assertRaises(FileNotFoundError):
            # Pass a non-existent file path
            parser.parse_args(["--config", "non_existent_file_path_12345.toml"])


if __name__ == "__main__":
    unittest.main()
