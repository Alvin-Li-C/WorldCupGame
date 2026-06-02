"""Check which fields have real data"""
import json

d = json.load(open(r'd:\AI\WorldCupGame\data\wcq_player_stats.json', 'r', encoding='utf-8'))

# Pick a known top scorer - Messi (Argentina)
messi = None
for p in d['阿根廷']:
    if 'Messi' in p['player']:
        messi = p
        break

print("=== Messi's full data record ===")
for k, v in messi.items():
    print(f"  {k:15s} = {v}")

print("\n=== Field coverage (non-zero count across all 346 players) ===")
all_players = [p for team in d.values() for p in team]
fields = list(all_players[0].keys())
for f in fields:
    nonzero = sum(1 for p in all_players if p.get(f, 0) != 0)
    print(f"  {f:15s}: {nonzero:3d} / {len(all_players)} players have non-zero values")
