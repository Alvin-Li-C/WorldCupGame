"""Analyze goals vs kickoff weather for finished World Cup matches."""
from __future__ import annotations

import os
import statistics

from briefing.weather_fetch import is_rainy, temp_band, temp_band_label, weather_label
from briefing_data import load_fixtures, load_history_index, load_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS_PATH = os.path.join(ROOT, 'data', 'briefing', 'weather_goals_analysis.json')


def _fixture_by_id(fixtures):
    return {f['fixture_id']: f for f in fixtures}


def _collect_finished_rows(history_index=None, fixtures=None):
    idx = history_index if history_index is not None else load_history_index()
    fix_map = _fixture_by_id(fixtures if fixtures is not None else load_fixtures())
    rows = []
    for report in (idx.get('reports') or {}).values():
        for m in report.get('matches') or []:
            hs, aw = m.get('home_score'), m.get('away_score')
            if hs is None or aw is None:
                continue
            fid = m.get('fixture_id')
            fix = fix_map.get(fid) or {}
            detail = fix.get('weather_detail') or {}
            if not detail or detail.get('error'):
                continue
            rows.append({
                'fixture_id': fid,
                'home_team': m.get('home_team'),
                'away_team': m.get('away_team'),
                'total_goals': int(hs) + int(aw),
                'played_date_beijing': m.get('played_date_beijing'),
                'weather_detail': detail,
                'temp_c': detail.get('temp_c'),
                'temp_band': detail.get('temp_band') or temp_band(detail.get('temp_c')),
                'is_rainy': detail.get('is_rainy', is_rainy(detail.get('weather_code'), detail.get('precip_mm'))),
                'condition_cn': detail.get('condition_cn') or weather_label(detail.get('weather_code')),
            })
    return rows


def _avg_goals(rows):
    if not rows:
        return None
    return round(statistics.mean(r['total_goals'] for r in rows), 2)


def build_weather_goals_analysis(history_index=None, fixtures=None) -> dict:
    rows = _collect_finished_rows(history_index, fixtures)
    overall = _avg_goals(rows)

    by_band = {}
    for band in ('cool', 'mild', 'warm', 'hot'):
        subset = [r for r in rows if r['temp_band'] == band]
        if subset:
            by_band[band] = {
                'label': temp_band_label(band),
                'matches': len(subset),
                'avg_goals': _avg_goals(subset),
                'sample': [
                    f"{r['home_team']} {r['total_goals']}球 ({r['temp_c']}°C {r['condition_cn']})"
                    for r in subset[:3]
                ],
            }

    dry = [r for r in rows if not r['is_rainy']]
    wet = [r for r in rows if r['is_rainy']]
    by_rain = {
        'dry': {'label': '非雨天', 'matches': len(dry), 'avg_goals': _avg_goals(dry)},
        'wet': {'label': '雨天/降水', 'matches': len(wet), 'avg_goals': _avg_goals(wet)},
    }

    by_condition = {}
    for r in rows:
        c = r['condition_cn']
        by_condition.setdefault(c, []).append(r)
    condition_stats = sorted(
        [
            {
                'condition': cond,
                'matches': len(rs),
                'avg_goals': _avg_goals(rs),
            }
            for cond, rs in by_condition.items()
        ],
        key=lambda x: (-x['matches'], x['condition']),
    )

    insights = []
    if overall is not None:
        insights.append(f'已赛 {len(rows)} 场样本，全场总进球均值 {overall} 球/场。')
    if by_band:
        best = max(by_band.values(), key=lambda x: x['avg_goals'] or 0)
        worst = min(by_band.values(), key=lambda x: x['avg_goals'] or 999)
        if best.get('avg_goals') is not None and worst.get('avg_goals') is not None and best != worst:
            insights.append(
                f'气温段中 {best["label"]} 场均 {best["avg_goals"]} 球最高，'
                f'{worst["label"]} 场均 {worst["avg_goals"]} 球最低（样本偏少，仅供参考）。'
            )
    if by_rain['wet']['matches'] and by_rain['dry']['avg_goals'] is not None:
        insights.append(
            f'雨天/降水 {by_rain["wet"]["matches"]} 场场均 {by_rain["wet"]["avg_goals"]} 球，'
            f'非雨天 {by_rain["dry"]["matches"]} 场场均 {by_rain["dry"]["avg_goals"]} 球。'
        )
    elif by_rain['dry']['matches']:
        insights.append('当前样本中尚无显著降水场次。')

    return {
        'sample_size': len(rows),
        'overall_avg_goals': overall,
        'by_temp_band': by_band,
        'by_rain': by_rain,
        'by_condition': condition_stats,
        'matches': rows,
        'insights': insights,
    }


def save_weather_goals_analysis(path=None, **kwargs):
    from briefing_data import save_json
    data = build_weather_goals_analysis(**kwargs)
    out = path or ANALYSIS_PATH
    save_json(out, data)
    return data


def load_weather_goals_analysis():
    return load_json(ANALYSIS_PATH, {})
