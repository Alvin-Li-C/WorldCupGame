#!/usr/bin/env python3
"""Build static HTML site for COS / Gitee Pages from local draft.db + briefing JSON."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from flask import Flask, render_template

from briefing_data import (
    get_match_detail,
    get_selections_for_display,
    history_dates_payload,
    load_briefing_enriched,
    load_history_index,
    load_json,
    report_has_results,
    save_json,
)
from briefing.shooter_standings import STANDINGS_PATH as SHOOTER_STANDINGS_PATH
from briefing.standings import STANDINGS_PATH as TEAM_STANDINGS_PATH

DIST = os.path.join(ROOT, 'dist')
STATIC_SRC = os.path.join(ROOT, 'static')

PARTICIPANT_COLORS = {
    '耗子': '#f5c518',
    '庆爷': '#4ade80',
    '李总': '#38bdf8',
    '老闫': '#f87171',
    '老王': '#c084fc',
}

app = Flask(__name__, template_folder=os.path.join(ROOT, 'templates'))


@app.template_filter('beijing_date')
def _filter_beijing_date(iso_date):
    from briefing_data import beijing_date_label
    return beijing_date_label(iso_date)


@app.template_filter('kickoff_beijing')
def _filter_kickoff_beijing(kickoff):
    from briefing_data import kickoff_beijing_label
    return kickoff_beijing_label(kickoff)


def _site_prefix(page_rel: str) -> str:
    """Relative path from HTML file to dist root (e.g. '../' for match/3.html)."""
    parts = page_rel.replace('\\', '/').split('/')
    depth = max(0, len(parts) - 1)
    return '../' * depth


def _rewrite_static_html(html: str, page_rel: str) -> str:
    base = _site_prefix(page_rel)
    static = base + 'static/'
    reports = base + 'data/briefing/reports/'
    briefing = base + 'briefing.html'
    teams = base + 'standings/teams.html'
    shooters = base + 'standings/shooters.html'
    match_prefix = base + 'match/'

    html = html.replace("url('/static/", f"url('{static}")
    html = html.replace('url("/static/', f'url("{static}')
    html = html.replace("url: '/static/", f"url: '{static}")
    html = html.replace("href='/static/", f"href='{static}")
    html = html.replace('href="/static/', f'href="{static}')
    html = html.replace("src='/static/", f"src='{static}")
    html = html.replace('src="/static/', f'src="{static}')
    html = html.replace("= '/static/", f"= '{static}")
    html = html.replace('= "/static/', f'= "{static}')

    html = html.replace(
        "fetch('/api/briefing/history/' + date)",
        f"fetch('{reports}' + date + '.json')",
    )
    html = html.replace(
        "fetch('/data/briefing/reports/' + date + '.json')",
        f"fetch('{reports}' + date + '.json')",
    )

    html = html.replace('href="/briefing"', f'href="{briefing}"')
    html = html.replace('href="/briefing.html"', f'href="{briefing}"')
    html = html.replace('href="/standings/teams"', f'href="{teams}"')
    html = html.replace('href="/standings/teams.html"', f'href="{teams}"')
    html = html.replace('href="/standings/shooters"', f'href="{shooters}"')
    html = html.replace('href="/standings/shooters.html"', f'href="{shooters}"')
    html = html.replace('href="/"', f'href="{briefing}"')

    html = re.sub(r'href="/match/(\d+)"', rf'href="{match_prefix}\1.html"', html)
    html = html.replace(
        "'<a class=\"btn-link\" href=\"/match/' + m.fixture_id + '\">查看详情</a></div>' +",
        f"'<a class=\"btn-link\" href=\"{match_prefix}' + m.fixture_id + '.html\">查看详情</a></div>' +",
    )

    html = re.sub(
        r'/\* BEGIN repair-handler \*/[\s\S]*?/\* END repair-handler \*/\s*',
        '',
        html,
    )
    if '.repair-btn' in html:
        html = html.replace(
            '</style>',
            '        .repair-btn, .repair-select { display: none !important; }\n    </style>',
            1,
        )
    return html


def _write_page(rel_path: str, html: str) -> None:
    html = _rewrite_static_html(html, rel_path)
    out = os.path.join(DIST, rel_path.replace('/', os.sep))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)


def _copy_tree(src: str, dest: str) -> None:
    if os.path.isdir(src):
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    elif os.path.isfile(src):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)


def export_history_reports() -> int:
    idx = load_history_index()
    reports_dir = os.path.join(DIST, 'data', 'briefing', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    count = 0
    for date, report in (idx.get('reports') or {}).items():
        if not report_has_results(report):
            continue
        save_json(os.path.join(reports_dir, f'{date}.json'), report)
        count += 1
    return count


def build_site() -> dict:
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST, exist_ok=True)

    latest = load_briefing_enriched()
    hist = history_dates_payload()
    report_date = hist.get('default') or ''

    with app.app_context():
        briefing_html = render_template(
            'briefing.html',
            latest=latest,
            hist=hist,
            report_date=report_date,
        )
        _write_page('briefing.html', briefing_html)
        _write_page('index.html', briefing_html)

        team_standings = load_json(TEAM_STANDINGS_PATH) or {}
        shooter_standings = load_json(SHOOTER_STANDINGS_PATH) or {}
        _write_page(
            'standings/teams.html',
            render_template(
                'standings_teams.html',
                standings=team_standings,
                colors=PARTICIPANT_COLORS,
            ),
        )
        _write_page(
            'standings/shooters.html',
            render_template(
                'standings_shooters.html',
                standings=shooter_standings,
                colors=PARTICIPANT_COLORS,
                selections=get_selections_for_display(),
            ),
        )

        match_count = 0
        from briefing_data import load_fixtures
        for fix in load_fixtures():
            fid = fix.get('fixture_id')
            if not fid:
                continue
            detail = get_match_detail(fid)
            if not detail:
                continue
            _write_page(
                f'match/{fid}.html',
                render_template('match_intro.html', m=detail),
            )
            match_count += 1

    _copy_tree(os.path.join(STATIC_SRC, 'stadiums'), os.path.join(DIST, 'static', 'stadiums'))
    _copy_tree(os.path.join(STATIC_SRC, 'flags'), os.path.join(DIST, 'static', 'flags'))
    _copy_tree(os.path.join(STATIC_SRC, 'wc2026-logo.svg'), os.path.join(DIST, 'static', 'wc2026-logo.svg'))

    report_files = export_history_reports()
    save_json(os.path.join(DIST, 'data', 'briefing', 'latest.json'), latest)
    save_json(os.path.join(DIST, 'data', 'briefing', 'standings_teams.json'), load_json(TEAM_STANDINGS_PATH))
    save_json(os.path.join(DIST, 'data', 'briefing', 'standings_shooters.json'), load_json(SHOOTER_STANDINGS_PATH))

    meta = {
        'briefing_date': latest.get('briefing_date'),
        'preview_date': (latest.get('today') or {}).get('date'),
        'report_dates': len(hist.get('dates') or []),
        'match_pages': match_count,
        'report_files': report_files,
        'dist': DIST,
    }
    return meta


def main():
    parser = argparse.ArgumentParser(description='Build static site into dist/')
    args = parser.parse_args()
    meta = build_site()
    print('Static site built:', json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
