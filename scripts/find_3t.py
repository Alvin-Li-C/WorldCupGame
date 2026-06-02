"""Find any 3-tuple entries in PLAYERS_DATA"""
import re

with open('d:\\AI\\WorldCupGame\\seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Use eval-style approach
# Find PLAYERS_DATA definition
start = content.find("PLAYERS_DATA = {")
end = content.find("\ndef seed_database")
section = content[start:end]

# Scan for pattern: ('Name', Number, 'POS'), where Number is unquoted
# This is a 3-tuple pattern (missing name_cn)
pattern = re.compile(r"\(\s*'[^']*'\s*,\s*\d+\s*,\s*'[A-Z]+'\s*\)")
matches = pattern.findall(section)
for m in matches:
    print(f"3-tuple found: {m}")

if not matches:
    print("No 3-tuples found!")
