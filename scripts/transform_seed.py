"""Transform seed_data.py to support name_cn field.
Changes: (name, jersey, pos) -> (name, name_cn, jersey, pos)
And updates seed_database() to insert name_cn.
"""
import re

with open('d:\\AI\\WorldCupGame\\seed_data.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Transform player tuples: ('Name', Number, 'POS') -> ('Name', '', Number, 'POS')
# Pattern matches tuples with 3 elements: string, number, quoted-string
player_tuple_pattern = re.compile(r"\('[^']*',\s*\d+,\s*'[^']*'\)")

def transform_tuple(m):
    t = m.group(0)
    # Extract the name (first string), number, and position
    # e.g. ('Carlos Acevedo', 1, 'GK')
    inner = t[1:-1]  # remove parens
    parts = re.split(r',\s*', inner, maxsplit=2)
    name = parts[0]
    num = parts[1]
    pos = parts[2]
    return f"({name}, '', {num}, {pos})"

content = player_tuple_pattern.sub(transform_tuple, content)

# Update seed_database() to include name_cn in INSERT
content = content.replace(
    "name, jersey_number, position = p",
    "name, name_cn, jersey_number, position = p"
)
content = content.replace(
    "cur.execute('INSERT INTO players (name, jersey_number, team_id, position) VALUES (?, ?, ?, ?)', (name, jersey_number, team_id, position))",
    "cur.execute('INSERT INTO players (name, name_cn, jersey_number, team_id, position) VALUES (?, ?, ?, ?, ?)', (name, name_cn, jersey_number, team_id, position))"
)

with open('d:\\AI\\WorldCupGame\\seed_data.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Transform complete!")
print(f"Total file size: {len(content)} chars")
