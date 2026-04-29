#!/usr/bin/env python3
"""Mock `claude` CLI for backend tests.

Reads a fixture file (path from --fixture or env MOCK_CLAUDE_FIXTURE) and emits
each line to stdout, sleeping briefly between lines to simulate streaming.

Usage in tests:
    subprocess.Popen(
        ["python", str(mock_claude_path), "-p", "...",
         "--output-format", "stream-json"],
        env={"MOCK_CLAUDE_FIXTURE": str(fixture_path), **os.environ})
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", dest="prompt", default="")
    parser.add_argument("--output-format", default="stream-json")
    parser.add_argument("--dangerously-skip-permissions", action="store_true")
    parser.add_argument("--fixture", default=None, help="Path to fixture .jsonl")
    args = parser.parse_args()

    fixture_path = args.fixture or os.environ.get("MOCK_CLAUDE_FIXTURE")
    if not fixture_path:
        error = '{"type":"error","code":"NO_FIXTURE",' \
                '"message":"set MOCK_CLAUDE_FIXTURE","recoverable":false}'
        print(error, flush=True)
        return 1

    delay_ms = float(os.environ.get("MOCK_CLAUDE_DELAY_MS", "5"))
    fixture = Path(fixture_path)
    if not fixture.exists():
        error = (f'{{"type":"error","code":"FIXTURE_NOT_FOUND",'
                 f'"message":"{fixture}","recoverable":false}}')
        print(error, flush=True)
        return 1

    for raw_line in fixture.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        print(line, flush=True)
        if delay_ms:
            time.sleep(delay_ms / 1000.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
