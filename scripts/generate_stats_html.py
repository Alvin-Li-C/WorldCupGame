"""Generate HTML table from WCQ player stats JSON"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
json_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
html_path = os.path.join(DATA_DIR, "player_stats_table.html")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Build rows
rows = []
for team, players in data.items():
    for p in players:
        rows.append({
            "team": team,
            "player": p["player"],
            "pos": p["pos"],
            "age": p["age"],
            "mp": p["mp"],
            "starts": p["starts"],
            "min": p["min"],
            "nineties": p["nineties"],
            "gls": p["gls"],
            "ast": p["ast"],
            "ga": p["ga"],
            "g_pk": p["g_pk"],
            "pk": p["pk"],
            "pkatt": p["pkatt"],
            "gls_per90": p["gls_per90"],
            "ast_per90": p["ast_per90"],
            "ga_per90": p["ga_per90"],
        })

# Sort by goals descending
rows.sort(key=lambda x: (-x["gls"], -x["ast"], -x["min"]))

# Team colors
TEAM_COLORS = {
    "西班牙": "#c60b1e", "法国": "#002395", "英格兰": "#cf081f",
    "德国": "#000000", "葡萄牙": "#006600", "荷兰": "#ff6600",
    "比利时": "#ed2939", "阿根廷": "#75aadb", "巴西": "#fedf00",
    "哥伦比亚": "#fcd116",
}

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>WCQ 球员数据</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1923; color: #e0e0e0; padding: 20px; }
h1 { text-align: center; margin-bottom: 8px; font-size: 24px; color: #fff; }
.subtitle { text-align: center; color: #888; margin-bottom: 20px; font-size: 14px; }
.controls { display: flex; gap: 12px; justify-content: center; margin-bottom: 16px; flex-wrap: wrap; }
.controls select, .controls input { padding: 8px 14px; border-radius: 6px; border: 1px solid #333; background: #1a2632; color: #fff; font-size: 14px; }
.controls input { width: 200px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th { position: sticky; top: 0; background: #1a2632; padding: 10px 8px; text-align: left; cursor: pointer; border-bottom: 2px solid #2a3a4a; white-space: nowrap; user-select: none; }
thead th:hover { background: #243444; }
thead th.sorted-asc::after { content: ' ▲'; color: #4fc3f7; }
thead th.sorted-desc::after { content: ' ▼'; color: #4fc3f7; }
tbody tr { border-bottom: 1px solid #1a2632; transition: background 0.15s; }
tbody tr:hover { background: #1a2632; }
td { padding: 8px; white-space: nowrap; }
.team-badge { display: inline-block; width: 4px; height: 20px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }
.player-name { font-weight: 600; color: #fff; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.highlight { color: #ffd54f; font-weight: 700; }
.pos-gk { color: #ff9800; } .pos-df { color: #4caf50; } .pos-mf { color: #2196f3; } .pos-fw { color: #f44336; }
.stat-zero { color: #444; }
#count { text-align: center; color: #666; margin-top: 12px; font-size: 13px; }
</style>
</head>
<body>
<h1>2026 WCQ 世界杯预选赛球员数据</h1>
<p class="subtitle">FBref WCQ Standard Stats — 10支球队 346名球员</p>
<div class="controls">
  <select id="teamFilter"><option value="">全部球队</option></select>
  <select id="posFilter"><option value="">全部位置</option><option value="GK">GK</option><option value="DF">DF</option><option value="MF">MF</option><option value="FW">FW</option></select>
  <input type="text" id="search" placeholder="搜索球员名...">
</div>
<table>
<thead><tr>
  <th data-col="team">球队</th>
  <th data-col="player">球员</th>
  <th data-col="pos">位置</th>
  <th data-col="age" class="num">年龄</th>
  <th data-col="mp" class="num">出场</th>
  <th data-col="starts" class="num">首发</th>
  <th data-col="min" class="num">分钟</th>
  <th data-col="nineties" class="num">90s</th>
  <th data-col="gls" class="num">进球</th>
  <th data-col="ast" class="num">助攻</th>
  <th data-col="ga" class="num">G+A</th>
  <th data-col="g_pk" class="num">非点进球</th>
  <th data-col="pk" class="num">点球</th>
  <th data-col="pkatt" class="num">点球尝试</th>
  <th data-col="gls_per90" class="num">进球/90</th>
  <th data-col="ast_per90" class="num">助攻/90</th>
  <th data-col="ga_per90" class="num">G+A/90</th>
</tr></thead>
<tbody id="tbody"></tbody>
</table>
<p id="count"></p>
<script>
const DATA = """ + json.dumps(rows, ensure_ascii=False) + """;
const TEAM_COLORS = """ + json.dumps(TEAM_COLORS, ensure_ascii=False) + """;
const tbody = document.getElementById('tbody');
const countEl = document.getElementById('count');
const teamFilter = document.getElementById('teamFilter');
const posFilter = document.getElementById('posFilter');
const searchEl = document.getElementById('search');

// Populate team filter
const teams = [...new Set(DATA.map(r => r.team))];
teams.forEach(t => { const o = document.createElement('option'); o.value = t; o.textContent = t; teamFilter.appendChild(o); });

let sortCol = 'gls', sortDir = -1;

function posClass(pos) {
  if (pos.includes('GK')) return 'pos-gk';
  if (pos.includes('FW')) return 'pos-fw';
  if (pos.includes('MF')) return 'pos-mf';
  if (pos.includes('DF')) return 'pos-df';
  return '';
}

function numCell(v) {
  return v === 0 ? '<span class="stat-zero">0</span>' : (v >= 5 ? `<span class="highlight">${v}</span>` : v);
}

function render() {
  const tf = teamFilter.value, pf = posFilter.value, q = searchEl.value.toLowerCase();
  let filtered = DATA.filter(r => {
    if (tf && r.team !== tf) return false;
    if (pf && !r.pos.includes(pf)) return false;
    if (q && !r.player.toLowerCase().includes(q)) return false;
    return true;
  });
  filtered.sort((a, b) => {
    let va = a[sortCol], vb = b[sortCol];
    if (typeof va === 'string') return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  });
  tbody.innerHTML = filtered.map(r => `<tr>
    <td><span class="team-badge" style="background:${TEAM_COLORS[r.team]||'#666'}"></span>${r.team}</td>
    <td class="player-name">${r.player}</td>
    <td class="${posClass(r.pos)}">${r.pos}</td>
    <td class="num">${r.age}</td>
    <td class="num">${r.mp}</td>
    <td class="num">${r.starts}</td>
    <td class="num">${r.min}</td>
    <td class="num">${r.nineties}</td>
    <td class="num">${numCell(r.gls)}</td>
    <td class="num">${numCell(r.ast)}</td>
    <td class="num">${numCell(r.ga)}</td>
    <td class="num">${r.g_pk}</td>
    <td class="num">${r.pk}</td>
    <td class="num">${r.pkatt}</td>
    <td class="num">${r.gls_per90.toFixed(2)}</td>
    <td class="num">${r.ast_per90.toFixed(2)}</td>
    <td class="num">${r.ga_per90.toFixed(2)}</td>
  </tr>`).join('');
  countEl.textContent = `显示 ${filtered.length} / ${DATA.length} 名球员`;
  document.querySelectorAll('thead th').forEach(th => {
    th.classList.remove('sorted-asc', 'sorted-desc');
    if (th.dataset.col === sortCol) th.classList.add(sortDir > 0 ? 'sorted-asc' : 'sorted-desc');
  });
}

document.querySelectorAll('thead th').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (sortCol === col) sortDir *= -1; else { sortCol = col; sortDir = -1; }
    render();
  });
});
teamFilter.addEventListener('change', render);
posFilter.addEventListener('change', render);
searchEl.addEventListener('input', render);
render();
</script>
</body></html>"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML generated: {html_path}")
print(f"Total rows: {len(rows)}")
