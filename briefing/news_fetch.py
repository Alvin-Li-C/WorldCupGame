"""RSS / domestic feeds / keyword prefilter for match news candidates."""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

import urllib.request

BJ = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WC_KEYWORDS = (
    'world cup', '2026', 'fifa world cup',
    '世界杯', '世预赛', '美加墨',
)
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
_DQD_API = 'https://api.dongqiudi.com/app/tabs/iphone/{tab_id}.json?mark=gif&version=8.0.0'
_ZHIBO8_FOOTBALL = 'https://news.zhibo8.com/zuqiu/'

CATEGORY_KEYWORDS = {
    'tactics': [
        'tactical', 'formation', 'system', 'pressing', 'counter-attack', 'game plan',
        'set piece', 'high line', 'low block', 'manager', 'coach',
        '战术', '阵型', '打法', '体系', '压迫', '反击', '布防',
    ],
    'discord': [
        'feud', 'row', 'clash', 'rift', 'dispute', 'locker room', 'falling out',
        '不和', '矛盾', '更衣室', '内讧', '摩擦', '关系',
    ],
    'form': [
        'key player', 'star', 'fitness', 'slump', 'goal drought', 'in form',
        'out of form', 'struggling', '关键球员', '核心', '状态', '进球荒', '低迷',
    ],
    'lineup': ['lineup', 'starting xi', 'starting', 'rotate', '阵容', '首发', '轮换'],
    'injury': ['injury', 'injured', 'doubtful', '伤病', '受伤', '缺阵'],
    'suspension': ['suspend', 'ban', 'red card', '停赛', '禁赛', '红牌'],
}


def _http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')


def _parse_rss(url, max_items=30):
    try:
        tree = ElementTree.fromstring(_http_get(url))
    except Exception:
        return []
    items = []
    for item in tree.findall('.//item')[:max_items]:
        title = (item.findtext('title') or '').strip()
        desc = (item.findtext('description') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = item.findtext('pubDate') or ''
        items.append({
            'title': title,
            'snippet': re.sub(r'<[^>]+>', '', desc)[:300],
            'source': url,
            'url': link or None,
            'published_at': pub,
        })
    return items


def _fetch_dongqiudi(tab_id, label, max_items=30):
    try:
        data = json.loads(_http_get(_DQD_API.format(tab_id=tab_id)))
    except Exception:
        return []
    items = []
    for article in (data.get('articles') or [])[:max_items]:
        title = (article.get('title') or '').strip()
        if not title:
            continue
        desc = (article.get('description') or article.get('b_description') or '').strip()
        url = article.get('share') or article.get('url') or article.get('url1')
        pub = article.get('published_at') or article.get('show_time') or article.get('created_at') or ''
        items.append({
            'title': title,
            'snippet': desc[:300],
            'source': label or f'懂球帝({tab_id})',
            'url': url,
            'published_at': str(pub) if pub else '',
        })
    return items


def _fetch_zhibo8_football(label='直播8足球', max_items=40):
    try:
        html = _http_get(_ZHIBO8_FOOTBALL)
    except Exception:
        return []
    pattern = re.compile(
        r'href="(?://news\.zhibo8\.com)?(/zuqiu/\d{4}-\d{2}-\d{2}/[^"]+)"[^>]*>([^<]+)</a>',
        re.I,
    )
    items = []
    seen = set()
    for path, title in pattern.findall(html):
        title = title.strip()
        if not title or len(title) < 6:
            continue
        url = f'https://news.zhibo8.com{path}'
        if url in seen:
            continue
        seen.add(url)
        items.append({
            'title': title,
            'snippet': title[:300],
            'source': label,
            'url': url,
            'published_at': '',
        })
        if len(items) >= max_items:
            break
    return items


def collect_news_items(config, max_per_source=30):
    """Aggregate configured RSS and domestic (懂球帝 / 直播8) feeds."""
    news_cfg = config.get('news', {})
    raw = []
    seen = set()

    def add_items(items):
        for item in items:
            key = item.get('url') or item.get('title')
            if not key or key in seen:
                continue
            seen.add(key)
            raw.append(item)

    for src in news_cfg.get('cn_feeds', []):
        src_type = src.get('type', '')
        label = src.get('label', '')
        if src_type == 'dongqiudi':
            add_items(_fetch_dongqiudi(src.get('tab_id', 1), label, max_per_source))
        elif src_type == 'zhibo8':
            add_items(_fetch_zhibo8_football(label or '直播8足球', max_per_source))

    for url in news_cfg.get('rss_feeds', []):
        add_items(_parse_rss(url, max_per_source))

    return raw


def _english_aliases(team_cn, team_map):
    aliases = []
    if not team_cn:
        return aliases
    for en, cn in (team_map or {}).items():
        if cn == team_cn:
            aliases.append(en)
    return aliases


def _load_team_map(config):
    path = config.get('team_name_map_file')
    if path:
        full = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if os.path.isfile(full):
            with open(full, encoding='utf-8') as f:
                return json.load(f)
    return config.get('team_name_map') or {}


def build_team_hints(home_team, away_team, config, team_hints_en=None):
    team_map = _load_team_map(config)
    hints = []
    for cn, en in ((home_team, None), (away_team, None)):
        if cn:
            hints.append(cn)
        for alias in _english_aliases(cn, team_map):
            hints.append(alias)
    if team_hints_en:
        for name in team_hints_en:
            if name:
                hints.append(name)
    seen = set()
    out = []
    for h in hints:
        key = h.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def score_candidate(text, team_hints, impact_keywords, our_picks=None, our_pick_bonus=15):
    lower = text.lower()
    score = 0
    category = 'other'
    best_cat_score = 0
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w.lower() in lower or w in text:
                s = impact_keywords.get(w, impact_keywords.get(cat, 10)) if isinstance(impact_keywords, dict) else 10
                if s > best_cat_score:
                    best_cat_score = s
                    category = cat
                score += 5
    team_hit = False
    for team in team_hints:
        if not team:
            continue
        if team in text or team.lower() in lower:
            score += 20
            team_hit = True
    if our_picks:
        for pick in our_picks:
            if pick and pick in text:
                score += our_pick_bonus
    if any(kw in lower for kw in WC_KEYWORDS):
        if team_hit:
            score += 15
        elif score > 0:
            score += 8
        else:
            score += 6
    return score, category


def _team_hint_for_blob(blob, home_team, away_team, team_map):
    lower = blob.lower()
    for cn in (home_team, away_team):
        if cn and cn in blob:
            return cn
    for cn in (home_team, away_team):
        for alias in _english_aliases(cn, team_map):
            if alias.lower() in lower:
                return cn
    return home_team


def prefilter_for_match(
    home_team,
    away_team,
    config,
    our_picks=None,
    max_candidates=20,
    team_hints_en=None,
):
    impact = config.get('news', {}).get('impact_keywords', {})
    bonus = config.get('news', {}).get('our_pick_bonus', 15)
    max_per_source = config.get('llm', {}).get('max_candidates_per_match', 20)
    team_map = _load_team_map(config)
    hints = build_team_hints(home_team, away_team, config, team_hints_en)
    raw = collect_news_items(config, max_per_source=max_per_source * 2)
    if not raw:
        return []

    scored = []
    for c in raw:
        blob = f"{c['title']} {c['snippet']}"
        s, cat = score_candidate(blob, hints, impact, our_picks, bonus)
        if s <= 0:
            continue
        team_hint = _team_hint_for_blob(blob, home_team, away_team, team_map)
        scored.append({**c, 'impact_score': s, 'category': cat, 'team_hint': team_hint})
    scored.sort(key=lambda x: -x['impact_score'])
    return scored[:max_candidates]
