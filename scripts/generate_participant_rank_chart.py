"""Generate standalone daily top-5 participant goal-ranking chart HTML."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.participant_rank_chart import compute_daily_series  # noqa: E402
from briefing_data import save_json  # noqa: E402

OUTPUT_HTML = os.path.join(ROOT, 'data', 'briefing', 'participant_rank_chart.html')
OUTPUT_JSON = os.path.join(ROOT, 'data', 'briefing', 'participant_rank_daily.json')

PARTICIPANT_COLORS = {
    '耗子': '#f5c518',
    '庆爷': '#4ade80',
    '李总': '#38bdf8',
    '老闫': '#f87171',
    '老王': '#c084fc',
}


def _render_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    start = data['start_date'][5:].replace('-', '/')
    end_label = data['dates'][-1][5:].replace('-', '/') if data['dates'] else start
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>五人进球排名变化 · {start}—{end_label}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0f1419; color: #e8eaed; min-height: 100vh; padding: 24px 16px 40px;
  }}
  h1 {{ font-size: 1.35rem; font-weight: 600; text-align: center; margin-bottom: 4px; }}
  .subtitle {{ text-align: center; color: #9aa0a6; font-size: 0.85rem; margin-bottom: 20px; }}
  .chart-box {{
    max-width: 960px; margin: 0 auto;
    background: #1a2332; border-radius: 12px; padding: 12px 8px 4px;
  }}
  #rankChart {{ width: 100%; height: 380px; }}
</style>
</head>
<body>
<h1>世界杯幻想选秀 · 五人排名走势</h1>
<p class="subtitle">{start} 开赛 — {end_label} · 按积分排名</p>
<div class="chart-box"><div id="rankChart"></div></div>
<script>
const DATA = {payload};
const chart = echarts.init(document.getElementById('rankChart'));
chart.setOption({{
  backgroundColor: 'transparent',
  tooltip: {{ trigger: 'axis' }},
  legend: {{ data: DATA.participants, bottom: 4, textStyle: {{ color: '#bdc1c6' }} }},
  grid: {{ left: 48, right: 24, top: 24, bottom: 56 }},
  xAxis: {{ type: 'category', data: DATA.date_labels }},
  yAxis: {{ type: 'value', min: 1, max: 5, interval: 1, inverse: true }},
  series: DATA.participants.map(name => ({{
    name, type: 'line', smooth: 0.35, symbol: 'circle', symbolSize: 8,
    lineStyle: {{ width: 3, color: DATA.series[name].color }},
    itemStyle: {{ color: DATA.series[name].color }},
    data: DATA.series[name].ranks,
  }})),
}});
window.addEventListener('resize', () => chart.resize());
</script>
</body>
</html>"""


def generate() -> str:
    data = compute_daily_series(colors=PARTICIPANT_COLORS)
    save_json(OUTPUT_JSON, data)
    html = _render_html(data)
    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    return OUTPUT_HTML


if __name__ == '__main__':
    out = generate()
    print(f'Wrote {out}', flush=True)
    print(f'Wrote {OUTPUT_JSON}', flush=True)
