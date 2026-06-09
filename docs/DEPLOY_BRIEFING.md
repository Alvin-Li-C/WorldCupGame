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
