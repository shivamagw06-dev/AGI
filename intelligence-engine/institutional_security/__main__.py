"""CLI: python -m institutional_security"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="institutional_security")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--username", default="analyst.demo")
    parser.add_argument("--password", default="analyst-pass")
    parser.add_argument("--roles", action="store_true")
    args = parser.parse_args(argv)

    from institutional_security.production import health, login, roles_api

    if args.login:
        print(
            json.dumps(
                login({"username": args.username, "password": args.password}),
                indent=2,
                default=str,
            )
        )
        return 0
    if args.roles:
        print(json.dumps(roles_api(), indent=2, default=str))
        return 0
    print(json.dumps(health(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())