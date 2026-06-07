#!/usr/bin/env python3
"""Download 16 WC 2026 host stadium photos into static/stadiums/."""
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'static', 'stadiums')

# Wikimedia Commons — host venue photos (1280px thumbs)
STADIUM_URLS = {
    'azteca.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Estadio_Azteca_aerial_view.jpg/1280px-Estadio_Azteca_aerial_view.jpg',
    'akron.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Estadio_Akron_%28cropped%29.jpg/1280px-Estadio_Akron_%28cropped%29.jpg',
    'bbva.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Estadio_BBVA_Bancomer_Monterrey.jpg/1280px-Estadio_BBVA_Bancomer_Monterrey.jpg',
    'mercedes_atlanta.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Mercedes-Benz_Stadium_aerial.jpg/1280px-Mercedes-Benz_Stadium_aerial.jpg',
    'gillette.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Gillette_Stadium_aerial.jpg/1280px-Gillette_Stadium_aerial.jpg',
    'metlife.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/MetLife_Stadium_exterior.jpg/1280px-MetLife_Stadium_exterior.jpg',
    'lincoln.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Lincoln_Financial_Field_-_aerial.jpg/1280px-Lincoln_Financial_Field_-_aerial.jpg',
    'lumen.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/CenturyLink_Field_panorama_2013.jpg/1280px-CenturyLink_Field_panorama_2013.jpg',
    'levis.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Levi%27s_Stadium_exterior.jpg/1280px-Levi%27s_Stadium_exterior.jpg',
    'sofi.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/SoFi_Stadium_interior_%28American_football%29.jpg/1280px-SoFi_Stadium_interior_%28American_football%29.jpg',
    'bcplace.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/BC_Place_Stadium.jpg/1280px-BC_Place_Stadium.jpg',
    'bmo.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/BMO_Field_aerial.jpg/1280px-BMO_Field_aerial.jpg',
    'att.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/AT%26T_Stadium_aerial.jpg/1280px-AT%26T_Stadium_aerial.jpg',
    'nrg.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/NRG_Stadium_aerial.jpg/1280px-NRG_Stadium_aerial.jpg',
    'hardrock.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Hard_Rock_Stadium_%28Aerial%29.jpg/1280px-Hard_Rock_Stadium_%28Aerial%29.jpg',
    'arrowhead.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Arrowhead_Stadium_aerial.jpg/1280px-Arrowhead_Stadium_aerial.jpg',
}


def download(name, url):
    dest = os.path.join(OUT_DIR, name)
    req = urllib.request.Request(url, headers={'User-Agent': 'WorldCupGame/1.0'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(dest, 'wb') as f:
        f.write(data)
    return len(data)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ok, fail = 0, []
    for name, url in STADIUM_URLS.items():
        try:
            size = download(name, url)
            print(f'OK {name} ({size // 1024} KB)')
            ok += 1
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f'FAIL {name}: {e}')
            fail.append(name)
    print(f'Done: {ok}/{len(STADIUM_URLS)}')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
