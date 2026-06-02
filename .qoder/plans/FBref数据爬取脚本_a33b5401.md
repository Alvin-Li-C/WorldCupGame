# FBref世界杯预选赛(WCQ)数据爬取

## 目标
从FBref获取10支热门世界杯球队在预选赛(WCQ)中的球员数据，用于智能预选算法的评分计算。

## 数据源确认

**关键：必须选择 "WCQ" 选项卡**

FBref国家队页面有三个选项：
- ❌ All Competitions（所有比赛）
- ✅ **WCQ — UEFA/CONMEBOL/AFC/CAF (M)**（预选赛）← 选择这个
- ❌ Friendlies (M)（友谊赛）

URL格式：
- UEFA预选赛: `fbref.com/en/comps/6/WCQ----UEFA-M-Stats`
- CONMEBOL预选赛: `fbref.com/en/comps/4/WCQ----CONMEBOL-M-Stats`
- AFC预选赛: `fbref.com/en/comps/5/WCQ----AFC-M-Stats`
- CAF预选赛: `fbref.com/en/comps/7/WCQ----CAF-M-Stats`

## 数据范围

### 10支热门球队
| 序号 | 球队 | 所属大洲 | FBref队伍ID |
|------|------|---------|-------------|
| 1 | 西班牙 | UEFA | b561dd30 |
| 2 | 阿根廷 | CONMEBOL | a22c25fc |
| 3 | 法国 | UEFA | d326e8e3 |
| 4 | 英格兰 | UEFA | 195a7302 |
| 5 | 巴西 | CONMEBOL | 2cdc1f7c |
| 6 | 德国 | UEFA | 978e5e4d |
| 7 | 葡萄牙 | UEFA | 837e3b29 |
| 8 | 荷兰 | UEFA | 6a8de82e |
| 9 | 比利时 | UEFA | da39b04f |
| 10 | 哥伦比亚 | CONMEBOL | 11b1e72c |

### 需要获取的字段

**Standard Stats（射门统计）：**
- Player, Pos, Age, 90s, Gls（进球）, Sh（射门）, SoT（射正）, SoT%（射正率）
- Sh/90, SoT/90, G/Sh（射门转化率）, G/SoT, PK（点球）, PKatt（点球尝试）

**Playing Time（出场时间）：**
- MP（出场次数）, Starts（首发次数）, Min（上场分钟）, 90s

**Miscellaneous Stats（杂项统计）：**
- OG（乌龙球）— 仅此列

## 实现方案

### Task 1: 安装依赖
```bash
pip install soccerdata pandas selenium
```

### Task 2: 创建数据爬取脚本

**文件**: `scripts/fetch_fbref_wcq_data.py`

```python
import soccerdata as sd
import pandas as pd
import time

# 10支热门球队
TEAMS = {
    "西班牙": {"id": "b561dd30", "confed": "UEFA"},
    "阿根廷": {"id": "a22c25fc", "confed": "CONMEBOL"},
    "法国": {"id": "d326e8e3", "confed": "UEFA"},
    "英格兰": {"id": "195a7302", "confed": "UEFA"},
    "巴西": {"id": "2cdc1f7c", "confed": "CONMEBOL"},
    "德国": {"id": "978e5e4d", "confed": "UEFA"},
    "葡萄牙": {"id": "837e3b29", "confed": "UEFA"},
    "荷兰": {"id": "6a8de82e", "confed": "UEFA"},
    "比利时": {"id": "da39b04f", "confed": "UEFA"},
    "哥伦比亚": {"id": "11b1e72c", "confed": "CONMEBOL"},
}

def fetch_wcq_data(team_name, team_id, confed):
    """
    获取单支球队WCQ预选赛数据
    
    关键：使用 leagues="WCQ — {confed} (M)" 来选择预选赛数据
    """
    league_name = f"WCQ — {confed} (M)"
    
    # 初始化FBref（会自动选择WCQ选项卡）
    fbref = sd.FBref(leagues=league_name, seasons="2026")
    
    # 1. Playing Time 数据
    playing_time = fbref.read_player_season_stats(stat_type="playing_time")
    
    # 2. Standard Stats (射门、xG等)
    standard = fbref.read_player_season_stats(stat_type="standard")
    
    # 3. Miscellaneous Stats (乌龙球)
    misc = fbref.read_player_season_stats(stat_type="misc")
    
    # 合并数据
    merged = playing_time.merge(
        standard[['Player', 'Pos', 'Age', 'Gls', 'Sh', 'SoT', 'PK', 'PKatt', 'xG']],
        on='Player', how='left'
    ).merge(
        misc[['Player', 'OG']],
        on='Player', how='left'
    )
    
    return merged

def fetch_all_teams():
    """爬取所有48支球队数据"""
    all_data = {}
    
    for team_name, info in TEAMS.items():
        print(f"正在获取 {team_name} 数据...")
        try:
            data = fetch_wcq_data(team_name, info['id'], info['confed'])
            all_data[team_name] = data.to_dict('records')
            time.sleep(3)  # 避免被限流
        except Exception as e:
            print(f"获取 {team_name} 失败: {e}")
    
    return all_data

if __name__ == "__main__":
    data = fetch_all_teams()
    
    # 保存为JSON
    import json
    with open('data/wcq_player_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"成功获取 {len(data)} 支球队数据")
```

### Task 3: 数据验证
验证爬取的数据完整性：
- 10支球队全部有数据
- 每队约15-25名球员
- 关键字段（Gls, Sh, MP, Min）无缺失

## 前置条件
- Python 3.8+
- 安装依赖: `pip install soccerdata pandas selenium`
- Chrome浏览器（Selenium需要）
- FBref限流：每次请求间隔3秒

## 预期产出
`data/wcq_player_stats.json` - 包含10支球队、约200名球员WCQ预选赛数据的JSON文件：

```json
{
  "西班牙": [
    {
      "player": "Lamine Yamal",
      "pos": "FW",
      "age": 18,
      "mp": 6,
      "min": 480,
      "90s": 5.3,
      "starts": 5,
      "gls": 4,
      "sh": 25,
      "sot": 12,
      "pk": 1,
      "pkatt": 1,
      "og": 0
    }
  ],
  ...
}
```