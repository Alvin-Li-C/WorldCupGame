from models import get_db

TOTAL_ROUNDS = 15
PICKS_PER_ROUND = 5
TOTAL_PARTICIPANTS = 5


def get_snake_order(round_number):
    """Return participant draft_order list for a given round.
    Odd rounds: forward [1,2,3,4,5], Even rounds: reverse [5,4,3,2,1]
    """
    if round_number % 2 == 1:
        return [1, 2, 3, 4, 5]
    else:
        return [5, 4, 3, 2, 1]


def get_participant_id_by_draft_order(order):
    db = get_db()
    row = db.execute(
        'SELECT id FROM participants WHERE draft_order = ?', (order,)
    ).fetchone()
    db.close()
    return row['id'] if row else None


def get_current_state():
    db = get_db()
    round_val = int(db.execute(
        'SELECT state_value FROM game_state WHERE state_key = "current_round"'
    ).fetchone()['state_value'])
    pick_val = int(db.execute(
        'SELECT state_value FROM game_state WHERE state_key = "current_pick"'
    ).fetchone()['state_value'])
    status = db.execute(
        'SELECT state_value FROM game_state WHERE state_key = "status"'
    ).fetchone()['state_value']

    # Current participant
    order = get_snake_order(round_val)
    current_order = order[pick_val - 1]
    participant = db.execute(
        'SELECT id, name, draft_order FROM participants WHERE draft_order = ?',
        (current_order,)
    ).fetchone()

    # All selections
    selections = db.execute('''
        SELECT s.id, s.round_number, s.pick_number,
               p.name AS participant_name, pl.name AS player_name,
               pl.jersey_number, t.name AS team_name, t.flag_emoji,
               s.created_at
        FROM selections s
        JOIN participants p ON s.participant_id = p.id
        JOIN players pl ON s.player_id = pl.id
        JOIN teams t ON pl.team_id = t.id
        ORDER BY s.id
    ''').fetchall()

    # Total players count
    total_players = db.execute('SELECT COUNT(*) AS cnt FROM players').fetchone()['cnt']
    selected_count = len(selections)

    # Participant details
    participants = db.execute(
        'SELECT id, name, draft_order FROM participants ORDER BY draft_order'
    ).fetchall()

    db.close()
    return {
        'current_round': round_val,
        'current_pick': pick_val,
        'status': status,
        'current_participant': {
            'id': participant['id'],
            'name': participant['name'],
            'draft_order': participant['draft_order'],
        } if participant else None,
        'selections': [dict(s) for s in selections],
        'total_players': total_players,
        'selected_count': selected_count,
        'participants': [dict(p) for p in participants],
    }


def validate_selection(participant_name, player_id):
    db = get_db()

    # 1. Check game not over
    state = get_current_state()
    if state['status'] == 'completed':
        db.close()
        return {'valid': False, 'error': '游戏已结束'}

    # 2. Check participant exists
    participant = db.execute(
        'SELECT id, draft_order FROM participants WHERE name = ?',
        (participant_name,)
    ).fetchone()
    if not participant:
        db.close()
        return {'valid': False, 'error': '参与者不存在'}

    # 3. Check it's this participant's turn
    order_list = get_snake_order(state['current_round'])
    expected_order = order_list[state['current_pick'] - 1]
    if participant['draft_order'] != expected_order:
        db.close()
        return {'valid': False, 'error': '还未轮到该参与者'}

    # 4. Check player exists
    player = db.execute(
        'SELECT id FROM players WHERE id = ?', (player_id,)
    ).fetchone()
    if not player:
        db.close()
        return {'valid': False, 'error': '球员不存在'}

    # 5. Check player not already selected
    taken = db.execute(
        'SELECT id FROM selections WHERE player_id = ?', (player_id,)
    ).fetchone()
    if taken:
        db.close()
        return {'valid': False, 'error': '该球员已被选择'}

    db.close()
    return {'valid': True}


def record_selection(participant_name, player_id):
    db = get_db()
    state = get_current_state()

    participant = db.execute(
        'SELECT id FROM participants WHERE name = ?',
        (participant_name,)
    ).fetchone()

    # Insert selection
    db.execute(
        '''INSERT INTO selections (round_number, pick_number, participant_id, player_id)
           VALUES (?, ?, ?, ?)''',
        (state['current_round'], state['current_pick'],
         participant['id'], player_id)
    )

    # Advance pick
    next_pick = state['current_pick'] + 1
    next_round = state['current_round']

    if next_pick > PICKS_PER_ROUND:
        next_pick = 1
        next_round += 1

    if next_round > TOTAL_ROUNDS:
        db.execute(
            'UPDATE game_state SET state_value = "completed" WHERE state_key = "status"'
        )
    else:
        db.execute(
            'UPDATE game_state SET state_value = ? WHERE state_key = "current_round"',
            (str(next_round),)
        )
        db.execute(
            'UPDATE game_state SET state_value = ? WHERE state_key = "current_pick"',
            (str(next_pick),)
        )

    db.execute(
        'UPDATE game_state SET state_value = ? WHERE state_key = "last_participant_id"',
        (str(participant['id']),)
    )

    db.commit()
    db.close()


def reset_game():
    from models import init_db
    init_db()


def is_game_over():
    db = get_db()
    status = db.execute(
        'SELECT state_value FROM game_state WHERE state_key = "status"'
    ).fetchone()['state_value']
    db.close()
    return status == 'completed'
