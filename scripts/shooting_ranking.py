"""xG Proxy + Bayesian Shrinkage Algorithm for WCQ Player Shooting Rankings
Uses Shots on Target (SoT) as a simplified xG proxy, with Bayesian shrinkage
for small-sample robustness. Runs Monte Carlo simulation for rank ranges.
"""
import json
import os
import sys
import random
import statistics
import unicodedata
from collections import defaultdict, Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# ── Build player name -> Chinese name mapping from seed_data ──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seed_data import PLAYERS_DATA

_SLUG_TO_CN = {
    'Mexico': '\u58a8\u897f\u54e5', 'Czechia': '\u6377\u514b', 'South-Africa': '\u5357\u975e', 'Korea-Republic': '\u97e9\u56fd',
    'Canada': '\u52a0\u62ff\u5927', 'Bosnia-and-Herzegovina': '\u6ce2\u9ed1', 'Qatar': '\u5361\u5854\u5c14', 'Switzerland': '\u745e\u58eb',
    'Brazil': '\u5df4\u897f', 'Haiti': '\u6d77\u5730', 'Morocco': '\u6469\u6d1b\u54e5', 'Scotland': '\u82cf\u683c\u5170',
    'United-States': '\u7f8e\u56fd', 'Australia': '\u6fb3\u5927\u5229\u4e9a', 'Paraguay': '\u5df4\u62c9\u572d', 'Turkiye': '\u571f\u8033\u5176',
    'Curacao': '\u5e93\u62c9\u7d22', 'Ecuador': '\u5384\u74dc\u591a\u5c14', 'Germany': '\u5fb7\u56fd', 'Cote-dIvoire': '\u79d1\u7279\u8fea\u74e6',
    'Netherlands': '\u8377\u5170', 'Japan': '\u65e5\u672c', 'Sweden': '\u745e\u5178', 'Tunisia': '\u7a81\u5c3c\u65af',
    'Belgium': '\u6bd4\u5229\u65f6', 'Egypt': '\u57c3\u53ca', 'IR-Iran': '\u4f0a\u6717', 'New-Zealand': '\u65b0\u897f\u5170',
    'Cape-Verde': '\u4f5b\u5f97\u89d2', 'Saudi-Arabia': '\u6c99\u7279', 'Spain': '\u897f\u73ed\u7259', 'Uruguay': '\u4e4c\u62c9\u572d',
    'France': '\u6cd5\u56fd', 'Norway': '\u632a\u5a01', 'Senegal': '\u585e\u5185\u52a0\u5c14', 'Iraq': '\u4f0a\u62c9\u514b',
    'Algeria': '\u963f\u5c14\u53ca\u5229\u4e9a', 'Argentina': '\u963f\u6839\u5ef7', 'Austria': '\u5965\u5730\u5229', 'Jordan': '\u7ea6\u65e6',
    'Colombia': '\u54e5\u4f26\u6bd4\u4e9a', 'Congo-DR': '\u521a\u679c\uff08\u91d1\uff09', 'Portugal': '\u8461\u8404\u7259', 'Uzbekistan': '\u4e4c\u5179\u522b\u514b\u65af\u5766',
    'Croatia': '\u514b\u7f57\u5730\u4e9a', 'England': '\u82f1\u683c\u5170', 'Ghana': '\u52a0\u7eb3', 'Panama': '\u5df4\u62ff\u9a6c',
}

def _normalize_name(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

_CN_NAME_MAP = {}
_CN_NAME_NORM = {}
for _team_cn, _squad in PLAYERS_DATA.items():
    for _name, _name_cn, _num, _pos in _squad:
        if _name_cn:
            _CN_NAME_MAP[_name] = _name_cn
            _CN_NAME_NORM[_normalize_name(_name)] = _name_cn

def _get_cn_name(eng_name):
    if eng_name in _CN_NAME_MAP:
        return _CN_NAME_MAP[eng_name]
    return _CN_NAME_NORM.get(_normalize_name(eng_name), "")

_CN_NAME_OVERRIDE = {
    # Korean WCQ-format names → Chinese (all 13 WCQ players)
    'Son Heung-min': '孙兴慜', 'Cho Gue-sung': '曹圭成', 'Lee Kang-in': '李刚仁',
    'Oh Hyeon-gyu': '吴贤揆', 'Hwang In-beom': '黄仁范', 'Lee Jae-sung': '李在城',
    'Hwang Hee-chan': '黄喜灿', 'Paik Seung-ho': '白昇浩', 'Lee Dong-gyeong': '李东炅',
    'Kim Min-jae': '金玟哉', 'Seol Young-woo': '薛英佑', 'Jo Hyeon-woo': '赵贤祐',
    'Kim Seung-gyu': '金承奎',
    # Korean WCQ-format names for remaining seed players (no WCQ data but prevents future dupes)
    'Bum-Keun Song': '宋范根', 'Moon-Hwan Kim': '金纹奂', 'Min-Jae Kim': '金玟哉',
    'Tae-Hyun Kim': '金太炫', 'Jin-Seob Park': '朴镇燮', 'Young-Woo Seol': '薛英佑',
    'Jin-Gyu Kim': '金镇圭', 'Jun-Ho Bae': '裴峻浩', 'Seung-Ho Paik': '白昇浩',
    'Hyun-Jun Yang': '杨贤俊', 'Ji-Sung Eom': '严智星', 'Dong-Gyeong Lee': '李东炅',
    'Heung-Min Son': '孙兴慜', 'Hyeon-Gyu Oh': '吴贤揆', 'Gue-Sung Cho': '曹圭成',
    'In-Beom Hwang': '黄仁范', 'Hee-Chan Hwang': '黄喜灿', 'Kang-In Lee': '李刚仁',
    'Jae-Sung Lee': '李在城', 'Hyeon-Woo Jo': '赵贤祐', 'Seung-Gyu Kim': '金承奎',
    'Han-Beom Lee': '李韩汎', 'Yu-Min Cho': '曹侑珉', 'Ki-Hyuk Lee': '李期奕',
    'Tae-Seok Lee': '李太锡', 'Jens Castrop': '延斯·卡斯特罗普',
    # Australian WCQ-format names → Chinese
    'Nestory Irankunda': '伊兰昆达', 'Mathew Leckie': '马修·莱基',
    'Jackson Irvine': '杰克逊·欧文', 'Connor Metcalfe': '康纳·梅特卡夫',
    'Ajdin Hrustic': '阿伊丁·赫鲁斯蒂奇', 'Awer Mabil': '奥尔·马比尔',
    'Ryan Teague': '瑞安·蒂格', 'Harry Souttar': '哈利·苏塔尔',
    "Aiden O'Neill": '奥尼尔', 'Aziz Behich': '阿齐兹·贝希奇',
    'Cameron Burgess': '卡梅隆·伯吉斯', 'Milo\u0161 Degenek': '米洛斯·迪基尼克',
    'Jason Geria': '杰森·杰里亚', 'Jordy Bos': '乔丹·博斯',
    'Cammy Devlin': '卡梅隆·德夫林', 'Mathew Ryan': '瑞安',
    'Ryan Strain': '瑞安·斯特莱恩', 'Alessandro Circati': '亚历山德罗·西卡蒂',
    'Mo Tour\u00e9': '穆罕默德·图雷', 'Kai Trewin': '凯·特里温',
    'Paul Izzo': '保罗·伊佐', 'Kasey Bos': '乔丹·博斯',
    # Brazilian WCQ-format names → Chinese
    'Gabriel Jesus': '加布里埃尔·热苏斯', 'Gabriel Magalh\u00e3es': '加布里埃尔',
    'Roger Ibanez': '伊巴涅斯', 'Gleison Bremer': '布雷默',
    # Other WCQ-format names
    'Yuito Suzuki': '铃木唯人', 'Jesus Rodr\u00edguez': '赫苏斯·罗德里格斯',
    'Danley Jean-Jacques': '丹利', 'Mohamed Abdelmonem': '穆罕默德·阿卜杜勒莫奈姆',
}
_CN_NAME_MAP.update(_CN_NAME_OVERRIDE)
for _k, _v in _CN_NAME_OVERRIDE.items():
    _CN_NAME_NORM[_normalize_name(_k)] = _v

# Use filtered data (only 26-man WC squad players) if available

# ── Seed name → WCQ name alias mapping (for dedup) ──
_SEED_ALIAS = {
    # Korea: seed "Given-Family" → WCQ "Family-Given"
    'Heung-Min Son': 'Son Heung-min', 'Gue-Sung Cho': 'Cho Gue-sung',
    'Kang-In Lee': 'Lee Kang-in', 'Hyeon-Gyu Oh': 'Oh Hyeon-gyu',
    'In-Beom Hwang': 'Hwang In-beom', 'Jae-Sung Lee': 'Lee Jae-sung',
    'Hee-Chan Hwang': 'Hwang Hee-chan', 'Seung-Ho Paik': 'Paik Seung-ho',
    'Dong-Gyeong Lee': 'Lee Dong-gyeong', 'Min-Jae Kim': 'Kim Min-jae',
    'Young-Woo Seol': 'Seol Young-woo', 'Hyeon-Woo Jo': 'Jo Hyeon-woo',
    'Seung-Gyu Kim': 'Kim Seung-gyu', 'Moon-Hwan Kim': 'Moon-Hwan Kim',
    'Tae-Hyun Kim': 'Tae-Hyun Kim', 'Jin-Seob Park': 'Jin-Seob Park',
    'Jin-Gyu Kim': 'Jin-Gyu Kim', 'Jun-Ho Bae': 'Jun-Ho Bae',
    'Hyun-Jun Yang': 'Hyun-Jun Yang', 'Ji-Sung Eom': 'Ji-Sung Eom',
    'Han-Beom Lee': 'Han-Beom Lee', 'Yu-Min Cho': 'Yu-Min Cho',
    'Ki-Hyuk Lee': 'Ki-Hyuk Lee', 'Tae-Seok Lee': 'Tae-Seok Lee',
    'Bum-Keun Song': 'Bum-Keun Song',
    # Australia: seed surname-only → WCQ full name
    'Ryan': 'Mathew Ryan', 'Izzo': 'Paul Izzo', 'Behich': 'Aziz Behich',
    'Bos': 'Jordy Bos', 'Burgess': 'Cameron Burgess', 'Circati': 'Alessandro Circati',
    'Degenek': 'Milo\u0161 Degenek', 'Geria': 'Jason Geria', 'Hrustic': 'Ajdin Hrustic',
    'Irvine': 'Jackson Irvine', 'Leckie': 'Mathew Leckie', 'Mabil': 'Awer Mabil',
    'Metcalfe': 'Connor Metcalfe', 'Souttar': 'Harry Souttar', 'Devlin': 'Cammy Devlin',
    'Trewin': 'Kai Trewin', 'Irankunda': 'Nestory Irankunda',
    "O'Neill": "Aiden O'Neill",
    # Brazil: seed mononym → WCQ full name
    'Gabriel': 'Gabriel Magalh\u00e3es', 'Ibanez': 'Roger Ibanez',
    'Bremer': 'Gleison Bremer',
    # Spain: seed nickname/short → WCQ full
    'Gavi': 'Gavi', 'Eric Garcia': 'Eric Garcia',
    # Egypt
    'Mohamed Abdelmonemn': 'Mohamed Abdelmonem',
    # Haiti: seed "Given Family" → WCQ "Family-Given"
    'Jean-Jacques Danley': 'Danley Jean-Jacques',
}

# ── Players cut from final squads (in filtered data but not in final seed) ──
_EXCLUDED = {
    'Senegal': {'Ilay Camara', 'Moustapha Mbow'},
    'Egypt': {'Mohamed Alaa'},
}

filtered_path = os.path.join(DATA_DIR, "wcq_player_stats_filtered.json")
if os.path.exists(filtered_path):
    json_path = filtered_path
    print("Using filtered data (WC 26-man squads only)")
else:
    json_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
    print("Using full WCQ data")

output_path = os.path.join(DATA_DIR, "player_ranking.json")

TEAM_PROJECTIONS = {
    "Spain": (7.0, 15.1), "Germany": (5.8, 12.2), "Brazil": (6.3, 11.8),
    "France": (6.8, 11.2), "England": (6.4, 10.0), "Argentina": (6.1, 9.5),
    "Portugal": (5.9, 9.1), "Belgium": (5.2, 8.7), "Netherlands": (5.3, 8.0),
    "Switzerland": (4.7, 7.4), "Colombia": (4.9, 6.8), "Mexico": (4.5, 6.6),
    "Norway": (5.0, 6.5), "Uruguay": (4.7, 6.1), "Croatia": (4.4, 6.0),
    "Morocco": (4.7, 5.5), "United-States": (4.5, 5.2), "Austria": (4.2, 5.1),
    "Canada": (4.1, 4.8), "Ecuador": (4.4, 4.7), "Japan": (4.4, 4.7),
    "Cote-dIvoire": (4.0, 4.4), "Senegal": (4.1, 4.4), "Scotland": (4.0, 4.4),
    "Egypt": (3.9, 4.3), "Czechia": (3.9, 4.1), "Turkiye": (4.2, 4.1),
    "Algeria": (3.7, 3.9), "Sweden": (4.0, 3.9), "Bosnia-and-Herzegovina": (3.7, 3.8),
    "Korea-Republic": (3.8, 3.6), "IR-Iran": (3.7, 3.6), "Ghana": (3.6, 3.2),
    "Paraguay": (3.8, 3.2), "Australia": (3.5, 2.8), "Cape-Verde": (3.3, 2.7),
    "Tunisia": (3.4, 2.6), "South-Africa": (3.4, 2.4), "Saudi-Arabia": (3.4, 2.3),
    "New-Zealand": (3.3, 2.3), "Qatar": (3.3, 2.3), "Uzbekistan": (3.3, 2.2),
    "Panama": (3.3, 2.2), "Congo-DR": (3.4, 2.2), "Jordan": (3.2, 2.0),
    "Iraq": (3.1, 1.9), "Haiti": (3.1, 1.8), "Curacao": (3.1, 1.6),
}

def rotation_factor(exp_games):
    if exp_games >= 6.0: return 0.80
    if exp_games >= 5.0: return 0.85
    if exp_games >= 4.0: return 0.90
    return 0.95

SOT_CONVERSION = 0.30
BASE_CONVERSION = 0.08
POS_PRIOR_XG = {'FW': 0.35, 'MF': 0.15, 'DF': 0.05, 'GK': 0.0}
PRIOR_WEIGHT = 8.0
PK_BONUS_CAP = 1.5

def _get_position(pos_str):
    if not pos_str: return 'MF'
    first = pos_str.split(',')[0].strip()
    return first if first in POS_PRIOR_XG else 'MF'

def _compute_team_mult(team, team_proj_override=None):
    all_goals = [v[1] for v in TEAM_PROJECTIONS.values()]
    median_goals = statistics.median(all_goals)
    if team_proj_override and team in team_proj_override:
        proj_goals = team_proj_override[team]
    else:
        _, proj_goals = TEAM_PROJECTIONS.get(team, (3.0, 2.0))
    return proj_goals / median_goals

def compute_ranking(data, team_proj_override=None):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    all_players = []
    # Add WCQ players to ranking; track for dedup; skip excluded/cut players
    seen_players, seen_norm, seen_cn = set(), set(), set()
    for team, players in data.items():
        excluded = _EXCLUDED.get(team, set())
        for p in players:
            pname = p["player"]
            # Skip excluded players entirely (don't add to tracking sets)
            if pname in excluded:
                continue
            nineties = p.get("nineties", 0)
            p_norm = _normalize_name(pname)
            # Only add to ranking if played minutes
            if nineties <= 0:
                continue
            # Track WCQ players with stats in dedup sets
            seen_players.add((pname, team))
            seen_norm.add((p_norm, team))
            p_cn = _get_cn_name(pname)
            if p_cn: seen_cn.add((p_cn, team))
            gls, ast = p.get("gls", 0), p.get("ast", 0)
            sh, sot = p.get("sh", 0), p.get("sot", 0)
            pk, pkatt = p.get("pk", 0), p.get("pkatt", 0)
            pos = p.get("pos", "")
            primary_pos = _get_position(pos)
            proj_games, proj_goals = TEAM_PROJECTIONS.get(team, (3.0, 2.0))
            if team_proj_override and team in team_proj_override:
                proj_goals = team_proj_override[team]
            team_mult = _compute_team_mult(team, team_proj_override)
            if sot > 0 or sh > 0:
                sot_per90 = sot / nineties
                non_sot_sh_per90 = max(0, sh - sot) / nineties
                raw_xg_per90 = sot_per90 * SOT_CONVERSION + non_sot_sh_per90 * BASE_CONVERSION
            else:
                prior = POS_PRIOR_XG.get(primary_pos, 0.10)
                raw_xg_per90 = (gls + prior * PRIOR_WEIGHT) / (nineties + PRIOR_WEIGHT)
            prior = POS_PRIOR_XG.get(primary_pos, 0.10)
            shrunk_xg_per90 = (raw_xg_per90 * nineties + prior * PRIOR_WEIGHT) / (nineties + PRIOR_WEIGHT)
            mp, minutes = p.get("mp", 0), p.get("min", 0)
            wcq_base_ratio = min(1.0, minutes / (mp * 90)) if mp > 0 else 0.5
            team_rot_factor = rotation_factor(proj_games)
            expected_wc_90s = proj_games * wcq_base_ratio * team_rot_factor
            if pkatt > 0 and nineties > 0:
                pk_per_90 = pk / nineties
                pk_success_rate = pk / pkatt if pkatt > 0 else 0.76
                pk_bonus = min(pk_per_90 * expected_wc_90s * pk_success_rate, PK_BONUS_CAP)
            else:
                pk_bonus = 0
            base_g = shrunk_xg_per90 * team_mult * expected_wc_90s
            final_g = base_g + pk_bonus
            all_players.append({
                "player": pname, "name_cn": _get_cn_name(pname),
                "team": team, "pos": pos, "team_share": 0.0,
                "final_projected_g": round(final_g, 3), "og": p.get("og", 0),
                "base_projected_g": round(base_g, 3), "pk_bonus": round(pk_bonus, 3),
                "efficiency_adj": round(team_mult, 3),
                "gls": gls, "ast": ast, "sh": sh, "nineties": round(nineties, 1),
                "pk": pk, "pkatt": pkatt,
                "gls_per90": p.get("gls_per90", 0),
                "sh_per90": round(p.get("sh_per90", 0), 2) if sh > 0 else 0,
                "g_sh": round(p.get("g_sh", 0), 3) if sh > 0 else 0,
                "xg_proxy": round(raw_xg_per90, 3), "shrunk_xg_per90": round(shrunk_xg_per90, 3),
                "team_mult": round(team_mult, 3), "expected_wc_90s": round(expected_wc_90s, 2),
                "sot": sot,
            })
    # Add missing seed_data players (not in WCQ or 0-nineties alias match)
    seen_norm_all = set(seen_norm)
    for team in TEAM_PROJECTIONS:
        cn_team = _SLUG_TO_CN.get(team)
        if not cn_team or cn_team not in PLAYERS_DATA: continue
        proj_games, proj_goals = TEAM_PROJECTIONS.get(team, (3.0, 2.0))
        if team_proj_override and team in team_proj_override:
            proj_goals = team_proj_override[team]
        team_mult = _compute_team_mult(team, team_proj_override)
        team_rot = rotation_factor(proj_games)
        for name, name_cn, jersey, pos in PLAYERS_DATA[cn_team]:
            if (name, team) in seen_players: continue
            if (_normalize_name(name), team) in seen_norm: continue
            cn = _get_cn_name(name)
            if cn and (cn, team) in seen_cn: continue
            alias = _SEED_ALIAS.get(name, '')
            if alias and (_normalize_name(alias), team) in seen_norm_all: continue
            prior = POS_PRIOR_XG.get(pos, 0.10)
            expected_wc_90s = proj_games * 0.50 * team_rot
            base_g = prior * team_mult * expected_wc_90s
            all_players.append({
                "player": name, "name_cn": _get_cn_name(name),
                "team": team, "pos": pos, "team_share": 0.0,
                "final_projected_g": round(base_g, 3), "og": 0,
                "base_projected_g": round(base_g, 3), "pk_bonus": 0,
                "efficiency_adj": round(team_mult, 3),
                "gls": 0, "ast": 0, "sh": 0, "nineties": 0, "pk": 0, "pkatt": 0,
                "gls_per90": 0, "sh_per90": 0, "g_sh": 0,
                "xg_proxy": round(prior, 3), "shrunk_xg_per90": round(prior, 3),
                "team_mult": round(team_mult, 3), "expected_wc_90s": round(expected_wc_90s, 2),
                "sot": 0, "no_wcq_data": True,
            })
    # Trim teams to exactly 26 players
    team_counts = Counter(p["team"] for p in all_players)
    for team, count in team_counts.items():
        if count <= 26:
            continue
        excess = count - 26
        team_players = [p for p in all_players if p["team"] == team]
        # First remove seed-only placeholders (no WCQ stats)
        seed_only = [p for p in team_players if p.get("no_wcq_data")]
        seed_only.sort(key=lambda x: x["final_projected_g"])  # remove lowest first
        to_remove = set()
        for p in seed_only:
            if excess <= 0:
                break
            to_remove.add(id(p))
            excess -= 1
        # If still over, remove WCQ-only extras (lowest-ranked)
        if excess > 0:
            cn_team = _SLUG_TO_CN.get(team)
            seed_names = set()
            if cn_team and cn_team in PLAYERS_DATA:
                seed_names = {n for n, _, _, _ in PLAYERS_DATA[cn_team]}
                seed_names.update(_normalize_name(n) for n, _, _, _ in PLAYERS_DATA[cn_team])
            wcq_only = [p for p in team_players
                        if id(p) not in to_remove
                        and p["player"] not in seed_names
                        and _normalize_name(p["player"]) not in seed_names]
            wcq_only.sort(key=lambda x: x["final_projected_g"])
            for p in wcq_only:
                if excess <= 0:
                    break
                to_remove.add(id(p))
                excess -= 1
        all_players = [p for p in all_players if id(p) not in to_remove]
    # Compute team_share
    team_totals = defaultdict(float)
    for pp in all_players: team_totals[pp["team"]] += pp["base_projected_g"]
    for pp in all_players:
        tt = team_totals.get(pp["team"], 0)
        pp["team_share"] = round(pp["base_projected_g"] / tt * 100, 1) if tt > 0 else 0.0
    all_players.sort(key=lambda x: (-x["final_projected_g"], -x["og"]))
    for i, p in enumerate(all_players, 1): p["rank"] = i
    return all_players

def run_monte_carlo(data, iterations=1000, noise_range=(0.85, 1.15)):
    all_ranks, all_scores = defaultdict(list), defaultdict(list)
    det_ranking = compute_ranking(data)
    det_rank_map = {f"{p['player']}|{p['team']}": p['rank'] for p in det_ranking}
    teams = list(TEAM_PROJECTIONS.keys())
    rng = random.Random(42)
    for _ in range(iterations):
        override = {}
        for team in teams:
            _, base_goals = TEAM_PROJECTIONS[team]
            override[team] = base_goals * rng.uniform(noise_range[0], noise_range[1])
        mc_ranking = compute_ranking(data, team_proj_override=override)
        for p in mc_ranking:
            key = f"{p['player']}|{p['team']}"
            all_ranks[key].append(p['rank'])
            all_scores[key].append(p['final_projected_g'])
    mc_results = []
    for key, ranks in all_ranks.items():
        ranks.sort()
        scores = sorted(all_scores[key])
        n = len(ranks)
        player, team = key.split("|")
        mc_results.append({
            "player": player, "team": team,
            "deterministic_rank": det_rank_map.get(key, 9999),
            "median_rank": ranks[n // 2], "best_rank": ranks[0], "worst_rank": ranks[-1],
            "p10_rank": ranks[int(n * 0.1)], "p90_rank": ranks[int(n * 0.9) - 1],
            "median_score": round(scores[n // 2], 3),
            "p10_score": round(scores[int(n * 0.1)], 3),
            "p90_score": round(scores[int(n * 0.9) - 1], 3),
            "volatility": round(ranks[-1] - ranks[0], 0),
        })
    mc_results.sort(key=lambda x: x["deterministic_rank"])
    return mc_results

def main():
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {sum(len(v) for v in data.values())} players from {len(data)} teams")
    print("Computing deterministic ranking...")
    ranking = compute_ranking(data)
    print(f"  -> {len(ranking)} players ranked")
    print("\nTop 20:")
    for p in ranking[:20]:
        cn = p.get('name_cn', '')
        print(f"  {p['rank']:>4}. {p['player']:<25s} ({cn:<6s}) {p['team']:<20s}"
              f"  Score={p['final_projected_g']:>5.3f}  xG={p['xg_proxy']:>5.3f}"
              f"  Shrk={p['shrunk_xg_per90']:>5.3f}  Mult={p['team_mult']:>4.2f}"
              f"  PK={p['pk_bonus']:>5.3f}  SoT={p['sot']}")
    print("\nRunning Monte Carlo simulation (1000 iterations)...")
    mc_results = run_monte_carlo(data, iterations=1000, noise_range=(0.85, 1.15))
    print(f"  -> {len(mc_results)} players with MC stats")
    output = {"deterministic": ranking, "monte_carlo": mc_results}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nOutput saved: {output_path}")
    print(f"Deterministic: {len(ranking)} players")
    print(f"Monte Carlo:   {len(mc_results)} players")

if __name__ == "__main__":
    main()
