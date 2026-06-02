"""Find and fix any remaining 3-tuples in seed_data.py"""
import re

with open('seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find start of PLAYERS_DATA and end before seed_database
start = content.find("PLAYERS_DATA = {")
end = content.find("\ndef seed_database")
section = content[start:end]

# Find lines that look like 3-element player tuples
# Pattern: ('Name', Number, 'POS'),
# These will have EXACTLY 3 single-quoted groups
lines = section.split('\n')
bad_count = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    # Count single-quoted strings
    count_quotes = stripped.count("'")
    # A 4-tuple has 4 quoted strings -> 8 quotes
    # A 3-tuple has 3 quoted strings -> 6 quotes (but names may have apostrophes)
    # Check if it starts with ( and is a tuple-like line
    if stripped.startswith('(') and stripped.endswith('),') or stripped.endswith('],'):
        # Extract tuple content
        inner = stripped[1:stripped.rindex(')')] if ')' in stripped else ''
        # Split by comma at top level
        parts = re.split(r",\s*(?=(?:[^']*'[^']*')*[^']*$)", inner)
        if len(parts) == 3:
            print(f"LINE {start//1 + i + 1}: {stripped[:100]}")
            bad_count += 1

if bad_count == 0:
    print("No 3-tuples found!")
else:
    print(f"\nTotal bad lines: {bad_count}")
