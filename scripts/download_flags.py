#!/usr/bin/env python3
"""Download flag PNGs for WC teams (flagcdn.com, 国内一般可访问)."""
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'static', 'flags')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from generate_fixtures_2026 import FLAG_CODES

EXTRA = {'xx': 'un'}


def download(code):
    dest = os.path.join(OUT, f'{code}.png')
    if os.path.isfile(dest) and os.path.getsize(dest) > 500:
        print(f'SKIP {code}')
        return True
    src = EXTRA.get(code, code)
    url = f'https://flagcdn.com/w320/{src}.png'
    req = urllib.request.Request(url, headers={'User-Agent': 'WorldCupGame/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        print(f'OK {code}')
        return True
    except Exception as e:
        print(f'FAIL {code}: {e}')
        return False


def main():
    os.makedirs(OUT, exist_ok=True)
    codes = sorted(set(FLAG_CODES.values()) | set(EXTRA))
    ok = sum(1 for c in codes if download(c))
    print(f'Done {ok}/{len(codes)}')
    return 0 if ok == len(codes) else 1


if __name__ == '__main__':
    sys.exit(main())
