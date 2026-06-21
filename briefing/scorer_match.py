"""Match API goal scorers to drafted players (English-first)."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIASES_PATH = os.path.join(ROOT, 'data', 'player_name_aliases.json')
MANUAL_MAP_PATH = os.path.join(ROOT, 'data', 'scorer_manual_map.json')

REASON_LABELS = {
    'not_drafted': '非选秀球员',
    'no_name_match': '英文名未匹配',
    'ambiguous': '同队多名候选',
    'manual_map_not_drafted': '映射球员未选秀',
}


def normalize_player_name(name: str) -> str:
    if not name:
        return ''
    text = unicodedata.normalize('NFKD', name)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[`'’.·\-]", ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _name_order_variants(norm: str) -> list[str]:
    """ESPN often uses family-given order; draft DB uses given-family (Western)."""
    parts = norm.split()
    if len(parts) < 2:
        return []
    variants = []
    if len(parts) == 2:
        variants.append(f'{parts[1]} {parts[0]}')
    else:
        variants.append(' '.join(parts[1:] + [parts[0]]))
        variants.append(' '.join([parts[-1]] + parts[:-1]))
    return variants


def _load_json(path, default):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_aliases() -> dict[str, str]:
    data = _load_json(ALIASES_PATH, {})
    raw = data.get('aliases', data) if isinstance(data, dict) else {}
    return {normalize_player_name(k): v for k, v in raw.items() if isinstance(k, str)}


def load_manual_rules() -> list[dict]:
    data = _load_json(MANUAL_MAP_PATH, {'rules': []})
    return list(data.get('rules') or [])


def save_manual_rules(rules: list[dict]) -> None:
    os.makedirs(os.path.dirname(MANUAL_MAP_PATH), exist_ok=True)
    with open(MANUAL_MAP_PATH, 'w', encoding='utf-8') as f:
        json.dump({'rules': rules}, f, ensure_ascii=False, indent=2)


def add_manual_rule(
    *,
    player_id: int,
    api_scorer_en: str | None = None,
    team_api: str | None = None,
    api_scorer_id: int | None = None,
    note: str = '',
) -> dict:
    rules = load_manual_rules()
    entry = {
        'player_id': player_id,
        'note': note,
        'created_at': datetime.now().isoformat(timespec='seconds'),
    }
    if api_scorer_id is not None:
        entry['api_scorer_id'] = api_scorer_id
    if api_scorer_en:
        entry['api_scorer_en'] = api_scorer_en
    if team_api:
        entry['team_api'] = team_api
    key = (api_scorer_id, normalize_player_name(api_scorer_en or ''), (team_api or '').lower())
    replaced = False
    for i, r in enumerate(rules):
        rk = (
            r.get('api_scorer_id'),
            normalize_player_name(r.get('api_scorer_en') or ''),
            (r.get('team_api') or '').lower(),
        )
        if rk == key:
            rules[i] = entry
            replaced = True
            break
    if not replaced:
        rules.append(entry)
    save_manual_rules(rules)
    return entry


def _selection_by_id(selections):
    return {s['player_id']: s for s in selections}


def _candidates_for_team(selections, team_cn):
    return [s for s in selections if s['team_name'] == team_cn]


def _match_by_english(api_name: str, team_cn: str, selections: list[dict]) -> dict | None:
    target = normalize_player_name(api_name)
    if not target:
        return None
    pool = _candidates_for_team(selections, team_cn)
    exact = [s for s in pool if normalize_player_name(s.get('name') or '') == target]
    if len(exact) == 1:
        return exact[0]
    return None


def _apply_manual_map(event: dict, selections: list[dict]) -> dict | None:
    rules = load_manual_rules()
    by_id = _selection_by_id(selections)
    scorer_id = event.get('scorer_api_id')
    scorer_en = event.get('scorer_en') or ''
    team_api = (event.get('team_en') or '').lower()
    norm_name = normalize_player_name(scorer_en)

    for rule in rules:
        rid = rule.get('api_scorer_id')
        sid = scorer_id
        if rid is not None and sid is not None and str(rid) == str(sid):
            return by_id.get(rule['player_id'])
        if rule.get('api_scorer_en') and rule.get('team_api'):
            if (
                normalize_player_name(rule['api_scorer_en']) == norm_name
                and rule['team_api'].lower() == team_api
            ):
                return by_id.get(rule['player_id'])
    return None


def match_scorer_to_selection(event: dict, selections: list[dict]) -> tuple[dict | None, str]:
    team_cn = event.get('team_cn')
    scorer_en = event.get('scorer_en') or ''
    if not team_cn or not scorer_en:
        return None, 'no_name_match'

    pool = _candidates_for_team(selections, team_cn)
    if not pool:
        return None, 'not_drafted'

    aliases = load_aliases()
    norm = normalize_player_name(scorer_en)
    names_to_try = [scorer_en]
    alias_target = aliases.get(norm)
    if alias_target:
        names_to_try.append(alias_target)
    for variant in _name_order_variants(norm):
        names_to_try.append(variant)

    for name in names_to_try:
        sel = _match_by_english(name, team_cn, selections)
        if sel:
            return sel, ''

    manual = _apply_manual_map(event, selections)
    if manual:
        if manual['player_id'] in _selection_by_id(selections):
            return manual, ''
        return None, 'manual_map_not_drafted'

    parts = normalize_player_name(scorer_en).split()
    if len(parts) == 1 and len(pool) > 1:
        first = parts[0]
        by_first = [
            s for s in pool
            if normalize_player_name(s.get('name') or '').split()[0:1] == [first]
        ]
        if len(by_first) == 1:
            return by_first[0], ''
        return None, 'ambiguous'

    # API full name vs draft surname-only (e.g. Connor Metcalfe -> Metcalfe).
    if len(parts) >= 2:
        last = parts[-1]
        by_last = [
            s for s in pool
            if normalize_player_name(s.get('name') or '') == last
        ]
        if len(by_last) == 1:
            return by_last[0], ''

    return None, 'no_name_match'
