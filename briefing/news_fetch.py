"""RSS / domestic feeds / keyword prefilter for match news candidates."""
import json
import os
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

import urllib.request

BJ = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WC_KEYWORDS = (
    'world cup', 'fifa world cup',
    '世界杯', '美加墨',
)
DOMESTIC_LEAGUE_MARKERS = (
    '中超', '中甲', '中乙', '足协杯', '中国之星', 'CFA',
    '英超', '西甲', '德甲', '意甲', '法甲', '欧冠',
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


def _parse_rss(url, max_items=30, label=None, timeout=30):
    try:
        tree = ElementTree.fromstring(_http_get(url, timeout=timeout))
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
            'source': label or url,
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


def _fetch_google_news_rss(query, label, max_items=8):
    try:
        url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({
            'q': query,
            'hl': 'zh-CN',
            'gl': 'CN',
            'ceid': 'CN:zh-Hans',
        })
        items = _parse_rss(url, max_items)
        for item in items:
            item['source'] = label
        return items
    except Exception:
        return []


def _team_search_news(home_team, away_team, config, max_per_team=8, team_hints_en=None):
    if not config.get('news', {}).get('team_search_rss', True):
        return []
    team_map = _load_team_map(config)
    out = []
    queries = []
    for team_cn in (home_team, away_team):
        if not team_cn:
            continue
        queries.append((f'{team_cn} 世界杯', f'搜索:{team_cn}'))
        for alias in _english_aliases(team_cn, team_map):
            queries.append((f'{alias} World Cup 2026', f'搜索:{alias}'))
    if team_hints_en:
        for name in team_hints_en:
            if name and not any(name in q[0] for q in queries):
                queries.append((f'{name} World Cup 2026', f'搜索:{name}'))
    for query, label in queries:
        out.extend(_fetch_google_news_rss(query, label, max_per_team))
    return out


def _iter_rss_feeds(news_cfg):
    for key in ('intl_feeds', 'rss_feeds'):
        for entry in news_cfg.get(key, []):
            if isinstance(entry, str):
                yield entry, None, 30
            elif isinstance(entry, dict) and entry.get('url'):
                timeout = entry.get('timeout', 8 if entry.get('optional') else 30)
                yield entry['url'], entry.get('label'), timeout


def collect_news_items(config, max_per_source=30):
    """Aggregate domestic (懂球帝 / 直播8) and international RSS feeds."""
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

    for url, label, timeout in _iter_rss_feeds(news_cfg):
        add_items(_parse_rss(url, max_per_source, label, timeout=timeout))

    for src in news_cfg.get('cn_feeds', []):
        src_type = src.get('type', '')
        label = src.get('label', '')
        if src_type == 'dongqiudi':
            add_items(_fetch_dongqiudi(src.get('tab_id', 1), label, max_per_source))
        elif src_type == 'zhibo8':
            add_items(_fetch_zhibo8_football(label or '直播8足球', max_per_source))

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


def _text_has_team(text, team_hints):
    lower = text.lower()
    for team in team_hints:
        if not team:
            continue
        if team in text or team.lower() in lower:
            return True
    return False


def _has_wc_context(text):
    lower = text.lower()
    if any(kw in text for kw in ('世界杯', '美加墨')):
        return True
    return 'world cup' in lower or 'fifa world cup' in lower


def _is_domestic_noise(text, team_hit):
    if team_hit:
        return False
    return any(m in text for m in DOMESTIC_LEAGUE_MARKERS)


def _english_nation_in_text(text, name):
    if len(name) < 3:
        return False
    pattern = re.compile(r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])', re.I)
    return bool(pattern.search(text))


def _mentions_other_fixture_nation(text, home_team, away_team, team_map):
    nations = sorted({cn for cn in (team_map or {}).values() if cn}, key=len, reverse=True)
    for cn in nations:
        if cn in (home_team, away_team):
            continue
        if len(cn) < 2:
            continue
        if cn in text:
            return True
    fixture_en = set()
    for cn in (home_team, away_team):
        fixture_en.update(_english_aliases(cn, team_map))
    lower = text.lower()
    for en, cn in (team_map or {}).items():
        if cn in (home_team, away_team) or en in fixture_en:
            continue
        if _english_nation_in_text(lower, en):
            return True
    return False


def relevance_tier(text, team_hints, home_team=None, away_team=None, team_map=None):
    """0=drop, 1=generic WC, 2=mentions a fixture nation."""
    team_hit = _text_has_team(text, team_hints)
    if _is_domestic_noise(text, team_hit):
        return 0
    if team_hit:
        return 2
    if _has_wc_context(text):
        if (
            team_map and home_team and away_team
            and _mentions_other_fixture_nation(text, home_team, away_team, team_map)
        ):
            return 0
        return 1
    return 0


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


def score_candidate(
    text,
    team_hints,
    impact_keywords,
    our_picks=None,
    our_pick_bonus=15,
    home_team=None,
    away_team=None,
    team_map=None,
):
    tier = relevance_tier(text, team_hints, home_team, away_team, team_map)
    if tier == 0:
        return 0, 'other'

    lower = text.lower()
    score = tier * 25
    category = 'other'
    best_cat_score = 0
    team_hit = tier >= 2
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w.lower() in lower or w in text:
                s = impact_keywords.get(w, impact_keywords.get(cat, 10)) if isinstance(impact_keywords, dict) else 10
                if s > best_cat_score:
                    best_cat_score = s
                    category = cat
                if team_hit:
                    score += 5
    if our_picks:
        for pick in our_picks:
            if pick and pick in text:
                score += our_pick_bonus
    if _has_wc_context(text):
        if team_hit:
            score += 15
        else:
            score += 8
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
    return None


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
    seen = {item.get('url') or item.get('title') for item in raw}
    for item in _team_search_news(home_team, away_team, config, team_hints_en=team_hints_en):
        key = item.get('url') or item.get('title')
        if key and key not in seen:
            seen.add(key)
            raw.append(item)
    if not raw:
        return []

    scored = []
    for c in raw:
        blob = f"{c['title']} {c['snippet']}"
        tier = relevance_tier(blob, hints, home_team, away_team, team_map)
        if tier == 0:
            continue
        s, cat = score_candidate(
            blob, hints, impact, our_picks, bonus, home_team, away_team, team_map,
        )
        if s <= 0:
            continue
        team_hint = _team_hint_for_blob(blob, home_team, away_team, team_map)
        scored.append({
            **c,
            'impact_score': s,
            'category': cat,
            'team_hint': team_hint,
            'relevance_tier': tier,
        })
    scored.sort(key=lambda x: (-x['relevance_tier'], -x['impact_score']))
    return scored[:max_candidates]
