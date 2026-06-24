"""懂球帝国家队阵容 person_id 解析（team/member API）。"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from briefing.dqd_player_stats import names_loosely_match
from briefing.scorer_match import normalize_player_name

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIONAL_IDS_PATH = os.path.join(ROOT, 'data', 'kb', 'dqd_national_team_ids.json')
TEAM_MAP_PATH = os.path.join(ROOT, 'data', 'team_name_map.json')

_TEAM_MEMBER = 'https://api.dongqiudi.com/soccer/biz/dqd/team/member/{team_id}'
_TEAM_DETAIL = 'https://api.dongqiudi.com/soccer/biz/dqd/team/detail/{team_id}'
_USER_AGENT = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
)
_HEADERS = {
    'User-Agent': _USER_AGENT,
    'Referer': 'https://topic.dongqiudi.com/',
}

# football-data / team_name_map 别名 -> seed_data 中文队名
_CN_ALIASES = {
    'Cape Verde Islands': '佛得角',
    'Congo DR': '刚果（金）',
    'Curaçao': '库拉索',
    'Czechia': '捷克',
    'Ivory Coast': '科特迪瓦',
    'Korea Republic': '韩国',
    'Saudi Arabia': '沙特',
    'United States': '美国',
    'Bosnia-Herzegovina': '波黑',
}


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _http_get_json(url: str, *, timeout: int = 30, delay_s: float = 0) -> Any:
    if delay_s:
        time.sleep(delay_s)
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', errors='replace'))


def parse_person_id(person: dict) -> str | None:
    pid = person.get('person_id')
    if pid:
        return str(pid)
    scheme = str(person.get('scheme') or '')
    if 'player/' in scheme:
        return scheme.rstrip('/').split('/')[-1]
    return None


def _norm_cn(s: str) -> str:
    s = re.sub(r'[·\-\s]', '', s or '')
    return s


def extract_team_members(payload: dict | list | None) -> list[dict]:
    """从 team/member 响应提取球员列表。"""
    members: list[dict] = []
    if not payload:
        return members

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get('person_id') or (
                node.get('scheme') and 'player/' in str(node.get('scheme'))
            ):
                pid = parse_person_id(node)
                if pid:
                    members.append({
                        'person_id': pid,
                        'name_en': node.get('person_en_name') or node.get('en_name') or '',
                        'name_cn': node.get('person_name') or node.get('name') or '',
                        'jersey': node.get('shirtnumber') or node.get('jersey_number'),
                        'position_group': node.get('position') or node.get('type'),
                    })
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    root = payload.get('data') if isinstance(payload, dict) else payload
    walk(root)

    # 去重（按 person_id）
    seen: set[str] = set()
    unique: list[dict] = []
    for m in members:
        if m['person_id'] in seen:
            continue
        seen.add(m['person_id'])
        m['name_norm'] = normalize_player_name(m['name_en'])
        m['name_cn_norm'] = _norm_cn(m['name_cn'])
        unique.append(m)
    return unique


def fetch_team_members(
    team_id: str | int,
    *,
    delay_s: float = 0,
    save_raw: bool = False,
    raw_root: str | None = None,
) -> list[dict]:
    url = _TEAM_MEMBER.format(team_id=team_id)
    try:
        data = _http_get_json(url, delay_s=delay_s)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []
    if save_raw and raw_root and isinstance(data, dict):
        from briefing.dqd_player_stats import save_raw_response
        save_raw_response(str(team_id), data, raw_root, kind='team_member')
    return extract_team_members(data)


def _name_variants(name_en: str) -> set[str]:
    norm = normalize_player_name(name_en)
    variants = {norm}
    parts = norm.split()
    if len(parts) >= 2:
        variants.add(parts[-1])
        variants.add(f'{parts[-1]} {parts[0]}')
        if len(parts) > 2:
            variants.add(' '.join(parts[1:]))
    return {v for v in variants if v}


def _players_match(canonical: dict, member: dict) -> bool:
    if names_loosely_match(canonical['name_en'], member['name_en']):
        return True
    cn_seed = _norm_cn(canonical.get('name_cn') or '')
    cn_api = member.get('name_cn_norm') or ''
    if cn_seed and cn_api and (cn_seed == cn_api or cn_seed in cn_api or cn_api in cn_seed):
        return True
    c_norm = canonical['name_norm']
    m_norm = member['name_norm']
    if c_norm and m_norm and (c_norm == m_norm or m_norm in c_norm or c_norm in m_norm):
        return True
    c_vars = _name_variants(canonical['name_en'])
    m_vars = _name_variants(member['name_en'])
    if c_vars & m_vars:
        return True
    return False


def match_jersey_member(canonical: dict, member: dict) -> bool:
    """球衣号同步：仅按英文名精确/宽松匹配，避免同姓球员误判。"""
    en_c = (canonical.get('name_en') or '').strip()
    en_m = (member.get('name_en') or '').strip()
    if en_c and en_m:
        if normalize_player_name(en_c) == normalize_player_name(en_m):
            return True
        if names_loosely_match(en_c, en_m):
            return True
        return False
    cn_seed = _norm_cn(canonical.get('name_cn') or '')
    cn_api = member.get('name_cn_norm') or _norm_cn(member.get('name_cn') or '')
    return bool(cn_seed and cn_api and cn_seed == cn_api)


def match_members_to_canonical(
    members: list[dict],
    canonical_players: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """返回 (matched, unmatched_canonical, unmatched_api)。"""
    matched: list[dict] = []
    used_members: set[str] = set()

    for player in canonical_players:
        candidates = [
            m for m in members
            if m['person_id'] not in used_members and _players_match(player, m)
        ]
        if not candidates:
            continue
        if len(candidates) == 1:
            pick = candidates[0]
            confidence = 'national_squad_exact'
        else:
            jersey = str(player.get('jersey_number') or '')
            by_jersey = [m for m in candidates if str(m.get('jersey') or '') == jersey]
            pick = by_jersey[0] if len(by_jersey) == 1 else candidates[0]
            confidence = 'national_squad_fuzzy'
        used_members.add(pick['person_id'])
        matched.append({
            'slug': player['slug'],
            'name_en': player['name_en'],
            'team_en': player['team_en'],
            'person_id': pick['person_id'],
            'api_name_en': pick['name_en'],
            'api_name_cn': pick['name_cn'],
            'match_confidence': confidence,
        })

    matched_slugs = {m['slug'] for m in matched}
    unmatched_canonical = [p for p in canonical_players if p['slug'] not in matched_slugs]
    unmatched_api = [m for m in members if m['person_id'] not in used_members]
    return matched, unmatched_canonical, unmatched_api


def scan_national_team_ids(
    team_cns: list[str],
    *,
    id_range: range | None = None,
    delay_s: float = 0.03,
    team_en_by_cn: dict[str, str] | None = None,
) -> dict[str, dict]:
    """扫描 team/detail，按中文队名（优先）或英文名匹配国家队 short team_id。"""
    wanted_cn = set(team_cns)
    wanted_en: dict[str, str] = {}
    if team_en_by_cn:
        for cn, en in team_en_by_cn.items():
            if cn in wanted_cn and en:
                wanted_en[en.lower()] = cn
    found: dict[str, dict] = {}
    scan_range = id_range or range(1, 2101)

    for tid in scan_range:
        url = _TEAM_DETAIL.format(team_id=tid)
        try:
            data = _http_get_json(url, delay_s=delay_s, timeout=3)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        bi = data.get('base_info') or {}
        cn = (bi.get('team_name') or '').strip()
        en = (bi.get('team_en_name') or '').strip()
        if cn in wanted_cn and cn not in found:
            matched_cn = cn
        elif en and en.lower() in wanted_en and wanted_en[en.lower()] not in found:
            matched_cn = wanted_en[en.lower()]
        else:
            continue
        found[matched_cn] = {
            'team_cn': cn,
            'team_en': en,
            'short_id': str(tid),
            'long_id': str(bi.get('team_id') or f'50000{tid}'),
        }
        if len(found) >= len(wanted_cn):
            break
    return found


def build_national_team_id_map(
    team_cns: list[str],
    *,
    force_scan: bool = False,
    team_en_by_cn: dict[str, str] | None = None,
) -> dict:
    existing = load_json(NATIONAL_IDS_PATH)
    if existing and not force_scan:
        by_cn = existing.get('by_cn') or existing
        if isinstance(by_cn, dict) and len(by_cn) >= len(team_cns) * 0.9:
            return existing

    scanned = scan_national_team_ids(team_cns, team_en_by_cn=team_en_by_cn)
    by_cn = scanned
    by_en: dict[str, dict] = {}
    for cn, info in scanned.items():
        if info.get('team_en'):
            by_en[info['team_en']] = info

    payload = {
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'by_cn': by_cn,
        'by_en': by_en,
        'missing_cn': [cn for cn in team_cns if cn not in by_cn],
    }
    save_json(NATIONAL_IDS_PATH, payload)
    return payload


def resolve_team_person_ids(
    team_cn: str,
    team_id: str | int,
    canonical_players: list[dict],
    *,
    delay_s: float = 0.2,
    save_raw: bool = False,
    raw_root: str | None = None,
) -> dict:
    members = fetch_team_members(
        team_id, delay_s=delay_s, save_raw=save_raw, raw_root=raw_root,
    )
    matched, unmatched_c, unmatched_api = match_members_to_canonical(members, canonical_players)
    return {
        'team_cn': team_cn,
        'team_id': str(team_id),
        'api_count': len(members),
        'matched': matched,
        'unmatched_canonical': [
            {'slug': p['slug'], 'name_en': p['name_en']} for p in unmatched_c
        ],
        'unmatched_api': [
            {'person_id': m['person_id'], 'name_en': m['name_en'], 'name_cn': m['name_cn']}
            for m in unmatched_api
        ],
    }
