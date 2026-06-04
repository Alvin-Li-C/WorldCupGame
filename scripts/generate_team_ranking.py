"""Generate HTML page: Top 500 players grouped by national team.
Teams sorted by player count (descending), players within each team sorted by score (descending).
"""
import json
import os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ranking_path = os.path.join(DATA_DIR, "player_ranking.json")
html_path = os.path.join(DATA_DIR, "team_ranking_top500.html")

# Team slug -> Chinese name
SLUG_TO_CN = {
    'Mexico': '墨西哥', 'Czechia': '捷克', 'South-Africa': '南非', 'Korea-Republic': '韩国',
    'Canada': '加拿大', 'Bosnia-and-Herzegovina': '波黑', 'Qatar': '卡塔尔', 'Switzerland': '瑞士',
    'Brazil': '巴西', 'Haiti': '海地', 'Morocco': '摩洛哥', 'Scotland': '苏格兰',
    'United-States': '美国', 'Australia': '澳大利亚', 'Paraguay': '巴拉圭', 'Turkiye': '土耳其',
    'Curacao': '库拉索', 'Ecuador': '厄瓜多尔', 'Germany': '德国', 'Cote-dIvoire': '科特迪瓦',
    'Netherlands': '荷兰', 'Japan': '日本', 'Sweden': '瑞典', 'Tunisia': '突尼斯',
    'Belgium': '比利时', 'Egypt': '埃及', 'IR-Iran': '伊朗', 'New-Zealand': '新西兰',
    'Cape-Verde': '佛得角', 'Saudi-Arabia': '沙特', 'Spain': '西班牙', 'Uruguay': '乌拉圭',
    'France': '法国', 'Norway': '挪威', 'Senegal': '塞内加尔', 'Iraq': '伊拉克',
    'Algeria': '阿尔及利亚', 'Argentina': '阿根廷', 'Austria': '奥地利', 'Jordan': '约旦',
    'Colombia': '哥伦比亚', 'Congo-DR': '刚果（金）', 'Portugal': '葡萄牙', 'Uzbekistan': '乌兹别克斯坦',
    'Croatia': '克罗地亚', 'England': '英格兰', 'Ghana': '加纳', 'Panama': '巴拿马',
}

TEAM_COLORS = {
    "Algeria": "#007229", "Argentina": "#75aadb", "Australia": "#ffcc00",
    "Austria": "#ed2939", "Belgium": "#c8102e", "Bosnia-and-Herzegovina": "#002395",
    "Brazil": "#fcd116", "Canada": "#e01111", "Cape-Verde": "#003366",
    "Colombia": "#fcd116", "Congo-DR": "#007f4f", "Cote-dIvoire": "#ff9900",
    "Croatia": "#e11a22", "Curacao": "#003399", "Czechia": "#11457e",
    "Ecuador": "#fcdd00", "Egypt": "#c8102e", "England": "#cf081f",
    "France": "#002395", "Germany": "#000000", "Ghana": "#ce1126",
    "Haiti": "#00209f", "IR-Iran": "#00843d", "Iraq": "#007a3d",
    "Japan": "#01043a", "Jordan": "#c8102e", "Korea-Republic": "#e60000",
    "Mexico": "#126f1e", "Morocco": "#c1272d", "Netherlands": "#ff6600",
    "New-Zealand": "#000000", "Norway": "#c8102e", "Panama": "#002a7f",
    "Paraguay": "#d52b1e", "Portugal": "#006600", "Qatar": "#7a1f3d",
    "Saudi-Arabia": "#006c35", "Scotland": "#003876", "Senegal": "#fcd116",
    "South-Africa": "#007a4d", "Spain": "#c60b1e", "Sweden": "#005b99",
    "Switzerland": "#e11a22", "Tunisia": "#e7002a", "Turkiye": "#e30a17",
    "United-States": "#002868", "Uruguay": "#002fa7", "Uzbekistan": "#0099b5",
}

def team_cn(slug):
    return SLUG_TO_CN.get(slug, slug.replace('-', ' '))

def generate():
    with open(ranking_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    top500 = data["deterministic"][:500]

    # Group by team
    teams = defaultdict(list)
    for p in top500:
        teams[p["team"]].append(p)

    # Sort players within each team by score desc
    for t in teams:
        teams[t].sort(key=lambda x: -x["final_projected_g"])

    # Sort teams by player count desc, then by total score desc
    sorted_teams = sorted(teams.keys(), key=lambda t: (-len(teams[t]), -sum(p["final_projected_g"] for p in teams[t])))

    total_players = len(top500)
    total_teams = len(sorted_teams)

    # Build HTML
    team_cards = []
    for team in sorted_teams:
        players = teams[team]
        color = TEAM_COLORS.get(team, "#4fc3f7")
        cn = team_cn(team)
        team_score = sum(p["final_projected_g"] for p in players)

        rows_html = ""
        for p in players:
            name_display = p.get("name_cn") or p["player"]
            eng_tooltip = p["player"]
            pos = p.get("pos", "")
            score = p["final_projected_g"]
            rank = p["rank"]
            xg = p.get("xg_proxy", 0)
            shrunk = p.get("shrunk_xg_per90", 0)
            pk = p.get("pk_bonus", 0)

            rank_badge = ""
            if rank <= 3:
                cls = ["rank-1", "rank-2", "rank-3"][rank - 1]
                rank_badge = f'<span class="rank-badge {cls}">{rank}</span>'
            else:
                rank_badge = f'<span class="rank-num">{rank}</span>'

            pk_cell = f'+{pk:.2f}' if pk > 0 else '<span class="zero">0</span>'

            rows_html += f"""<tr data-player="{eng_tooltip}">
  <td class="num">{rank_badge}</td>
  <td class="pname" title="{eng_tooltip}">{name_display}</td>
  <td class="pos-cell pos-{pos.split(',')[0].strip().lower()}">{pos}</td>
  <td class="num score-cell">{score:.2f}</td>
  <td class="num">{xg:.3f}</td>
  <td class="num">{shrunk:.3f}</td>
  <td class="num">{pk_cell}</td>
</tr>"""

        team_cards.append(f"""
<div class="team-card">
  <div class="team-header" style="border-left-color:{color}">
    <div class="team-title">
      <span class="team-badge" style="background:{color}"></span>
      <span class="team-cn">{cn}</span>
      <span class="team-en">{team.replace('-',' ')}</span>
    </div>
    <div class="team-stats">
      <span class="player-count">{len(players)}人</span>
      <span class="team-total">总分: {team_score:.2f}</span>
    </div>
  </div>
  <table class="team-table">
    <thead><tr>
      <th class="num">#</th><th>球员</th><th>位置</th>
      <th class="num">得分</th><th class="num">xG/90</th>
      <th class="num">Shrk</th><th class="num">PK</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>""")

    cards_html = "\n".join(team_cards)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 WC 射手排名 Top 500 (按国家队分组)</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #0f1923; color: #e0e0e0; padding: 20px; max-width: 1400px; margin: 0 auto; }}
h1 {{ text-align: center; margin-bottom: 4px; font-size: 26px; color: #fff; }}
.subtitle {{ text-align: center; color: #888; margin-bottom: 6px; font-size: 13px; }}
.summary {{ display: flex; justify-content: center; gap: 24px; margin-bottom: 20px; flex-wrap: wrap; }}
.summary-item {{ background: #1a2632; border: 1px solid #2a3a4a; border-radius: 8px; padding: 8px 16px; text-align: center; }}
.summary-item .val {{ font-size: 22px; font-weight: 700; color: #4fc3f7; }}
.summary-item .label {{ font-size: 11px; color: #888; margin-top: 2px; }}

/* Search */
.search-bar {{ display: flex; justify-content: center; margin-bottom: 20px; }}
.search-bar input {{ padding: 8px 14px; border-radius: 8px; border: 1px solid #333; background: #1a2632; color: #fff; font-size: 14px; width: 280px; }}
.search-bar input::placeholder {{ color: #666; }}

/* Team card */
.team-card {{ background: #151f2b; border: 1px solid #1e2e3e; border-radius: 10px; margin-bottom: 16px; overflow: hidden; }}
.team-header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #1a2632; border-left: 4px solid #4fc3f7; border-radius: 10px 10px 0 0; }}
.team-title {{ display: flex; align-items: center; gap: 10px; }}
.team-badge {{ width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }}
.team-cn {{ font-size: 18px; font-weight: 700; color: #fff; }}
.team-en {{ font-size: 12px; color: #888; }}
.team-stats {{ display: flex; gap: 16px; align-items: center; }}
.player-count {{ background: #2a3a4a; padding: 3px 10px; border-radius: 12px; font-size: 12px; color: #4fc3f7; font-weight: 600; }}
.team-total {{ font-size: 13px; color: #aaa; }}

/* Table */
.team-table {{ width: 100%; border-collapse: collapse; }}
.team-table th {{ background: #1e2e3e; padding: 6px 10px; text-align: left; font-size: 11px; color: #888; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #2a3a4a; }}
.team-table td {{ padding: 6px 10px; font-size: 13px; border-bottom: 1px solid #1a2530; }}
.team-table tr:hover {{ background: #1a2a3a; }}
.team-table .num {{ text-align: center; width: 50px; }}
.team-table .pname {{ font-weight: 600; color: #fff; white-space: nowrap; }}
.team-table .score-cell {{ color: #4fc3f7; font-weight: 700; }}
.team-table .zero {{ color: #555; }}
.team-table th.num {{ text-align: center; }}

/* Rank badges */
.rank-badge {{ display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 20px; border-radius: 4px; font-weight: 700; font-size: 11px; }}
.rank-1 {{ background: #ffd700; color: #000; }}
.rank-2 {{ background: #c0c0c0; color: #000; }}
.rank-3 {{ background: #cd7f32; color: #fff; }}
.rank-num {{ color: #888; font-size: 12px; }}

/* Position colors */
.pos-gk {{ color: #ff9800; }} .pos-fw {{ color: #e91e63; }}
.pos-mf {{ color: #4caf50; }} .pos-df {{ color: #2196f3; }}
.pos-cell {{ font-size: 11px; text-align: center; }}

/* Nav */
.nav {{ text-align: center; margin-bottom: 16px; }}
.nav a {{ color: #4fc3f7; text-decoration: none; font-size: 14px; padding: 6px 16px; border: 1px solid #2a3a4a; border-radius: 6px; background: #1a2632; transition: all 0.2s; }}
.nav a:hover {{ background: #243444; }}

/* Responsive grid */
@media (min-width: 900px) {{
  .team-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
}}

/* Hidden by search */
.team-card.hidden {{ display: none; }}

/* Selected player */
tr.selected {{ background: rgba(76, 175, 80, 0.15) !important; }}
tr.selected td {{ border-bottom-color: rgba(76, 175, 80, 0.3); }}
tr.selected .pname {{ color: #81c784; }}
.selected-badge {{ display: inline-block; background: #4caf50; color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 8px; margin-left: 6px; font-weight: 600; vertical-align: middle; }}
</style>
</head>
<body>
<h1>2026 世界杯射手排名 Top 500</h1>
<p class="subtitle">按国家队分组 · 国家队内按得分排序 · 国家队按球员人数排序</p>

<div class="summary">
  <div class="summary-item"><div class="val">{total_players}</div><div class="label">球员总数</div></div>
  <div class="summary-item"><div class="val">{total_teams}</div><div class="label">国家队数</div></div>
  <div class="summary-item"><div class="val">{sorted_teams[0].replace('-',' ')}</div><div class="label">人数最多</div></div>
</div>

<div class="nav">
  <a href="/stats">射手排名详情 →</a>
</div>

<div class="search-bar">
  <input type="text" id="search" placeholder="搜索球员或国家队 (中文/英文)..." />
</div>

<div class="team-grid" id="teamGrid">
{cards_html}
</div>

<script>
const search = document.getElementById('search');
const cards = document.querySelectorAll('.team-card');

search.addEventListener('input', () => {{
  const q = search.value.toLowerCase().trim();
  if (!q) {{
    cards.forEach(c => c.classList.remove('hidden'));
    return;
  }}
  cards.forEach(card => {{
    const header = card.querySelector('.team-header');
    const teamMatch = header.textContent.toLowerCase().includes(q);
    const rows = card.querySelectorAll('tbody tr');
    let playerMatch = false;
    rows.forEach(r => {{
      const name = r.querySelector('.pname');
      const title = name ? (name.getAttribute('title') || '') + ' ' + name.textContent : '';
      if (title.toLowerCase().includes(q)) {{
        r.style.display = '';
        playerMatch = true;
      }} else {{
        r.style.display = q ? 'none' : '';
      }}
    }});
    card.classList.toggle('hidden', !teamMatch && !playerMatch);
  }});
}});

// Auto-refresh selection status every 5 seconds
const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
function refreshSelections() {{
  fetch('/api/teams')
    .then(r => r.json())
    .then(teams => {{
      const selectedNames = new Set();
      teams.forEach(t => {{
        t.players.forEach(p => {{
          if (p.selected) selectedNames.add(norm(p.name));
        }});
      }});
      document.querySelectorAll('tbody tr[data-player]').forEach(row => {{
        const playerName = norm(row.getAttribute('data-player'));
        const pnameCell = row.querySelector('.pname');
        if (!pnameCell) return;
        const badge = pnameCell.querySelector('.selected-badge');
        if (selectedNames.has(playerName)) {{
          row.classList.add('selected');
          if (!badge) pnameCell.insertAdjacentHTML('beforeend', '<span class="selected-badge">已选</span>');
        }} else {{
          row.classList.remove('selected');
          if (badge) badge.remove();
        }}
      }});
    }})
    .catch(() => {{}});
}}
refreshSelections();
setInterval(refreshSelections, 5000);
</script>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML generated: {html_path}")
    print(f"Top 500 players across {total_teams} teams")
    print(f"Largest team: {team_cn(sorted_teams[0])} ({len(teams[sorted_teams[0]])} players)")

if __name__ == "__main__":
    generate()
