"""Console entry point for Codex hooks."""

from __future__ import annotations

import argparse

from .hooks import hook_main


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", choices=("session-start", "stop"))
    args = parser.parse_args()
    raise SystemExit(hook_main(args.event))


if __name__ == "__main__":
    main()
