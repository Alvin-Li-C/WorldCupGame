# 射门评分算法 V2 — 基于球队实力调整的射手预测

## 1. 核心问题与解决思路

### 1.1 原方案的致命缺陷
原方案**没有考虑球队实力差异**：
- 强队（西班牙、法国）预期踢 7 场，弱队（海地、库拉索）只踢 3 场
- 强队场均创造 3-5 次射门机会，弱队场均 1-2 次
- 直接比较 WCQ 原始数据 = 拿中国预选赛数据预测世界杯表现

### 1.2 行业标准方法调研
研究了目前主流的世界杯射手预测模型，包括：

**A. PredictionMarketPicks Monte Carlo + Goal Share**（行业标杆）
- 10,000 次完整赛事蒙特卡洛模拟
- 每场比赛用 Poisson 分布模拟比分
- 将球队总进球按**球员历史进球占比**分配给个人
- PK 权获得 0.3-0.5 球的加成
- 结果：前 10 名中 8 人是点球手

**B. onthepitch 三层集成模型**
- Elo 评分（基线）、Dixon-Coles 双变量 Poisson（攻防参数）、Hierarchical Poisson（贝叶斯）
- 50,000 次蒙特卡洛 bracket 模拟

**C. Sports-ai.dev AI 模型**
- 使用球员 WCQ 效率 + 球队预期比赛场次 + PK 权 + 年龄
- 特征驱动，非暴力模拟

### 1.3 本方案采用的方法

我们采用 **Goal-Share Distribution + Monte Carlo 简化版**，核心思想：

**不要给指标分配权重，而是从团队总产出出发，按球员历史贡献占比分配**

```
团队层面：每支球队在世界杯中的预期总进球（来自 Rotowire Monte Carlo 模拟）
         ↓
球员层面：按球员在 WCQ 中占球队进球/进攻产出的比例，分配到个人
         ↓
PK 加成：点球手额外增加预期进球
         ↓
效率微调：有射门数据的球员，用 G/Sh 和 SoT% 微调预期（修正 WCQ 样本偏差）
```

## 2. 算法设计

### 2.1 数据源

**来源 A: Rotowire 团队预期进球**（来自他们的 Monte Carlo 模型）

Rotowire Expected Games 计算方法：
```
Expected Games = 3（小组赛保底）
               + P(小组出线)    → 踢 1/32 决赛
               + P(进16强)      → 踢 1/16 决赛
               + P(进8强)       → 踢 1/4 决赛
               + P(进4强)       → 踢 半决赛
               + P(进4强)       → 踢 决赛或三四名（半决赛后人人都有第 8 场）
               （最大 8 场）
```
注意：最后一项直接用 P(进4强)，因为无论半决赛输赢，每支半决赛球队都会再踢一场（赢→决赛，输→三四名决赛）。
等价公式：`3 + P(R32) + P(R16) + P(QF) + 2 × P(SF)`，最大 8 场。
每轮晋级概率来自 Rotowire 的球队攻防实力评级模型 + 博彩市场赔率 + 小组对手分析。

完整的 48 队映射表（按预期进球降序）：

| # | 我们的 Slug | Rotowire 名称 | 大洲 | 预期场次 | 预期进球 |
|---|------------|--------------|------|---------|---------|
| 1 | Spain | Spain | UEFA | 7.0 | 15.1 |
| 2 | Germany | Germany | UEFA | 5.8 | 12.2 |
| 3 | Brazil | Brazil | CONMEBOL | 6.3 | 11.8 |
| 4 | France | France | UEFA | 6.8 | 11.2 |
| 5 | England | England | UEFA | 6.4 | 10.0 |
| 6 | Argentina | Argentina | CONMEBOL | 6.1 | 9.5 |
| 7 | Portugal | Portugal | UEFA | 5.9 | 9.1 |
| 8 | Belgium | Belgium | UEFA | 5.2 | 8.7 |
| 9 | Netherlands | Netherlands | UEFA | 5.3 | 8.0 |
| 10 | Switzerland | Switzerland | UEFA | 4.7 | 7.4 |
| 11 | Colombia | Colombia | CONMEBOL | 4.9 | 6.8 |
| 12 | Mexico | Mexico | CONCACAF | 4.5 | 6.6 |
| 13 | Norway | Norway | UEFA | 5.0 | 6.5 |
| 14 | Uruguay | Uruguay | CONMEBOL | 4.7 | 6.1 |
| 15 | Croatia | Croatia | UEFA | 4.4 | 6.0 |
| 16 | Morocco | Morocco | CAF | 4.7 | 5.5 |
| 17 | United-States | USA | CONCACAF | 4.5 | 5.2 |
| 18 | Austria | Austria | UEFA | 4.2 | 5.1 |
| 19 | Canada | Canada | CONCACAF | 4.1 | 4.8 |
| 20 | Ecuador | Ecuador | CONMEBOL | 4.4 | 4.7 |
| 21 | Japan | Japan | AFC | 4.4 | 4.7 |
| 22 | Cote-dIvoire | Ivory Coast | CAF | 4.0 | 4.4 |
| 23 | Senegal | Senegal | CAF | 4.1 | 4.4 |
| 24 | Scotland | Scotland | UEFA | 4.0 | 4.4 |
| 25 | Egypt | Egypt | CAF | 3.9 | 4.3 |
| 26 | Czechia | Czech Republic | UEFA | 3.9 | 4.1 |
| 27 | Turkiye | Turkey | UEFA | 4.2 | 4.1 |
| 28 | Algeria | Algeria | CAF | 3.7 | 3.9 |
| 29 | Sweden | Sweden | UEFA | 4.0 | 3.9 |
| 30 | Bosnia-and-Herzegovina | Bosnia | UEFA | 3.7 | 3.8 |
| 31 | Korea-Republic | South Korea | AFC | 3.8 | 3.6 |
| 32 | IR-Iran | Iran | AFC | 3.7 | 3.6 |
| 33 | Ghana | Ghana | CAF | 3.6 | 3.2 |
| 34 | Paraguay | Paraguay | CONMEBOL | 3.8 | 3.2 |
| 35 | Australia | Australia | AFC | 3.5 | 2.8 |
| 36 | Cape-Verde | Cabo Verde | CAF | 3.3 | 2.7 |
| 37 | Tunisia | Tunisia | CAF | 3.4 | 2.6 |
| 38 | South-Africa | South Africa | CAF | 3.4 | 2.4 |
| 39 | Saudi-Arabia | Saudi Arabia | AFC | 3.4 | 2.3 |
| 40 | New-Zealand | New Zealand | OFC | 3.3 | 2.3 |
| 41 | Qatar | Qatar | AFC | 3.3 | 2.3 |
| 42 | Uzbekistan | Uzbekistan | AFC | 3.3 | 2.2 |
| 43 | Panama | Panama | CONCACAF | 3.3 | 2.2 |
| 44 | Congo-DR | DR Congo | CAF | 3.4 | 2.2 |
| 45 | Jordan | Jordan | AFC | 3.2 | 2.0 |
| 46 | Iraq | Iraq | AFC | 3.1 | 1.9 |
| 47 | Haiti | Haiti | CONCACAF | 3.1 | 1.8 |
| 48 | Curacao | Curacao | CONCACAF | 3.1 | 1.6 |

**来源 B: FIFA World Ranking (June 2026)** — 辅助校验球队实力
**来源 C: WCQ 球员数据** — 我们已经爬取的 G/90, Sh/90, SoT%, G/Sh, PK 等

### 2.2 核心算法：Goal-Share Distribution

不再给指标分配权重，而是用 **目标分配法**：从团队预期总产出出发，按球员历史占比分配。

#### Step 1: 计算球员在 WCQ 中的进攻产出占比
```
  对于每支球队，计算所有球员的"进攻贡献率"：
  
  每个球员的原始进攻产出（两种方案，选较好的一种）：
    Plan A — 纯射手:  goal_share_weight = gls / nineties        (进球率)
    Plan B — 进攻贡献: contrib_weight = (gls + ast) / nineties  (进球+助攻率)
  
  注意:
    - gls 是球员为球队攻入的进球（不包括乌龙球）
    - og 是乌龙球（攻入自家球门），与 gls 完全独立
    - og 不计入球员的进攻产出——乌龙球不帮助球队得分
    - og 在排名表中作为独立信息展示（"该球员在WCQ中打入 X 个乌龙球"）
  
  最终采用: player_raw_rate = max(goal_share_weight, contrib_weight × 0.7)
    — 进球率为主，助攻率打 7 折（助攻间接贡献）
  
  球员占球队进攻产出比例:
    player_share = player_raw_rate / Σ(all_teammates_raw_rates)
    — 例如 Mbappe 占法国总进攻产出的 25%，则他预期获得法国 25% 的世界杯进球
```

### Step 2: 计算预期世界杯进球 (Projected WC Goals)
```
  Team_Projected_Goals 来自 Rotowire 文章（详见上表"预期进球"列）：
    西班牙 15.1, 德国 12.2, 巴西 11.8, 法国 11.2, 英格兰 10.0,
    阿根廷 9.5, 葡萄牙 9.1, 比利时 8.7, 荷兰 8.0, 瑞士 7.4,
    海地 1.8, 伊拉克 1.9, 库拉索 1.6
    (完整 48 队数据见上表)

  Base_Projected_G = Team_Projected_Goals × player_share
    — 这是该球员在世界杯中的"基准预期进球"

  举例 — 法国队:
    法国预期总进球 = 11.2
    Mbappe 占法国进攻产出 25% → Base = 11.2 × 0.25 = 2.80 球
    登贝莱 占法国进攻产出 12% → Base = 11.2 × 0.12 = 1.34 球
```

**关键优势**：这个方法是自洽的——同一队所有球员的预期进球之和 = 该队预期总进球。

#### Step 3: PK 加成（点球手额外加分）
```
  来自行业研究：PK 权在赛事中额外贡献 0.3-0.5 球。
  
  if pkatt > 0:
    PK_bonus = PK_per_90 × Expected_WC_90s × (pk/pkatt if pkatt > 0 else 0.76)
    
    其中:
      Expected_WC_90s = Expected_Games × WC_Adjusted_Ratio
      
      WC_Adjusted_Ratio 考虑小组赛轮换:
        WCQ_base_ratio = min(1.0, WCQ_min / (WCQ_MP × 90))
        Team_Rotation_Factor:
          预期场次 >= 6.0: 0.80（西班牙/法国/英格兰/巴西/阿根廷）
          预期场次 >= 5.0: 0.85（葡萄牙/德国/荷兰/比利时/挪威）
          预期场次 >= 4.0: 0.90（哥伦比亚/瑞士/乌拉圭/摩洛哥等）
          预期场次 <  4.0: 0.95（弱队）
        WC_Adjusted_Ratio = WCQ_base_ratio × Team_Rotation_Factor
    
  else:
    PK_bonus = 0
```

#### Step 4: 效率微调（有射门数据的球员）
```
  对于有射门数据的球员（sh > 0），用射击转化率微调基准预期：
  
  G_Sh_ratio = WCQ_G_per_Sh / Team_Avg_G_per_Sh
    — 如果球员转化率远高于队友平均，说明他的进球能力被低估了
    — 反之如果远低于平均，说明他可能运气好（或罚点球多）
  
  Efficiency_Adjustment = clamp(G_Sh_ratio, 0.7, 1.3)
    — 限制在 ±30%，防止极端值
  
  Final_Projected_G = Base_Projected_G × Efficiency_Adjustment + PK_bonus
```

#### Step 5: 最终排名 = 选秀预选顺序
```
  所有 48 队、2061 名球员统一按以下规则排序：
    
  总分 = Final_Projected_G（预期世界杯进球）— 降序
  同分则 OG（乌龙球多者优先）— 因为本游戏中 OG 也算进球
  
  即: sort by (-final_projected_g, -og)
  
  Top 3 示例：
    1. Mbappe   总分 3.15  OG 0
    2. Kane     总分 2.72  OG 0
    3. Haaland  总分 2.72  OG 0  (若与 Kane 同分，且 OG 相同)
    ...
    若 Kane 2.72 OG 1, Haaland 2.72 OG 0 → Kane 排前
  
  输出格式：
    {
      "rank": 1,
      "player": "Kylian Mbappe",
      "team": "France",
      "pos": "FW",
      "team_share": 0.25,        // 占全队进攻产出 25%
      "final_projected_g": 3.15, // 总分（最终预期进球）← 主排序
      "og": 0,                   // 乌龙球 ← 次排序（同分时 OG 高者前）
      "base_projected_g": 2.80,  // 运动战预期
      "pk_bonus": 0.35,          // 点球附加
      "efficiency_adj": 1.05,    // 效率微调
      "gls": 8, "ast": 3,       // WCQ 实绩
      "sh": 45, "nineties": 10.5,
      "pk": 2, "pkatt": 2
    }
```

### 2.3 为什么这种方法比权重法更好
| 方面 | 旧方法（权重法） | 新方法（Goal-Share Distribution） |
|------|----------------|-----------------------------------|
| 理论基础 | 主观分配权重 | 基于团队总产出按比例分配（行业标准） |
| 自洽性 | 球员评分和=100，不与实际进球关联 | 全队预期进球之和=Rotowire团队预期 |
| 数据覆盖 | 仅 30 队有射门数据 | **全部 48 队**（用进球+助攻即可） |
| 黑马检测 | 权重完全主观 | 小球队高效射手通过 share 自然浮现 |
| 可比性 | 跨球队直接比原始值 | 每人在各自球队框架内比较 |

## 3. 实施步骤

#### 步骤 1：创建 `/scripts/shooting_ranking.py`
逻辑脚本：
- 加载 `wcq_player_stats.json`
- 内置 Rotowire 团队预期进球映射表（48 队，含 Expected Games 和 Projected Goals）
- **Step A**: 对每支球队，计算所有球员的原始进攻产出率（gls/90 或 (gls+ast)/90）
- **Step B**: 归一化为占比（player_share = 球员率 / 全队率和）
- **Step C**: 乘以球队预期总进球 → Base_Projected_G
- **Step D**: 计算 PK_bonus（含轮换调整的 Expected_WC_90s）
- **Step E**: 对有射门数据的球员做 G/Sh 效率微调 → Final_Projected_G
- **Step F**: 按 Final_Projected_G 降序排名，附带排名序号
- **导出**: `data/player_ranking.json` — 所有 2061 名球员的排名数据（含中间变量）

### 步骤 2：修改 `/scripts/generate_stats_html_v2.py`

新增 **"射手排名"标签页**，独立展示完整排名：

**HTML 结构：**
- 标签切换在顶部：`[完整数据] [射手排名]`
- 默认显示射手排名页

**排名展示（全量 2061 人）：**
| 排名 | 球员 | 球队 | 位置 | 占队比 | **总分** | PK附加 | OG | G/90 | Sh/90 |
|------|------|------|------|--------|---------|--------|-----|------|-------|
- **排名** — 1, 2, 3 ... 2061
- **总分** — Final_Projected_G，排序主依据（反应该球员在世界杯中的预期进球）
- **OG** — 同分时 OG 高者排前（因为本游戏中 OG 算进球）
- **占队比** — 该球员占全队进攻产出百分比
- **PK附加** — 点球带来的额外预期进球

**交互功能：**
- 搜索框（按球员名/球队筛选）
- 位置筛选（全部 / FW / MF / DF / GK）
- 列排序切换（点击表头按预期进球/G/90/Sh/90 等排序）
- 显示当前条目数 "Showing X / 2061 players"
- 排名列带奖牌图标（Top 3：金/银/铜）

### 步骤 3：重新生成 HTML
- 运行 `shooting_ranking.py` → 生成 `player_ranking.json`
- 运行 `generate_stats_html_v2.py` → 加载排名数据，生成 `wcq_player_stats_table.html`
- 服务器（localhost:5500）自动刷新

## 4. 修改的文件
- `scripts/shooting_ranking.py` — **新建**，Goal-Share 算法引擎，输出 `player_ranking.json`
- `scripts/generate_stats_html_v2.py` — **修改**，添加"射手排名"标签页 + 加载排名 JSON 数据
- `data/player_ranking.json` — **新建**，2061 名球员完整排名数据
- `data/wcq_player_stats_table.html` — **重新生成**，含完整数据 + 射手排名双标签页

## 5. 算法效果预期

### 预期排名 Top 15（基于 Goal-Share Distribution，参考博彩市场验证）
| 排名 | 球员 | 球队 | 占队比 | 预期进球 | 说明 |
|------|------|------|--------|---------|------|
| 1 | Kylian Mbappe | France | ~25% | ~3.0 | 法国预期 11.2 球，Mbappe 占 1/4 + PK 手 |
| 2 | Harry Kane | England | ~22% | ~2.7 | 英格兰 10.0 球，Kane 主导 + PK |
| 3 | Erling Haaland | Norway | ~35% | ~2.5 | 挪威预期 6.5 球但 Haaland 占比极高 + PK |
| 4 | Lautaro Martinez | Argentina | ~20% | ~2.3 | 阿根廷 9.5 球 |
| 5 | Vinicius Jr | Brazil | ~18% | ~2.4 | 巴西 11.8 球 |
| 6 | Alvaro Morata | Spain | ~15% | ~2.2 | 西班牙 15.1 球，但得分点分散 |
| 7 | Cristiano Ronaldo | Portugal | ~20% | ~2.2 | 葡萄牙 9.1 球 + PK |
| 8 | Cody Gakpo | Netherlands | ~20% | ~2.1 | 荷兰 8.0 球 |
| 9 | Son Heung-min | Korea Republic | ~35% | ~2.1 | 韩国预期 3.6 球但 Son 占比极高 + PK |
| 10 | Romelu Lukaku | Belgium | ~20% | ~2.1 | 比利时 8.7 球 |
| ... | | | | | |
| — | Lionel Messi | Argentina | ~12% | ~1.5 | 年龄+角色变化导致占比下降 |
| — | Viktor Gyokeres | Sweden | ~30% | ~1.5 | 瑞典预期 3.9 球但个人占比极高(黑马) |

### 与博彩市场一致性验证
算法结果应与 DraftKings 金靴赔率强相关（Spearman rank correlation > 0.85）。
