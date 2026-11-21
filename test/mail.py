#!/usr/bin/env -S uv run --script

import argparse
import sys

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path

now = datetime.now(timezone.utc)

test_dir = Path(__file__).parent
mail_dir = test_dir / "mail"


def parse_args() -> argparse.Namespace:
    parser = ArgumentParser(description="Downgraded stub for GNU Mailutils mail")
    parser.add_argument("--append", action="append")
    parser.add_argument("--attach", action="append")
    parser.add_argument("--bcc", action="append")
    parser.add_argument("--cc", action="append")
    parser.add_argument("--content-type", action="append")
    parser.add_argument("--encoding", action="append")
    parser.add_argument("--mime", action="store_true")
    parser.add_argument("--subject", help="todo")
    parser.add_argument("recipients", nargs="+")
    return parser.parse_args()


def main():
    args = sys.argv[1:]
    body = sys.stdin.read()
    mail_dir.mkdir(exist_ok=True)
    filename = f"{now.isoformat()}.log"
    with open(mail_dir / filename, "w", encoding="utf-8") as f:
        f.write("Arguments:\n")
        for arg in args:
            f.write(f"  {arg}\n")
        f.write("\n")
        f.write("-----BEGIN BODY-----\n")
        f.write(body)
        f.write("-----END BODY-----\n")


main()
