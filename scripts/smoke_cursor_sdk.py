#!/usr/bin/env python3
"""Smoke test Cursor SDK with AIKey.txt."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.sdk_compat import ensure_cursor_sdk_os_compat
from briefing.secrets import read_secret


def main():
    ensure_cursor_sdk_os_compat()
    api_key = read_secret('static/basedata/AIKey.txt', 'CURSOR_API_KEY')
    if not api_key:
        print('No API key in AIKey.txt or CURSOR_API_KEY')
        sys.exit(1)
    try:
        ensure_cursor_sdk_os_compat()
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    except ImportError:
        print('Install: pip install cursor-sdk')
        sys.exit(1)

    result = Agent.prompt(
        'Reply with exactly: ok',
        AgentOptions(
            api_key=api_key,
            model='composer-2.5',
            local=LocalAgentOptions(cwd=ROOT),
        ),
    )
    print('status:', result.status)
    print('result:', (result.result or '')[:200])
    if result.status == 'error':
        sys.exit(1)


if __name__ == '__main__':
    main()
