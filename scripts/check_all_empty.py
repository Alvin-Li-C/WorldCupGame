"""Check ALL teams for empty Chinese names, output to file"""
import re, sys

with open('d:\\AI\\WorldCupGame\\seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.index('PLAYERS_DATA = {')
lines = content[start:].split('\n')

current_team = None
empty_by_team = {}

for line in lines:
    team_match = re.match(r"\s+'([^']+)': \[", line)
    if team_match:
        current_team = team_match.group(1)
        continue
    if current_team and "', '', " in line:
        if current_team not in empty_by_team:
            empty_by_team[current_team] = []
        name_match = re.search(r"'([^']*)', '', ", line)
        if name_match:
            empty_by_team[current_team].append(name_match.group(1))

with open('d:\\AI\\WorldCupGame\\empty_check_result.txt', 'w', encoding='utf-8') as out:
    if not empty_by_team:
        out.write("✓ ALL teams have Chinese names!\n")
    else:
        total = 0
        for team in sorted(empty_by_team.keys()):
            count = len(empty_by_team[team])
            out.write(f"{team}: {count} empty\n")
            total += count
        out.write(f"\nTotal empty name_cn: {total}\n")
        out.write(f"Teams with empty names: {len(empty_by_team)}\n")
