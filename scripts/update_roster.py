"""
Reusable roster update script.
Replaces injured (unselected) players in the live database.
Usage: Edit the CHANGES list below and run the script.

Each change: (team_name, old_player_english_name, new_name, new_name_cn, new_jersey, new_position)
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'draft.db')

# === EDIT THIS LIST FOR EACH ROSTER UPDATE ===
CHANGES = [
    # (球队, 受伤球员英文名, 新球员英文名, 新球员中文名, 新号码, 位置)
    ('德国', 'Lennart Karl', 'Assan Ouedraogo', '阿桑·韦德拉奥果', 21, 'MF'),
    ('德国', 'Robin Gosens', 'Nadiem Amiri', '纳迪姆·阿米里', 20, 'MF'),
]


def update_roster(changes):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    results = []
    for team_name, old_name, new_name, new_name_cn, new_jersey, new_position in changes:
        # Find the player
        row = cur.execute('''
            SELECT p.id, p.name, p.name_cn, p.jersey_number, p.position,
                   s.id AS selection_id
            FROM players p
            JOIN teams t ON p.team_id = t.id
            LEFT JOIN selections s ON s.player_id = p.id
            WHERE t.name = ? AND p.name = ?
        ''', (team_name, old_name)).fetchone()

        if not row:
            results.append(f"[SKIP] {team_name}/{old_name}: player not found in DB")
            continue

        if row['selection_id'] is not None:
            results.append(f"[SKIP] {team_name}/{old_name}: ALREADY SELECTED (selection #{row['selection_id']})")
            continue

        # Update in-place (same id, new info)
        cur.execute('''
            UPDATE players SET name = ?, name_cn = ?, jersey_number = ?, position = ?
            WHERE id = ?
        ''', (new_name, new_name_cn, new_jersey, new_position, row['id']))

        results.append(
            f"[OK] {team_name}: {old_name} (#{row['jersey_number']} {row['position']}) "
            f"-> {new_name} (#{new_jersey} {new_position}) [id={row['id']}]"
        )

    conn.commit()
    conn.close()

    print("=== Roster Update Results ===")
    for r in results:
        print(r)
    print(f"\nTotal changes: {sum(1 for r in results if r.startswith('[OK]'))}/{len(changes)}")
    return results


if __name__ == '__main__':
    update_roster(CHANGES)
