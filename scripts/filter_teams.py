"""Filter to only 48 qualified teams and regenerate HTML"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
json_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
filtered_json_path = os.path.join(DATA_DIR, "wcq_player_stats.json")  # overwrite

# 48 qualified teams (using the slug format from our scrape)
QUALIFIED_TEAMS = {
    # AFC 9
    "Japan", "IR-Iran", "Korea-Republic", "Australia", "Uzbekistan",
    "Jordan", "Qatar", "Saudi-Arabia", "Iraq",
    # CAF 10
    "Morocco", "Senegal", "Egypt", "Tunisia", "Algeria",
    "South-Africa", "Cote-dIvoire", "Ghana", "Cape-Verde", "Congo-DR",
    # CONCACAF 6
    "United-States", "Mexico", "Canada", "Panama", "Haiti", "Curacao",
    # CONMEBOL 6
    "Argentina", "Brazil", "Colombia", "Ecuador", "Uruguay", "Paraguay",
    # OFC 1
    "New-Zealand",
    # UEFA 16
    "France", "Spain", "England", "Portugal", "Germany", "Netherlands",
    "Belgium", "Croatia", "Switzerland", "Austria", "Scotland",
    "Norway", "Sweden", "Turkiye", "Czechia", "Bosnia-and-Herzegovina",
}

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter
removed = [k for k in data if k not in QUALIFIED_TEAMS]
filtered = {k: v for k, v in data.items() if k in QUALIFIED_TEAMS}

print(f"Original: {len(data)} teams, {sum(len(v) for v in data.values())} players")
print(f"Removed: {removed}")
print(f"Filtered: {len(filtered)} teams, {sum(len(v) for v in filtered.values())} players")

# Overwrite JSON
with open(filtered_json_path, "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"\nSaved: {filtered_json_path}")
