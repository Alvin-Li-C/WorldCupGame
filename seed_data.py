from models import get_db, init_db

# 48 teams in 12 groups (A-L), 4 per group
# Actual 2026 FIFA World Cup qualified teams
TEAMS = [
    # Group A
    ('墨西哥', 'A', '\U0001f1f2\U0001f1fd'),
    ('捷克', 'A', '\U0001f1e8\U0001f1ff'),
    ('南非', 'A', '\U0001f1ff\U0001f1e6'),
    ('韩国', 'A', '\U0001f1f0\U0001f1f7'),
    # Group B
    ('加拿大', 'B', '\U0001f1e8\U0001f1e6'),
    ('波黑', 'B', '\U0001f1e7\U0001f1e6'),
    ('卡塔尔', 'B', '\U0001f1f6\U0001f1e6'),
    ('瑞士', 'B', '\U0001f1e8\U0001f1ed'),
    # Group C
    ('巴西', 'C', '\U0001f1e7\U0001f1f7'),
    ('海地', 'C', '\U0001f1ed\U0001f1f9'),
    ('摩洛哥', 'C', '\U0001f1f2\U0001f1e6'),
    ('苏格兰', 'C', '\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f'),
    # Group D
    ('美国', 'D', '\U0001f1fa\U0001f1f8'),
    ('澳大利亚', 'D', '\U0001f1e6\U0001f1fa'),
    ('巴拉圭', 'D', '\U0001f1f5\U0001f1fe'),
    ('土耳其', 'D', '\U0001f1f9\U0001f1f7'),
    # Group E
    ('库拉索', 'E', '\U0001f1e8\U0001f1fc'),
    ('厄瓜多尔', 'E', '\U0001f1ea\U0001f1e8'),
    ('德国', 'E', '\U0001f1e9\U0001f1ea'),
    ('科特迪瓦', 'E', '\U0001f1e8\U0001f1ee'),
    # Group F
    ('荷兰', 'F', '\U0001f1f3\U0001f1f1'),
    ('日本', 'F', '\U0001f1ef\U0001f1f5'),
    ('瑞典', 'F', '\U0001f1f8\U0001f1ea'),
    ('突尼斯', 'F', '\U0001f1f9\U0001f1f3'),
    # Group G
    ('比利时', 'G', '\U0001f1e7\U0001f1ea'),
    ('埃及', 'G', '\U0001f1ea\U0001f1ec'),
    ('伊朗', 'G', '\U0001f1ee\U0001f1f7'),
    ('新西兰', 'G', '\U0001f1f3\U0001f1ff'),
    # Group H
    ('佛得角', 'H', '\U0001f1e8\U0001f1fb'),
    ('沙特', 'H', '\U0001f1f8\U0001f1e6'),
    ('西班牙', 'H', '\U0001f1ea\U0001f1f8'),
    ('乌拉圭', 'H', '\U0001f1fa\U0001f1fe'),
    # Group I
    ('法国', 'I', '\U0001f1eb\U0001f1f7'),
    ('挪威', 'I', '\U0001f1f3\U0001f1f4'),
    ('塞内加尔', 'I', '\U0001f1f8\U0001f1f3'),
    ('伊拉克', 'I', '\U0001f1ee\U0001f1f6'),
    # Group J
    ('阿尔及利亚', 'J', '\U0001f1e9\U0001f1ff'),
    ('阿根廷', 'J', '\U0001f1e6\U0001f1f7'),
    ('奥地利', 'J', '\U0001f1e6\U0001f1f9'),
    ('约旦', 'J', '\U0001f1ef\U0001f1f4'),
    # Group K
    ('哥伦比亚', 'K', '\U0001f1e8\U0001f1f4'),
    ('牙买加', 'K', '\U0001f1ef\U0001f1f2'),
    ('葡萄牙', 'K', '\U0001f1f5\U0001f1f9'),
    ('乌兹别克斯坦', 'K', '\U0001f1fa\U0001f1ff'),
    # Group L
    ('克罗地亚', 'L', '\U0001f1ed\U0001f1f7'),
    ('英格兰', 'L', '\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f'),
    ('加纳', 'L', '\U0001f1ec\U0001f1ed'),
    ('巴拿马', 'L', '\U0001f1f5\U0001f1e6'),
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
