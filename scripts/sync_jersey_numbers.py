#!/usr/bin/env python3
"""从懂球帝国家队阵容同步真实球衣号码到 seed_data、数据库、球员 KB 与 history_index。

写入策略：仅就地修改 jersey_number 字段，不重写整段数据或整文件。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SEED_PATH = os.path.join(ROOT, 'seed_data.py')
NATIONAL_IDS_PATH = os.path.join(ROOT, 'data', 'kb', 'dqd_national_team_ids.json')
TEAM_MEMBER_DIR = os.path.join(ROOT, 'data', 'kb', 'wc_player_kb', 'raw', 'dqd', 'team_member')
KB_PLAYERS_DIR = os.path.join(ROOT, 'data', 'kb', 'wc_player_kb', 'players')
HISTORY_PATH = os.path.join(ROOT, 'data', 'briefing', 'history_index.json')
LINEUPS_PATH = os.path.join(ROOT, 'data', 'briefing', 'match_lineups.json')
FIXTURES_PATH = os.path.join(ROOT, 'data', 'fixtures_2026.json')
CANONICAL_PATH = os.path.join(ROOT, 'data', 'kb', 'wc_squad_canonical.json')

# seed_data 球员行：('Name', '中文', 号码, 'POS'),
_PLAYER_TUPLE_RE = re.compile(
    r"^(\s*\('(?:[^'\\]|\\.)*',\s*'(?:[^'\\]|\\.)*',\s*)(\d+)(,\s*'(?:GK|DF|MF|FW)'\),)\s*$"
)
_IDENTITY_JERSEY_RE = re.compile(r'("jersey_number"\s*:\s*)(\d+)')
_CANONICAL_JERSEY_RE = re.compile(r'("jersey_number"\s*:\s*)(\d+)')


def _load_json(path: str, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _models():
    from models import DB_PATH, get_db
    return DB_PATH, get_db


def _seed():
    from seed_data import PLAYERS_DATA, TEAMS
    return PLAYERS_DATA, TEAMS


def _dqd_helpers():
    from briefing.dqd_person_resolve import (
        extract_team_members,
        match_jersey_member,
    )
    from briefing.scorer_match import normalize_player_name
    return match_jersey_member, extract_team_members, normalize_player_name


def _player_key(team_cn: str, name_en: str) -> tuple[str, str]:
    _, _, normalize_player_name = _dqd_helpers()
    return team_cn, normalize_player_name(name_en)


def collect_lineup_jerseys() -> dict[tuple[str, str], int]:
    """match_lineups + fixtures 作为号码补充来源。"""
    lineups = _load_json(LINEUPS_PATH, {}) or {}
    fixtures_raw = _load_json(FIXTURES_PATH, {}) or {}
    fixtures = fixtures_raw.get('fixtures') if isinstance(fixtures_raw, dict) else fixtures_raw
    fixtures = fixtures or []
    fixture_teams: dict[str, tuple[str, str]] = {}
    for fx in fixtures:
        if not isinstance(fx, dict):
            continue
        fid = str(fx.get('fixture_id') or fx.get('id') or '')
        home = fx.get('home_team_cn') or fx.get('home_team') or ''
        away = fx.get('away_team_cn') or fx.get('away_team') or ''
        if fid and home and away:
            fixture_teams[fid] = (home, away)

    jerseys: dict[tuple[str, str], int] = {}
    for fid, entry in lineups.items():
        teams = fixture_teams.get(str(fid))
        if not teams:
            continue
        home_cn, away_cn = teams
        for side, team_cn in (('home', home_cn), ('away', away_cn)):
            for pl in entry.get(side) or []:
                jersey = pl.get('jersey')
                full = pl.get('full') or pl.get('display') or ''
                if not jersey or not full:
                    continue
                try:
                    num = int(str(jersey).strip())
                except ValueError:
                    continue
                jerseys[_player_key(team_cn, full)] = num
    return jerseys


def build_update_map() -> tuple[dict[tuple[str, str], int], list[str]]:
    """返回 {(team_cn, name_norm): new_jersey} 与日志。"""
    match_jersey_member, extract_team_members, normalize_player_name = _dqd_helpers()
    PLAYERS_DATA, TEAMS = _seed()
    national = _load_json(NATIONAL_IDS_PATH, {}) or {}
    by_cn = national.get('by_cn') or national
    lineups = collect_lineup_jerseys()
    updates: dict[tuple[str, str], int] = {}
    logs: list[str] = []

    for team_cn, _group, _flag in TEAMS:
        members: list[dict] = []
        info = by_cn.get(team_cn)
        if info:
            fp = os.path.join(TEAM_MEMBER_DIR, f"{info['short_id']}.json")
            if os.path.isfile(fp):
                with open(fp, encoding='utf-8') as f:
                    payload = json.load(f)
                members = extract_team_members(payload)

        used_members: set[str] = set()
        for name_en, name_cn, old_jersey, _pos in PLAYERS_DATA.get(team_cn, []):
            player = {
                'name_en': name_en,
                'name_cn': name_cn,
                'name_norm': normalize_player_name(name_en),
                'jersey_number': old_jersey,
            }
            new_jersey = None

            candidates = [
                m for m in members
                if m.get('person_id') not in used_members
                and match_jersey_member(player, m)
                and m.get('jersey')
            ]
            if len(candidates) == 1:
                pick = candidates[0]
            elif len(candidates) > 1:
                jersey = str(old_jersey)
                by_jersey = [m for m in candidates if str(m.get('jersey') or '') == jersey]
                pick = by_jersey[0] if len(by_jersey) == 1 else candidates[0]
                logs.append(f'[WARN] {team_cn} / {name_en}: {len(candidates)} EN matches, picked {pick.get("name_en")}')
            else:
                pick = None

            if pick:
                used_members.add(str(pick['person_id']))
                try:
                    new_jersey = int(str(pick['jersey']).strip())
                except ValueError:
                    pass

            if new_jersey is None:
                player_norm = normalize_player_name(name_en)
                for (t_cn, name_norm), num in lineups.items():
                    if t_cn != team_cn or name_norm != player_norm:
                        continue
                    new_jersey = num
                    break

            if new_jersey is None:
                logs.append(f'[MISS] {team_cn} / {name_en}')
                continue
            if new_jersey != old_jersey:
                updates[_player_key(team_cn, name_en)] = new_jersey
                logs.append(f'[CHG] {team_cn} / {name_en}: #{old_jersey} -> #{new_jersey}')
    return updates, logs


def _parse_players_data_from_source(content: str) -> dict[str, list[tuple]]:
    tree = ast.parse(content)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'PLAYERS_DATA':
                    out: dict[str, list[tuple]] = {}
                    for key_node, val_node in zip(node.value.keys, node.value.values):
                        team_cn = ast.literal_eval(key_node)
                        out[team_cn] = [ast.literal_eval(x) for x in val_node.elts]
                    return out
    raise RuntimeError('PLAYERS_DATA not found in seed_data.py')


def _patch_text_jersey_only(old_text: str, new_text: str, field_name: str = 'jersey_number') -> bool:
    """确认两段文本除指定数字字段外完全一致（用于写前校验）。"""
    def strip_jerseys(text: str) -> str:
        if field_name == 'jersey_number':
            text = _IDENTITY_JERSEY_RE.sub(r'\1__JERSEY__', text)
            text = _CANONICAL_JERSEY_RE.sub(r'\1__JERSEY__', text)
        return text

    return strip_jerseys(old_text) == strip_jerseys(new_text)


def update_seed_data(updates: dict[tuple[str, str], int]) -> int:
    """仅替换球员元组中的号码整数，保留行内姓名/位置等原文。"""
    with open(SEED_PATH, encoding='utf-8') as f:
        lines = f.readlines()

    players = _parse_players_data_from_source(''.join(lines))
    changed = 0
    new_lines: list[str] = []
    current_team: str | None = None

    for line in lines:
        stripped = line.rstrip('\n')
        team_m = re.match(r"\s+'([^']+)':\s*\[", stripped)
        if team_m:
            current_team = team_m.group(1)

        m = _PLAYER_TUPLE_RE.match(stripped)
        if m and current_team:
            name_en, _name_cn, old_jersey, _pos = players[current_team].pop(0)
            new_jersey = updates.get(_player_key(current_team, name_en), old_jersey)
            if new_jersey != old_jersey:
                changed += 1
                stripped = f'{m.group(1)}{new_jersey}{m.group(3)}'
        new_lines.append(stripped + '\n')

    new_content = ''.join(new_lines)
    with open(SEED_PATH, encoding='utf-8') as f:
        old_content = f.read()
    # 除号码外内容应一致
    old_players = _parse_players_data_from_source(old_content)
    new_players = _parse_players_data_from_source(new_content)
    for team in old_players:
        for old, new in zip(old_players[team], new_players[team]):
            if old[0] != new[0] or old[1] != new[1] or old[3] != new[3]:
                raise RuntimeError(f'非号码字段被改动: {team} {old} -> {new}')

    with open(SEED_PATH, 'w', encoding='utf-8', newline='') as f:
        f.write(new_content)
    return changed


def update_database(updates: dict[tuple[str, str], int]) -> int:
    DB_PATH, get_db = _models()
    if not os.path.isfile(DB_PATH):
        return 0
    db = get_db()
    changed = 0
    rows = db.execute('''
        SELECT p.id, p.name, p.jersey_number, t.name AS team_cn
        FROM players p
        JOIN teams t ON t.id = p.team_id
    ''').fetchall()
    for row in rows:
        key = _player_key(row['team_cn'], row['name'])
        new_jersey = updates.get(key)
        if new_jersey is None or new_jersey == row['jersey_number']:
            continue
        db.execute(
            'UPDATE players SET jersey_number = ? WHERE id = ?',
            (new_jersey, row['id']),
        )
        changed += 1
    db.commit()
    db.close()
    return changed


def _patch_json_file_jersey(fp: str, new_jersey: int, old_jersey: int) -> bool:
    """就地替换 identity.jersey_number，不重排 JSON。"""
    with open(fp, encoding='utf-8') as f:
        text = f.read()
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        if int(m.group(2)) == old_jersey:
            count += 1
            return f'{m.group(1)}{new_jersey}'
        return m.group(0)

    new_text, n = _IDENTITY_JERSEY_RE.subn(repl, text, count=1)
    if n != 1 or count != 1:
        return False
    if _patch_text_jersey_only(text, new_text):
        with open(fp, 'w', encoding='utf-8', newline='') as f:
            f.write(new_text)
        return True
    raise RuntimeError(f'KB 文件补丁校验失败: {fp}')


def update_kb_players(updates: dict[tuple[str, str], int]) -> int:
    changed = 0
    if not os.path.isdir(KB_PLAYERS_DIR):
        return 0
    for fn in os.listdir(KB_PLAYERS_DIR):
        if not fn.endswith('.json'):
            continue
        fp = os.path.join(KB_PLAYERS_DIR, fn)
        with open(fp, encoding='utf-8') as f:
            data = json.load(f)
        ident = data.get('identity') or {}
        team_cn = ident.get('team_cn') or ''
        name_en = ident.get('name_en') or ''
        old = ident.get('jersey_number')
        key = _player_key(team_cn, name_en)
        new_jersey = updates.get(key)
        if new_jersey is None or new_jersey == old:
            continue
        if _patch_json_file_jersey(fp, new_jersey, old):
            changed += 1
    return changed


def update_canonical_squad(updates: dict[tuple[str, str], int]) -> int:
    if not os.path.isfile(CANONICAL_PATH):
        return 0
    with open(CANONICAL_PATH, encoding='utf-8') as f:
        text = f.read()
    data = json.loads(text)
    changed = 0
    for pl in data.get('players') or []:
        key = _player_key(pl.get('team_cn', ''), pl.get('name_en', ''))
        if key not in updates:
            continue
        old = pl.get('jersey_number')
        new = updates[key]
        if old == new:
            continue
        # 每个球员对象只替换对应 slug 后紧跟的 jersey_number
        slug = re.escape(pl.get('slug', ''))
        pattern = re.compile(
            rf'("slug"\s*:\s*"{slug}"[\s\S]*?"jersey_number"\s*:\s*){old}\b'
        )
        new_text, n = pattern.subn(rf'\g<1>{new}', text, count=1)
        if n != 1:
            raise RuntimeError(f'canonical 未找到 {pl.get("slug")} 的 jersey_number')
        text = new_text
        changed += 1
    if changed:
        with open(CANONICAL_PATH, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
    return changed


def update_history_index() -> int:
    """仅替换 our_scorers 块内与 player_id 对应的 jersey_number 行。"""
    DB_PATH, get_db = _models()
    if not os.path.isfile(HISTORY_PATH) or not os.path.isfile(DB_PATH):
        return 0
    db = get_db()
    jersey_by_id = {
        row['id']: row['jersey_number']
        for row in db.execute('SELECT id, jersey_number FROM players').fetchall()
    }
    db.close()

    with open(HISTORY_PATH, encoding='utf-8') as f:
        text = f.read()

    changed = 0
    for pid, jersey in jersey_by_id.items():
        # 在含该 player_id 的 scorer 对象中替换 jersey_number
        pattern = re.compile(
            rf'("player_id"\s*:\s*{pid}\s*,[\s\S]*?"jersey_number"\s*:\s*)\d+'
        )
        new_text, n = pattern.subn(rf'\g<1>{jersey}', text, count=1)
        if n:
            text = new_text
            changed += 1

    if changed:
        with open(HISTORY_PATH, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
    return changed


def verify_against_baseline(baseline_seed: str | None = None) -> list[str]:
    """校验当前 seed_data 相对基线仅号码不同。"""
    issues: list[str] = []
    with open(SEED_PATH, encoding='utf-8') as f:
        cur = f.read()
    if baseline_seed:
        old_players = _parse_players_data_from_source(baseline_seed)
    else:
        return issues
    new_players = _parse_players_data_from_source(cur)
    for team in old_players:
        for old, new in zip(old_players[team], new_players.get(team, [])):
            if old[0] != new[0] or old[1] != new[1] or old[3] != new[3]:
                issues.append(f'非号码字段变化: {team} {old} -> {new}')
    return issues


def apply_db_from_seed() -> int:
    """生产环境：将 draft.db 的 jersey_number 与 seed_data.PLAYERS_DATA 对齐（不依赖懂球帝）。"""
    DB_PATH, get_db = _models()
    PLAYERS_DATA, _TEAMS = _seed()
    if not os.path.isfile(DB_PATH):
        return 0
    db = get_db()
    changed = 0
    for team_cn, squad in PLAYERS_DATA.items():
        for name_en, _name_cn, jersey, _pos in squad:
            row = db.execute('''
                SELECT p.id, p.jersey_number
                FROM players p
                JOIN teams t ON t.id = p.team_id
                WHERE t.name = ? AND p.name = ?
            ''', (team_cn, name_en)).fetchone()
            if not row or row['jersey_number'] == jersey:
                continue
            db.execute(
                'UPDATE players SET jersey_number = ? WHERE id = ?',
                (jersey, row['id']),
            )
            changed += 1
    db.commit()
    db.close()
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description='同步真实球衣号码（仅修改 jersey_number）')
    parser.add_argument('--dry-run', action='store_true', help='仅预览变更')
    parser.add_argument(
        '--db-from-seed',
        action='store_true',
        help='生产环境：仅将 draft.db / history_index 与 seed_data 对齐（git pull 后用）',
    )
    args = parser.parse_args()

    if args.db_from_seed:
        DB_PATH, get_db = _models()
        PLAYERS_DATA, _TEAMS = _seed()
        if args.dry_run:
            pending = 0
            if os.path.isfile(DB_PATH):
                db = get_db()
                for team_cn, squad in PLAYERS_DATA.items():
                    for name_en, _cn, jersey, _pos in squad:
                        row = db.execute('''
                            SELECT p.jersey_number FROM players p
                            JOIN teams t ON t.id = p.team_id
                            WHERE t.name = ? AND p.name = ?
                        ''', (team_cn, name_en)).fetchone()
                        if row and row['jersey_number'] != jersey:
                            pending += 1
                            print(f'[CHG] {team_cn} / {name_en}: #{row["jersey_number"]} -> #{jersey}')
                db.close()
            print(f'\n待更新数据库: {pending} 条')
            return 0
        db_n = apply_db_from_seed()
        hist_n = update_history_index()
        print(f'已从 seed_data 对齐数据库: {db_n} 条（仅 jersey_number）')
        print(f'已更新 history_index: {hist_n} 条（仅 our_scorers.jersey_number）')
        return 0

    updates, logs = build_update_map()
    chg_logs = [l for l in logs if l.startswith('[CHG]')]
    miss_logs = [l for l in logs if l.startswith('[MISS]')]

    print(f'待更新: {len(updates)} 名球员')
    print(f'未匹配: {len(miss_logs)} 名球员')
    for line in chg_logs[:20]:
        print(line)
    if len(chg_logs) > 20:
        print(f'... 另有 {len(chg_logs) - 20} 条变更')
    if miss_logs:
        print('\n未匹配球员:')
        for line in miss_logs[:20]:
            print(line)
        if len(miss_logs) > 20:
            print(f'... 另有 {len(miss_logs) - 20} 名')

    if args.dry_run:
        return 0

    if not updates:
        print('\n无需更新。')
        return 0

    seed_n = update_seed_data(updates)
    db_n = update_database(updates)
    kb_n = update_kb_players(updates)
    hist_n = update_history_index()
    canon_n = update_canonical_squad(updates)

    print(f'\n已写入 seed_data.py: {seed_n} 条（仅号码）')
    print(f'已更新数据库: {db_n} 条（仅 jersey_number 列）')
    print(f'已更新球员 KB: {kb_n} 条（仅 identity.jersey_number）')
    print(f'已更新 history_index: {hist_n} 条（仅 our_scorers.jersey_number）')
    print(f'已更新 canonical squad: {canon_n} 条（仅 jersey_number）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
