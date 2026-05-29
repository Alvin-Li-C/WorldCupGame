from models import get_db, init_db

# 48 teams in 12 groups (A-L), 4 per group
# Actual 2026 FIFA World Cup qualified teams
TEAMS = [
    # Group A
    ('Mexico', 'A', '\U0001f1f2\U0001f1fd'),
    ('Czech Republic', 'A', '\U0001f1e8\U0001f1ff'),
    ('South Africa', 'A', '\U0001f1ff\U0001f1e6'),
    ('South Korea', 'A', '\U0001f1f0\U0001f1f7'),
    # Group B
    ('Canada', 'B', '\U0001f1e8\U0001f1e6'),
    ('Bosnia and Herzegovina', 'B', '\U0001f1e7\U0001f1e6'),
    ('Qatar', 'B', '\U0001f1f6\U0001f1e6'),
    ('Switzerland', 'B', '\U0001f1e8\U0001f1ed'),
    # Group C
    ('Brazil', 'C', '\U0001f1e7\U0001f1f7'),
    ('Haiti', 'C', '\U0001f1ed\U0001f1f9'),
    ('Morocco', 'C', '\U0001f1f2\U0001f1e6'),
    ('Scotland', 'C', '\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f'),
    # Group D
    ('United States', 'D', '\U0001f1fa\U0001f1f8'),
    ('Australia', 'D', '\U0001f1e6\U0001f1fa'),
    ('Paraguay', 'D', '\U0001f1f5\U0001f1fe'),
    ('Turkey', 'D', '\U0001f1f9\U0001f1f7'),
    # Group E
    ('Curacao', 'E', '\U0001f1e8\U0001f1fc'),
    ('Ecuador', 'E', '\U0001f1ea\U0001f1e8'),
    ('Germany', 'E', '\U0001f1e9\U0001f1ea'),
    ('Ivory Coast', 'E', '\U0001f1e8\U0001f1ee'),
    # Group F
    ('Netherlands', 'F', '\U0001f1f3\U0001f1f1'),
    ('Japan', 'F', '\U0001f1ef\U0001f1f5'),
    ('Sweden', 'F', '\U0001f1f8\U0001f1ea'),
    ('Tunisia', 'F', '\U0001f1f9\U0001f1f3'),
    # Group G
    ('Belgium', 'G', '\U0001f1e7\U0001f1ea'),
    ('Egypt', 'G', '\U0001f1ea\U0001f1ec'),
    ('Iran', 'G', '\U0001f1ee\U0001f1f7'),
    ('New Zealand', 'G', '\U0001f1f3\U0001f1ff'),
    # Group H
    ('Cape Verde', 'H', '\U0001f1e8\U0001f1fb'),
    ('Saudi Arabia', 'H', '\U0001f1f8\U0001f1e6'),
    ('Spain', 'H', '\U0001f1ea\U0001f1f8'),
    ('Uruguay', 'H', '\U0001f1fa\U0001f1fe'),
    # Group I
    ('France', 'I', '\U0001f1eb\U0001f1f7'),
    ('Norway', 'I', '\U0001f1f3\U0001f1f4'),
    ('Senegal', 'I', '\U0001f1f8\U0001f1f3'),
    ('Iraq', 'I', '\U0001f1ee\U0001f1f6'),
    # Group J
    ('Algeria', 'J', '\U0001f1e9\U0001f1ff'),
    ('Argentina', 'J', '\U0001f1e6\U0001f1f7'),
    ('Austria', 'J', '\U0001f1e6\U0001f1f9'),
    ('Jordan', 'J', '\U0001f1ef\U0001f1f4'),
    # Group K
    ('Colombia', 'K', '\U0001f1e8\U0001f1f4'),
    ('Jamaica', 'K', '\U0001f1ef\U0001f1f2'),
    ('Portugal', 'K', '\U0001f1f5\U0001f1f9'),
    ('Uzbekistan', 'K', '\U0001f1fa\U0001f1ff'),
    # Group L
    ('Croatia', 'L', '\U0001f1ed\U0001f1f7'),
    ('England', 'L', '\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f'),
    ('Ghana', 'L', '\U0001f1ec\U0001f1ed'),
    ('Panama', 'L', '\U0001f1f5\U0001f1e6'),
]

SURNAMES = [
    '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
    '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗',
    '郑', '梁', '谢', '宋', '唐', '韩', '曹', '许', '邓', '冯',
    '曾', '程', '蔡', '彭', '潘', '袁', '董', '余', '苏', '叶',
    '蒋', '田', '杜', '丁', '沈', '任', '姚', '范', '方', '崔',
]

GIVEN_NAMES = [
    '伟', '强', '磊', '军', '洋', '勇', '杰', '涛', '明', '超',
    '华', '飞', '斌', '海', '鑫', '鹏', '宇', '峰', '辉', '浩',
    '晨', '博', '毅', '轩', '健', '龙', '文', '志远', '建华', '建国',
    '建平', '志强', '志豪', '伟强', '晓明', '晓东', '志明', '永强',
    '国华', '国庆', '嘉豪', '嘉诚', '俊杰', '家辉', '家豪', '家伟',
    '朝晖', '国栋', '文浩', '天宇', '宇航', '子豪', '子轩', '浩然',
]


def seed_database():
    init_db()
    db = get_db()
    cur = db.cursor()

    # Insert teams
    team_ids = {}
    for i, (name, group, flag) in enumerate(TEAMS, 1):
        cur.execute(
            'INSERT INTO teams (name, group_name, flag_emoji) VALUES (?, ?, ?)',
            (name, group, flag)
        )
        team_ids[i] = cur.lastrowid

    # Insert players: 23 non-GK per team
    import random
    random.seed(42)
    used_surnames = list(SURNAMES)
    used_given = list(GIVEN_NAMES)

    player_count = 0
    for team_idx in range(1, 49):
        team_id = team_ids[team_idx]
        for pnum in range(1, 24):  # 23 non-GK players per team
            # Determine position based on player number
            if pnum <= 7:
                position = 'FW'
            elif pnum <= 15:
                position = 'MF'
            else:
                position = 'DF'

            # Generate Chinese name: Surname + Given Name
            surname = random.choice(used_surnames)
            given = random.choice(used_given)
            name = surname + given

            cur.execute(
                'INSERT INTO players (name, jersey_number, team_id, position) VALUES (?, ?, ?, ?)',
                (name, pnum, team_id, position)
            )
            player_count += 1

    # Insert participants
    participants = [
        ('庆爷', 1),
        ('耗子', 2),
        ('老王', 3),
        ('李总', 4),
        ('老闫', 5),
    ]
    for name, order in participants:
        cur.execute(
            'INSERT INTO participants (name, draft_order) VALUES (?, ?)',
            (name, order)
        )

    db.commit()
    db.close()
    print(f'Seeded: {len(TEAMS)} teams, {player_count} players, {len(participants)} participants')


if __name__ == '__main__':
    seed_database()
