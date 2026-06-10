# 每日简报部署说明

站点：**https://tolerance.pythonanywhere.com/**

## 发布闸门

1. 本地验证（Mock 预览、`build_daily_briefing.py --mock`、Flask `/briefing`）
2. 用户 **Approve**
3. `git commit` / `git push`（**不要**在定时任务中使用 `--push`）
4. PA `git pull` + Web → Reload

## 个人电脑（每日构建）

```powershell
cd D:\AI\WorldCupGame
python scripts\build_daily_briefing.py
```

可选：

- `--mock` — 刷新示例 JSON 时间戳（**不写入** history）
- `--dry-run` — 校验将上传的 JSON，不 POST
- `--upload` — POST 到 `https://tolerance.pythonanywhere.com/api/import-briefing`（需 `IMPORT_BRIEFING_TOKEN`；含赛果校验，含测试比分会**拒绝上传**）

上传前必跑：

```powershell
python scripts\check_briefing_data.py
python scripts\build_daily_briefing.py --dry-run
```

**禁止**将 inject 脚本产生的比分 commit / upload。开赛前 `history_index` 应无带 `source: football-data` 以外的完赛记录。

赛前新闻来源（[`data/scraper_config.json`](data/scraper_config.json)）：

- **国内**：懂球帝 API（头条 + 国际）、直播8 足球滚动
- **国际 RSS**（`intl_feeds`）：ESPN、CBS Soccer、Sky News；BBC / Guardian 在可访问时自动并入（失败则跳过）
- **队名搜索**：Google News RSS（中/英队名 + 世界杯），可选关闭 `team_search_rss`

密钥文件（勿提交 git）：

- `static/basedata/football-data.txt`
- `static/basedata/AIKey.txt`
- `static/basedata/teamInfo.txt`

## 比赛介绍页元数据

**一次性脚本**（赛程/大本营变更后重跑）：

```powershell
python scripts\generate_world_cup_bases.py
python scripts\enrich_fixture_venue_context.py
python scripts\fetch_squad_ages.py
python scripts\fetch_national_caps.py
python scripts\fetch_coaches_dongqiudi.py
python scripts\build_team_squad_meta.py
```

- `fetch_squad_ages.py`：从 **football-data.org** 拉取名单出生日期 → `squad_player_ages.json`，用于**平均年龄**。
- `fetch_national_caps.py`：从 **Transfermarkt 开放数据集** 匹配 `wc_squads.json` 26 人名单的**国脚生涯出场** → `squad_national_caps.json`，用于**球队结构**（多≥30 / 中10–29 / 少&lt;10 场）。
- `fetch_coaches_dongqiudi.py`：教练中文名（懂球帝 + `coach_team_defaults.json`）。
- `build_team_squad_meta.py` 合并上述三项；缺文件时会自动调用对应 fetch 脚本。

产出：

| 文件 | 内容 |
|------|------|
| `data/stadium_venues.json` | 16 球场海拔/坐标 |
| `data/team_world_cup_bases.json` | 48 队大本营 |
| `data/fixtures_2026.json` | 每场 `venue_context`、`home_travel`、`away_travel` |
| `data/squad_player_ages.json` | 名单球员年龄（football-data.org） |
| `data/squad_national_caps.json` | 名单球员国脚生涯出场（Transfermarkt） |
| `data/coach_world_cup.json` | 48 队主教练中文名、任期 |
| `data/coach_team_defaults.json` | 教练中文名兜底（懂球帝/API 无数据时） |
| `data/team_squad_meta.json` | 平均年龄、球队结构、教练 |

**每日构建**（`build_daily_briefing.py`）额外写入：

- `latest.json` 每场 `odds`（BetExplorer 免费抓取，失败时用 `match_odds_seed.json` 兜底）
- `data/briefing/match_odds.json`（赔率缓存，按 `fixture_id`）
- `data/briefing/team_form.json`（近 5 场战绩 + 预选赛进失球风格；ESPN `fifa.worldq.*` 赛程，场均进/失球比 ≥1.3 进攻型、≤0.8 防守型；主办国显示「主办国免预选赛」）

Flask `/match/<id>` 只读上述 JSON，无需 PA 再跑脚本。

### 赔率（免费，无需 API Key）

- 数据源：[BetExplorer 世界杯赛程页](https://www.betexplorer.com/football/world/world-cup-2026/fixtures/) 公开 1X2 欧赔
- 配置：[`data/scraper_config.json`](data/scraper_config.json) → `odds.fixtures_url`
- 抓取失败或页面暂无该场次时，使用 [`data/briefing/match_odds_seed.json`](data/briefing/match_odds_seed.json) 兜底
- **不写入** `instance/draft.db`，构建前后 `selections` 条数应一致

## Windows 任务计划（每日 20:00）

一键注册（PowerShell **管理员可选**，当前用户即可）：

```powershell
cd D:\AI\WorldCupGame
powershell -ExecutionPolicy Bypass -File scripts\register_daily_briefing_task.ps1
```

| 项 | 值 |
|----|-----|
| 任务名 | `WorldCupGame-DailyBriefing` |
| 触发 | 每天 **20:00**（本机本地时间，北京时间） |
| 程序 | `python.exe` |
| 参数 | `D:\AI\WorldCupGame\scripts\build_daily_briefing.py --upload` |
| 起始于 | `D:\AI\WorldCupGame` |

**不加** `--push`。需本机 20:00 在线；`IMPORT_BRIEFING_TOKEN` 与 PA 环境变量一致。

### 球场图与 Logo

```powershell
python scripts\download_stadium_photos.py
```

图源：[ArchDaily 中文网](https://www.archdaily.cn/cn/993991/2026nian-fifashi-jie-bei-zai-mei-guo-zai-mo-xi-ge-zai-jia-na-da)（`images.adsttc.com`，国内可访问）。16 张球场图在 `static/stadiums/`；WC Logo 为 `static/wc2026-logo.svg`。

## PythonAnywhere

```bash
cd ~/WorldCupGame && git pull
# Web tab → Reload
```

`IMPORT_BRIEFING_TOKEN` 在 PA Web 环境变量中配置，与 PC 上传时一致。

## 冒烟测试

```powershell
pip install cursor-sdk python-dotenv
python scripts\smoke_cursor_sdk.py
python scripts\check_briefing_data.py
python scripts\build_daily_briefing.py --mock
python -c "from app import app; from briefing_data import history_dates_payload; print(history_dates_payload())"
```
