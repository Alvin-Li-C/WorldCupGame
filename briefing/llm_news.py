"""Cursor SDK Top-3 news selection with keyword fallback."""
import json
import re

from briefing_data import CATEGORY_LABELS
from briefing.secrets import read_secret

CATEGORY_LABEL_MAP = CATEGORY_LABELS

ALLOWED_CATEGORIES = (
    'tactics', 'discord', 'form', 'lineup', 'injury', 'suspension', 'other',
)


def build_selection_instruction(home_team, away_team, max_n):
    return (
        f'你是世界杯赛前情报编辑。从 candidates 中为「{home_team} vs {away_team}」'
        f'选出最可能影响本场比分的 {max_n} 条。\n'
        '优先级（高→低）：\n'
        '1. tactics — 双方战术/阵型/打法调整、教练赛前部署、针对对手的布防或进攻选择\n'
        '2. discord — 队内关系、更衣室矛盾、主帅与球员或管理层摩擦、首发竞争引发的分歧\n'
        '3. form — 关键球员竞技状态、复出、进球荒或近期表现起伏（优先主力与球星）\n'
        '4. lineup — 预计首发、轮换、变阵信号\n'
        '5. injury / suspension — 直接削弱本场战力时保留\n'
        '6. other — 仅当以上主题均无可用候选\n'
        '尽量不选：全赛事泛览、48强速览、球衣排名、转会八卦、与两队无关的第三方新闻。\n'
        '若 our_picks 非空，涉及我方选秀球员的条目可适当优先，但仍须符合上列主题。\n'
        '输出：仅 JSON 数组。字段 rank,team,category,category_label,headline,impact,'
        'impact_score,source,published_at,url。\n'
        f'category 仅用 {"/".join(ALLOWED_CATEGORIES)}。\n'
        'category_label 用对应中文（战术/不和/状态/阵容/伤病/停赛/其他）。\n'
        'headline 中文、简明。impact 为 high|medium|low。team 为相关球队中文名。'
    )


def keyword_top3(candidates, home_team, away_team, max_n=3):
    out = []
    for i, c in enumerate(candidates[:max_n], 1):
        cat = c.get('category', 'other')
        impact = 'high' if c.get('impact_score', 0) >= 35 else 'medium'
        out.append({
            'rank': i,
            'team': c.get('team_hint') or home_team,
            'category': cat,
            'category_label': CATEGORY_LABEL_MAP.get(cat, '其他'),
            'headline': c.get('title', '')[:120],
            'impact': impact,
            'impact_score': c.get('impact_score', 0),
            'source': c.get('source', ''),
            'published_at': c.get('published_at'),
            'url': c.get('url'),
        })
    return out


def _parse_llm_json(text):
    text = text.strip()
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        return json.loads(m.group())
    return json.loads(text)


def select_key_news(home_team, away_team, candidates, config, our_picks=None, retry_once=True):
    max_n = config.get('news', {}).get('max_per_match', 3)
    if not candidates:
        return []

    llm_cfg = config.get('llm', {})
    api_key = read_secret(llm_cfg.get('api_key_file', ''), llm_cfg.get('api_key_env'))
    if not api_key:
        return keyword_top3(candidates, home_team, away_team, max_n)

    prompt = json.dumps({
        'home_team': home_team,
        'away_team': away_team,
        'our_picks': our_picks or [],
        'candidates': candidates,
        'instruction': build_selection_instruction(home_team, away_team, max_n),
    }, ensure_ascii=False)

    for attempt in range(2 if retry_once else 1):
        try:
            import os

            from briefing.sdk_compat import ensure_cursor_sdk_os_compat
            ensure_cursor_sdk_os_compat()
            from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
            result = Agent.prompt(
                prompt,
                AgentOptions(
                    api_key=api_key,
                    model=llm_cfg.get('model', 'composer-2.5'),
                    local=LocalAgentOptions(cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                ),
            )
            if result.status == 'error':
                continue
            items = _parse_llm_json(result.result or '[]')
            for item in items:
                cat = item.get('category', 'other')
                item['category_label'] = item.get('category_label') or CATEGORY_LABEL_MAP.get(cat, '其他')
            return items[:max_n]
        except Exception:
            if attempt == 0 and retry_once:
                continue
            break
    return keyword_top3(candidates, home_team, away_team, max_n)
