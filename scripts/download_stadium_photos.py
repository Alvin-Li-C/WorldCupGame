#!/usr/bin/env python3
"""Download 16 WC 2026 stadium photos (ArchDaily.cn / images.adsttc.com,国内可访问)."""
import argparse
import io
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'static', 'stadiums')

# Source: https://www.archdaily.cn/cn/993991/... — use large_jpg (~2000px), not medium_jpg (~528px)
STADIUM_URLS = {
    # Lumen Field · Seattle (ArchDaily 2026 WC list, © Kirk Wester)
    'lumen.jpg': 'https://images.adsttc.com/media/images/639e/6ee3/f733/b401/701f/3b18/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_3.jpg?1671327480',
    'levis.jpg': 'https://images.adsttc.com/media/images/639e/6f86/a452/0802/91ad/4fdf/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_4.jpg?1671327641',
    'sofi.jpg': 'https://images.adsttc.com/media/images/639e/6ffb/f733/b401/701f/3b27/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_5.jpg?1671327746',
    # Seating bowl close-up (Levi's Stadium gallery)
    'arrowhead.jpg': 'https://images.adsttc.com/media/images/56c3/ac19/e58e/ced9/6100/01b5/large_jpg/LS-01_6006A2.jpg?1455664137',
    'att.jpg': 'https://images.adsttc.com/media/images/639e/765b/f733/b401/701f/3b31/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_8.jpg?1671329394',
    # Mercedes-Benz Stadium · Atlanta interior bowl (HOK / ArchDaily gallery)
    'mercedes_atlanta.jpg': 'https://images.adsttc.com/media/images/5a0e/f16f/b22e/382f/e000/00ed/large_jpg/Falcon-133.jpg?1510928732',
    # Houston soccer bowl interior (BBVA Compass / Populous gallery — same city)
    'nrg.jpg': 'https://images.adsttc.com/media/images/522f/47ea/e8e4/4e33/3b00/00ad/large_jpg/HOUTXSOC_0018_Lyons.jpg?1378830294',
    'gillette.jpg': 'https://images.adsttc.com/media/images/639e/77a7/f733/b401/701f/3b47/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_10.jpg?1671329723',
    'lincoln.jpg': 'https://images.adsttc.com/media/images/639e/7811/a452/0802/91ad/5010/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_11.jpg?1671329827',
    'hardrock.jpg': 'https://images.adsttc.com/media/images/639e/787f/a452/0802/91ad/5015/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_12.jpg?1671329940',
    'metlife.jpg': 'https://images.adsttc.com/media/images/639e/78d7/a452/0802/91ad/501d/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_13.jpg?1671330024',
    'akron.jpg': 'https://images.adsttc.com/media/images/639e/794e/f733/b401/701f/3b58/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_14.jpg?1671330147',
    'bbva.jpg': 'https://images.adsttc.com/media/images/639e/797e/a452/0802/91ad/5025/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_15.jpg?1671330178',
    'azteca.jpg': 'https://images.adsttc.com/media/images/639e/7a13/a452/0802/91ad/502e/large_jpg/explore-the-full-list-of-football-stadiums-for-the-2026-fifa-world-cup-in-united-states-mexico-and-canada_16.jpg?1671330343',
    # Covered bowl interior (U.S. Bank Stadium gallery — similar enclosed match-day feel)
    'bcplace.jpg': 'https://images.adsttc.com/media/images/56f8/6d52/e58e/ce8d/2000/010a/large_jpg/Interior_from_East.jpg?1459121470',
    # Soccer bowl close-up (BBVA Compass gallery — Toronto BMO is soccer-specific)
    'bmo.jpg': 'https://images.adsttc.com/media/images/522f/477d/e8e4/4e33/3b00/00a9/large_jpg/HOUTXSOC_0029_Lyons.jpg?1378830183',
}

# ArchDaily large_jpg is only ~1000px for some venues (Wikimedia blocked from CN).
MIN_WIDTH_BY_FILE = {
    'bbva.jpg': 900,
}

MIN_BYTES = 120_000
MIN_WIDTH = 1600


def image_width(path):
    if not Image or not os.path.isfile(path):
        return 0
    try:
        with Image.open(path) as im:
            return im.size[0]
    except OSError:
        return 0


def min_width_for(name):
    return MIN_WIDTH_BY_FILE.get(name, MIN_WIDTH)


def download(name, url, force=False, retries=3):
    dest = os.path.join(OUT_DIR, name)
    need_w = min_width_for(name)
    width = image_width(dest)
    if not force and os.path.isfile(dest) and os.path.getsize(dest) >= MIN_BYTES and width >= need_w:
        print(f'SKIP {name} ({width}px, already HD)')
        return True
    referer = 'https://commons.wikimedia.org/' if 'wikimedia.org' in url else 'https://www.archdaily.cn/'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 WorldCupGame/1.0',
            'Referer': referer,
        },
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if len(data) < MIN_BYTES:
                raise ValueError(f'too small ({len(data)} bytes)')
            if Image:
                w, h = Image.open(io.BytesIO(data)).size
                if w < min_width_for(name):
                    raise ValueError(f'width too low ({w}x{h}, need {min_width_for(name)})')
            tmp = dest + '.part'
            with open(tmp, 'wb') as f:
                f.write(data)
            os.replace(tmp, dest)
            dim = f'{w}x{h}' if Image else '?'
            print(f'OK {name} ({len(data) // 1024} KB, {dim})')
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            print(f'RETRY {name} {attempt}/{retries}: {e}')
            time.sleep(attempt * 2)
    return False


def main():
    parser = argparse.ArgumentParser(description='Download WC 2026 stadium backdrop photos')
    parser.add_argument('--force', action='store_true', help='Re-download even if file looks HD')
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    ok = sum(1 for n, u in STADIUM_URLS.items() if download(n, u, force=args.force))
    print(f'Done: {ok}/{len(STADIUM_URLS)} (ArchDaily large_jpg)')
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
