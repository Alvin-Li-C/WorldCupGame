#!/usr/bin/env python3
"""Download 16 WC 2026 stadium photos (ArchDaily.cn / images.adsttc.com,国内可访问)."""
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'static', 'stadiums')

# Source: https://www.archdaily.cn/cn/993991/... (medium_jpg per venue, article order)
STADIUM_URLS = {
    'lumen.jpg': 'https://images.adsttc.com/media/images/639e/6ee3/f733/b401/701f/3b18/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_3.jpg?1671327480',
    'levis.jpg': 'https://images.adsttc.com/media/images/639e/6f86/a452/0802/91ad/4fdf/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_4.jpg?1671327641',
    'sofi.jpg': 'https://images.adsttc.com/media/images/639e/6ffb/f733/b401/701f/3b27/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_5.jpg?1671327746',
    'arrowhead.jpg': 'https://images.adsttc.com/media/images/639e/70aa/a452/0802/91ad/4ff5/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_6.jpg?1671327933',
    'att.jpg': 'https://images.adsttc.com/media/images/639e/765b/f733/b401/701f/3b31/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_8.jpg?1671329394',
    'mercedes_atlanta.jpg': 'https://images.adsttc.com/media/images/639e/76c6/f733/b401/701f/3b3a/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_9.jpg?1671329490',
    'nrg.jpg': 'https://images.adsttc.com/media/images/639e/774c/f733/b401/701f/3b42/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_9.jpg?1671329630',
    'gillette.jpg': 'https://images.adsttc.com/media/images/639e/77a7/f733/b401/701f/3b47/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_10.jpg?1671329723',
    'lincoln.jpg': 'https://images.adsttc.com/media/images/639e/7811/a452/0802/91ad/5010/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_11.jpg?1671329827',
    'hardrock.jpg': 'https://images.adsttc.com/media/images/639e/787f/a452/0802/91ad/5015/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_12.jpg?1671329940',
    'metlife.jpg': 'https://images.adsttc.com/media/images/639e/78d7/a452/0802/91ad/501d/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_13.jpg?1671330024',
    'akron.jpg': 'https://images.adsttc.com/media/images/639e/794e/f733/b401/701f/3b58/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_14.jpg?1671330147',
    'bbva.jpg': 'https://images.adsttc.com/media/images/639e/797e/a452/0802/91ad/5025/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_15.jpg?1671330178',
    'azteca.jpg': 'https://images.adsttc.com/media/images/639e/7a13/a452/0802/91ad/502e/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_16.jpg?1671330343',
    'bcplace.jpg': 'https://images.adsttc.com/media/images/639e/7a9a/a452/0802/91ad/5039/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_16.jpg?1671330477',
    'bmo.jpg': 'https://images.adsttc.com/media/images/639e/7c2b/a452/0802/91ad/503a/medium_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_17.jpg?1671330869',
}

MIN_BYTES = 8000


def download(name, url, retries=3):
    dest = os.path.join(OUT_DIR, name)
    if os.path.isfile(dest) and os.path.getsize(dest) >= MIN_BYTES:
        print(f'SKIP {name} (exists)')
        return True
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 WorldCupGame/1.0',
            'Referer': 'https://www.archdaily.cn/',
        },
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) < MIN_BYTES:
                raise ValueError(f'too small ({len(data)} bytes)')
            tmp = dest + '.part'
            with open(tmp, 'wb') as f:
                f.write(data)
            os.replace(tmp, dest)
            print(f'OK {name} ({len(data) // 1024} KB)')
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            print(f'RETRY {name} {attempt}/{retries}: {e}')
            time.sleep(attempt * 2)
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ok = sum(1 for n, u in STADIUM_URLS.items() if download(n, u))
    print(f'Done: {ok}/{len(STADIUM_URLS)} (source: ArchDaily.cn)')
    if ok < len(STADIUM_URLS):
        fallback = os.path.join(OUT_DIR, 'sofi.jpg')
        for name in STADIUM_URLS:
            path = os.path.join(OUT_DIR, name)
            if not os.path.isfile(path) or os.path.getsize(path) < MIN_BYTES:
                if os.path.isfile(fallback):
                    shutil.copy2(fallback, path)
                    print(f'FALLBACK copy -> {name}')
    return 0 if ok == len(STADIUM_URLS) else 1


if __name__ == '__main__':
    sys.exit(main())
