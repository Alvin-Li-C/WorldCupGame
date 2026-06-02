"""Check which teams still have empty Chinese names in seed_data.py"""
import re

with open('d:\\AI\\WorldCupGame\\seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.index('PLAYERS_DATA = {')
current_team = None
total_empty = 0
teams_with_empty = {}

for line_num, line in enumerate(content[start:].split('\n')):
    team_match = re.match(r"\s+'([^']+)': \[", line)
    if team_match:
        current_team = team_match.group(1)
        continue
    if current_team and "', '', " in line:
        name_match = re.search(r"'([^']*)', '', ", line)
        if name_match:
            en_name = name_match.group(1)
            if en_name:
                total_empty += 1
                if current_team not in teams_with_empty:
                    teams_with_empty[current_team] = []
                teams_with_empty[current_team].append(en_name)

print(f"Teams with empty Chinese names: {len(teams_with_empty)}")
for team, players in sorted(teams_with_empty.items()):
    total = len(players)
    print(f"\n  {team} ({total} empty):")
    for p in players:
        print(f"    {p}")

if total_empty == 0:
    print("\n✓ All players have Chinese names!")
else:
    print(f"\nTotal empty name_cn entries: {total_empty}")
