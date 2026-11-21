import argparse
import importlib.util
import logging
import signal
import sys
import threading
import traceback

from argparse import ArgumentParser
from pathlib import Path
from platform import python_implementation
from types import FrameType

from .configuration import Configuration
from .utility import platform


def parse_args():
    parser = ArgumentParser(
        description="VoIP voicemail server",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=32),
    )
    parser.add_argument("--config", metavar="FILE", help="use this config file")
    parser.add_argument("--debug", action="store_true", help="show traceback on error")
    parser.add_argument(
        "--greeting",
        nargs="?",
        const="",
        metavar="FILE",
        help="use FILE (.wav) as greeting, or the default greeting if omitted",
    )
    return parser.parse_args(), parser.prog


def print_to_stderr(*values: object) -> None:
    print(*values, file=sys.stderr)


def main() -> None:
    args, app_name = parse_args()

    try:
        verify_environment()

        from .application import Application

        config_file = (
            args.config
            if args.config is not None
            else (
                f"/usr/local/etc/{app_name}.toml" if platform.is_debian_like() else None
            )
        )
        if config_file is None:
            raise ValueError(
                "No configuration file specified and no default location available for this platform."
            )
        config = Configuration.load(config_file, app_name)
        logging.basicConfig(
            level=config.log.level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        stop_event = threading.Event()

        def handle_shutdown_signal(signum: int, frame: FrameType | None) -> None:
            stop_event.set()

        # register new signal handlers and save the previous ones
        previous_signal_handlers = {
            sig: signal.signal(sig, handle_shutdown_signal)
            for sig in (signal.SIGINT, signal.SIGTERM)
        }

        try:
            app = Application(app_name)
            if args.greeting is not None:
                app.set_greeting(config, Path(args.greeting) if args.greeting else None)
            else:
                app.run(config, stop_event)
        finally:
            # restore previous signal handlers
            for sig, handler in previous_signal_handlers.items():
                signal.signal(sig, handler)
    except BaseException as error:
        if args.debug:
            print_to_stderr(f"Traceback:\n")
            traceback.print_tb(error.__traceback__)
            print_to_stderr()
        print_to_stderr(f"Error: {error}")
        raise SystemExit(1) from error


def verify_environment() -> None:
    if python_implementation() != "CPython":
        raise RuntimeError(
            "Use CPython so PJSUA2 wrapper destruction occurs deterministically"
        )
    if importlib.util.find_spec("pjsua2") is None:
        raise RuntimeError("Cannot find PJSUA2 extension module")


if __name__ == "__main__":
    main()
