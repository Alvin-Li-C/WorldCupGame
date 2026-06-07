"""Resolve WC 2026 stadium photo filenames from API venue names."""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_PATH = os.path.join(ROOT, 'data', 'stadium_photo_map.json')


def _load_map():
    if not os.path.isfile(MAP_PATH):
        return {'venues': [], 'default_photo': 'azteca.jpg'}
    with open(MAP_PATH, encoding='utf-8') as f:
        return json.load(f)


def resolve_stadium_photo(venue_name: str | None, fallback_photo: str = 'azteca.jpg') -> str:
    if not venue_name:
        return fallback_photo
    text = venue_name.lower()
    data = _load_map()
    for entry in data.get('venues') or []:
        for key in entry.get('keys') or []:
            if key.lower() in text:
                return entry['photo']
    return data.get('default_photo') or fallback_photo


def resolve_stadium_label(venue_name: str | None, city: str | None = None) -> str:
    if venue_name and city:
        return f'{venue_name} · {city}'
    if venue_name:
        return venue_name
    return 'TBD'
