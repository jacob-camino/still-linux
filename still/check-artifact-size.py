#!/usr/bin/env python3
"""Reject missing/oversized artifact inputs before GitHub storage is used."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-gib", type=int, required=True)
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args()
    if args.max_gib <= 0:
        parser.error("--max-gib must be positive")
    total = 0
    for path in args.files:
        if not path.is_file():
            parser.error(f"artifact input is not a file: {path}")
        total += path.stat().st_size
    print(f"Artifact inputs: {total / 1024 ** 3:.3f} GiB; limit: {args.max_gib} GiB")
    if total == 0 or total > args.max_gib * 1024 ** 3:
        parser.error("artifact is empty or exceeds the reviewed storage allowance")


if __name__ == "__main__":
    main()
