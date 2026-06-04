"""Goal-Share Distribution Algorithm for WCQ Player Shooting Rankings
Computes expected WC goals for all 2061 players using Rotowire projections.
Also runs Monte Carlo simulation for luck-adjusted rank ranges.
"""
import json
import os
import sys
import random
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Use filtered data (only 26-man WC squad players) if available
filtered_path = os.path.join(DATA_DIR, "wcq_player_stats_filtered.json")
if os.path.exists(filtered_path):
    json_path = filtered_path
    print("Using filtered data (WC 26-man squads only)")
else:
    json_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
    print("Using full WCQ data")
    
output_path = os.path.join(DATA_DIR, "player_ranking.json")

# ── Rotowire data: slug → (Expected Games, Projected Goals) ──
TEAM_PROJECTIONS = {
    "Spain": (7.0, 15.1), "Germany": (5.8, 12.2), "Brazil": (6.3, 11.8),
    "France": (6.8, 11.2), "England": (6.4, 10.0), "Argentina": (6.1, 9.5),
    "Portugal": (5.9, 9.1), "Belgium": (5.2, 8.7), "Netherlands": (5.3, 8.0),
    "Switzerland": (4.7, 7.4), "Colombia": (4.9, 6.8), "Mexico": (4.5, 6.6),
    "Norway": (5.0, 6.5), "Uruguay": (4.7, 6.1), "Croatia": (4.4, 6.0),
    "Morocco": (4.7, 5.5), "United-States": (4.5, 5.2), "Austria": (4.2, 5.1),
    "Canada": (4.1, 4.8), "Ecuador": (4.4, 4.7), "Japan": (4.4, 4.7),
    "Cote-dIvoire": (4.0, 4.4), "Senegal": (4.1, 4.4), "Scotland": (4.0, 4.4),
    "Egypt": (3.9, 4.3), "Czechia": (3.9, 4.1), "Turkiye": (4.2, 4.1),
    "Algeria": (3.7, 3.9), "Sweden": (4.0, 3.9), "Bosnia-and-Herzegovina": (3.7, 3.8),
    "Korea-Republic": (3.8, 3.6), "IR-Iran": (3.7, 3.6), "Ghana": (3.6, 3.2),
    "Paraguay": (3.8, 3.2), "Australia": (3.5, 2.8), "Cape-Verde": (3.3, 2.7),
    "Tunisia": (3.4, 2.6), "South-Africa": (3.4, 2.4), "Saudi-Arabia": (3.4, 2.3),
    "New-Zealand": (3.3, 2.3), "Qatar": (3.3, 2.3), "Uzbekistan": (3.3, 2.2),
    "Panama": (3.3, 2.2), "Congo-DR": (3.4, 2.2), "Jordan": (3.2, 2.0),
    "Iraq": (3.1, 1.9), "Haiti": (3.1, 1.8), "Curacao": (3.1, 1.6),
}

def rotation_factor(exp_games):
    """Team rotation factor based on expected tournament longevity."""
    if exp_games >= 6.0: return 0.80
    if exp_games >= 5.0: return 0.85
    if exp_games >= 4.0: return 0.90
    return 0.95

def compute_ranking(data, team_proj_override=None, min_n90=2.0):
    """
    Core algorithm: Goal-Share Distribution.
    Returns list of dicts sorted by score descending.
    team_proj_override: optional dict {slug: projected_goals} for MC simulation.
    min_n90: minimum 90-min units for full rate calculation.
            Players below this threshold have rates dampened (shrinkage) to
            prevent small-sample bias (e.g. 1 goal in 18 min → absurd rate).
    """
    # Load player data
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ── Precompute team-level stats ──
    team_g_sh_avg = {}  # team → avg G/Sh ratio
    for team, players in data.items():
        total_sh = sum(p.get("sh", 0) for p in players)
        total_g = sum(p.get("gls", 0) for p in players)
        team_g_sh_avg[team] = (total_g / total_sh) if total_sh > 0 else None

    # ── Step A: Compute each player's offensive output rate ──
    team_raw_rates = defaultdict(list)  # team → [(player_idx, raw_rate)]
    all_players = []  # flat list with team reference

    for team, players in data.items():
        proj_games, proj_goals = TEAM_PROJECTIONS.get(team, (3.0, 2.0))
        # Override projected goals for MC simulations
        if team_proj_override and team in team_proj_override:
            proj_goals = team_proj_override[team]

        for p in players:
            nineties = p.get("nineties", 0)
            if nineties <= 0:
                continue

            gls = p.get("gls", 0)
            ast = p.get("ast", 0)
            pk = p.get("pk", 0)
            pkatt = p.get("pkatt", 0)

            # Plan A: pure goal rate
            goal_rate = gls / nineties
            # Plan B: contribution rate (G+A, discounted 30%)
            contrib_rate = (gls + ast) / nineties * 0.7
            player_raw_rate = max(goal_rate, contrib_rate)

            # Small-sample shrinkage: dampen rates for players with limited minutes
            # Prevents 1 goal in 18 min → absurd 5.0 rate
            sample_ratio = min(1.0, nineties / min_n90)
            effective_rate = player_raw_rate * sample_ratio

            team_raw_rates[team].append((p, effective_rate, proj_games, proj_goals, player_raw_rate))

    # ── Step B: Normalize to share percentages ──
    for team, player_list in team_raw_rates.items():
        total_rate = sum(item[1] for item in player_list)
        if total_rate == 0:
            continue

        for p, effective_rate, proj_games, proj_goals, raw_rate in player_list:
            share = effective_rate / total_rate

            # ── Step C: Base projected goals ──
            base_g = proj_goals * share

            # ── Step D: PK bonus ──
            pk = p.get("pk", 0)
            pkatt = p.get("pkatt", 0)
            nineties = p.get("nineties", 0)

            if pkatt > 0 and nineties > 0:
                pk_per_90 = pk / nineties
                pk_success_rate = pk / pkatt if pkatt > 0 else 0.76

                # Expected WC minutes with rotation adjustment
                mp = p.get("mp", 0)
                minutes = p.get("min", 0)
                wcq_base_ratio = min(1.0, minutes / (mp * 90)) if mp > 0 else 0.5
                team_rot_factor = rotation_factor(proj_games)
                wc_adjusted_ratio = wcq_base_ratio * team_rot_factor
                expected_wc_90s = proj_games * wc_adjusted_ratio

                pk_bonus = pk_per_90 * expected_wc_90s * pk_success_rate
            else:
                pk_bonus = 0

            # ── Step E: Efficiency adjustment ──
            sh = p.get("sh", 0)
            gls = p.get("gls", 0)
            efficiency_adj = 1.0

            if sh > 0 and team_g_sh_avg[team] and team_g_sh_avg[team] > 0:
                player_g_sh = gls / sh
                g_sh_ratio = player_g_sh / team_g_sh_avg[team]
                efficiency_adj = max(0.7, min(1.3, g_sh_ratio))

            final_g = base_g * efficiency_adj + pk_bonus

            # Sort by (-final_g, -og) for tiebreak
            all_players.append({
                "player": p["player"],
                "team": team,
                "pos": p["pos"],
                "team_share": round(share * 100, 1),     # percentage
                "final_projected_g": round(final_g, 3),
                "og": p.get("og", 0),
                "base_projected_g": round(base_g, 3),
                "pk_bonus": round(pk_bonus, 3),
                "efficiency_adj": round(efficiency_adj, 3),
                "gls": gls,
                "ast": ast,
                "sh": sh,
                "nineties": round(nineties, 1),
                "pk": pk,
                "pkatt": pkatt,
                "gls_per90": round(p.get("gls_per90", 0), 2),
                "sh_per90": round(p.get("sh_per90", 0), 2) if sh > 0 else 0,
                 "g_sh": round(p.get("g_sh", 0), 3) if sh > 0 else 0,
            })

    # Step F: Sort by (-final_projected_g, -og)
    all_players.sort(key=lambda x: (-x["final_projected_g"], -x["og"]))

    # Assign ranks
    for i, p in enumerate(all_players, 1):
        p["rank"] = i

    return all_players


def run_monte_carlo(data, iterations=1000, noise_range=(0.85, 1.15)):
    """
    Run N Monte Carlo simulations with random team goal adjustments.
    Returns dict: player_key → {median_rank, best_rank, worst_rank, median_score}
    """
    all_ranks = defaultdict(list)  # player_key → [rank1, rank2, ...]
    all_scores = defaultdict(list)

    # Get a deterministic ranking first for comparison
    det_ranking = compute_ranking(data)
    det_rank_map = {f"{p['player']}|{p['team']}": p['rank'] for p in det_ranking}

    teams = list(TEAM_PROJECTIONS.keys())
    rng = random.Random(42)  # seeded for reproducibility

    for _ in range(iterations):
        # Apply random noise to each team's projected goals
        override = {}
        for team in teams:
            _, base_goals = TEAM_PROJECTIONS[team]
            factor = rng.uniform(noise_range[0], noise_range[1])
            override[team] = base_goals * factor

        mc_ranking = compute_ranking(data, team_proj_override=override)
        for p in mc_ranking:
            key = f"{p['player']}|{p['team']}"
            all_ranks[key].append(p['rank'])
            all_scores[key].append(p['final_projected_g'])

    # Compute statistics
    mc_results = []
    for key, ranks in all_ranks.items():
        ranks.sort()
        scores = sorted(all_scores[key])
        n = len(ranks)
        median_rank = ranks[n // 2]
        # Deciles
        p10 = ranks[int(n * 0.1)]
        p90 = ranks[int(n * 0.9) - 1]

        player, team = key.split("|")
        mc_results.append({
            "player": player,
            "team": team,
            "deterministic_rank": det_rank_map.get(key, 9999),
            "median_rank": median_rank,
            "best_rank": ranks[0],
            "worst_rank": ranks[-1],
            "p10_rank": p10,
            "p90_rank": p90,
            "median_score": round(scores[n // 2], 3),
            "p10_score": round(scores[int(n * 0.1)], 3),
            "p90_score": round(scores[int(n * 0.9) - 1], 3),
            "volatility": round(ranks[-1] - ranks[0], 0),
        })

    mc_results.sort(key=lambda x: x["deterministic_rank"])
    return mc_results


def main():
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {sum(len(v) for v in data.values())} players from {len(data)} teams")

    # 1. Deterministic ranking
    print("Computing deterministic ranking...")
    ranking = compute_ranking(data)
    print(f"  → {len(ranking)} players ranked")

    # Print Top 10
    print("\nTop 10:")
    for p in ranking[:10]:
        print(f"  {p['rank']:>4}. {p['player']:<25s} {p['team']:<20s}"
              f"  Score={p['final_projected_g']:>5.3f}  Share={p['team_share']}%"
              f"  PK={p['pk_bonus']:>5.3f}  OG={p['og']}")

    # 2. Monte Carlo simulation
    print("\nRunning Monte Carlo simulation (1000 iterations)...")
    mc_results = run_monte_carlo(data, iterations=1000, noise_range=(0.85, 1.15))
    print(f"  → {len(mc_results)} players with MC stats")
    print(f"  (random factor: 0.85 - 1.15, seeded for reproducibility)")

    # 3. Output
    output = {
        "deterministic": ranking,
        "monte_carlo": mc_results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput saved: {output_path}")
    print(f"Deterministic: {len(ranking)} players")
    print(f"Monte Carlo:   {len(mc_results)} players")

    # MC summary
    volatile = [m for m in mc_results if m["volatility"] >= 100]
    print(f"\nHigh volatility players (rank swing >= 100): {len(volatile)}")
    for m in volatile[:5]:
        print(f"  {m['player']:<25s} {m['team']:<20s}"
              f"  det_rank={m['deterministic_rank']:>4}  range={m['best_rank']:>4}-{m['worst_rank']:>4}")


if __name__ == "__main__":
    main()
