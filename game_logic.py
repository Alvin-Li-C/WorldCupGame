from models import get_db
import json
import hashlib

TOTAL_ROUNDS = 250
PICKS_PER_ROUND = 5
TOTAL_PARTICIPANTS = 5
TOP20_CUTOFF = 20


def global_pick_number(round_number, pick_number):
    """Overall draft slot (1-based) across all rounds."""
    return (round_number - 1) * PICKS_PER_ROUND + pick_number


def is_top20_pick(round_number, pick_number):
    """True if this selection was made in the first 20 overall draft picks."""
    return global_pick_number(round_number, pick_number) <= TOP20_CUTOFF


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
               pl.name_cn AS player_name_cn,
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
        'total_rounds': TOTAL_ROUNDS,
        'picks_per_round': PICKS_PER_ROUND,
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
        # Check if all players have been selected
        total_players = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        selected_count = db.execute('SELECT COUNT(*) FROM selections').fetchone()[0]
        if selected_count >= total_players:
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

    # ===== SERVER-SIDE AUTO-DRAFT CASCADE =====
    auto_picks = _execute_auto_draft(db)

    db.commit()
    db.close()
    return auto_picks


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


# ========== Preselect Queue & Auto-Draft Helpers ==========

def init_pin_for_participant(participant_name, pin):
    """Set initial PIN for a participant. Returns True on success."""
    db = get_db()
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    existing = db.execute(
        'SELECT participant_name FROM preselect_queues WHERE participant_name = ?',
        (participant_name,)
    ).fetchone()
    if existing:
        # Row exists (e.g. auto-draft created it without PIN), update it
        db.execute(
            'UPDATE preselect_queues SET pin_hash = ? WHERE participant_name = ?',
            (pin_hash, participant_name)
        )
    else:
        db.execute(
            'INSERT INTO preselect_queues (participant_name, pin_hash) VALUES (?, ?)',
            (participant_name, pin_hash)
        )
    db.commit()
    db.close()
    return True


def verify_pin_for_participant(participant_name, pin):
    db = get_db()
    row = db.execute(
        'SELECT pin_hash FROM preselect_queues WHERE participant_name = ?',
        (participant_name,)
    ).fetchone()
    db.close()
    if not row:
        return False
    return hashlib.sha256(pin.encode()).hexdigest() == row['pin_hash']


def has_pin_set(participant_name):
    db = get_db()
    row = db.execute(
        'SELECT participant_name FROM preselect_queues WHERE participant_name = ?',
        (participant_name,)
    ).fetchone()
    db.close()
    return row is not None


def get_queue_for_participant(participant_name, pin):
    """Returns (queue_list, has_pin_set). Raises ValueError on wrong PIN."""
    db = get_db()
    row = db.execute(
        'SELECT pin_hash, queue_data FROM preselect_queues WHERE participant_name = ?',
        (participant_name,)
    ).fetchone()
    db.close()
    if not row:
        return [], False

    if hashlib.sha256(pin.encode()).hexdigest() != row['pin_hash']:
        raise ValueError('PIN错误')

    return json.loads(row['queue_data']), True


def save_queue_for_participant(participant_name, pin, queue):
    db = get_db()
    row = db.execute(
        'SELECT pin_hash FROM preselect_queues WHERE participant_name = ?',
        (participant_name,)
    ).fetchone()
    if not row:
        db.close()
        return False
    if hashlib.sha256(pin.encode()).hexdigest() != row['pin_hash']:
        db.close()
        return False
    db.execute(
        'UPDATE preselect_queues SET queue_data = ?, updated_at = datetime(\'now\') WHERE participant_name = ?',
        (json.dumps(queue), participant_name)
    )
    db.commit()
    db.close()
    return True


def toggle_auto_draft_for_participant(participant_name, enabled):
    db = get_db()
    db.execute(
        '''INSERT INTO preselect_queues (participant_name, pin_hash, queue_data, auto_draft, updated_at)
           VALUES (?, '', '[]', ?, datetime('now'))
           ON CONFLICT(participant_name) DO UPDATE SET auto_draft = ?, updated_at = datetime('now')''',
        (participant_name, 1 if enabled else 0, 1 if enabled else 0)
    )
    db.commit()
    db.close()


def get_auto_draft_state_for_participant(participant_name):
    db = get_db()
    row = db.execute(
        'SELECT auto_draft FROM preselect_queues WHERE participant_name = ?',
        (participant_name,)
    ).fetchone()
    db.close()
    return row['auto_draft'] == 1 if row else False


def _execute_auto_draft(db):
    """
    Server-side auto-draft cascade.
    After a pick is made, check if the next participant(s) have auto-draft enabled.
    If so, auto-pick from their queue.
    Must be called with an open db connection (before commit).
    """
    picks = []

    for _ in range(1250):  # Safety limit - cover all possible picks
        # Check game not over
        status_row = db.execute(
            'SELECT state_value FROM game_state WHERE state_key = "status"'
        ).fetchone()
        if status_row['state_value'] == 'completed':
            break

        # Get current round/pick
        round_row = db.execute(
            'SELECT state_value FROM game_state WHERE state_key = "current_round"'
        ).fetchone()
        pick_row = db.execute(
            'SELECT state_value FROM game_state WHERE state_key = "current_pick"'
        ).fetchone()
        cur_round = int(round_row['state_value'])
        cur_pick = int(pick_row['state_value'])

        # Get current participant
        order_list = get_snake_order(cur_round)
        current_order = order_list[cur_pick - 1]
        participant = db.execute(
            'SELECT id, name FROM participants WHERE draft_order = ?',
            (current_order,)
        ).fetchone()

        if not participant:
            break

        # Check if participant has auto-draft ON and has set a PIN
        pq = db.execute(
            'SELECT auto_draft, queue_data, pin_hash FROM preselect_queues WHERE participant_name = ?',
            (participant['name'],)
        ).fetchone()

        if not pq or pq['auto_draft'] != 1 or pq['pin_hash'] == '':
            break  # No auto-draft or no PIN set (no preselect without PIN)

        # Get queue, filter already-selected
        queue = json.loads(pq['queue_data'])
        selected_ids = set(
            r[0] for r in db.execute('SELECT player_id FROM selections').fetchall()
        )

        auto_player_id = None
        for pid in queue:
            if pid not in selected_ids:
                auto_player_id = pid
                break

        if auto_player_id is None:
            break  # Queue empty

        # Record auto-pick
        db.execute(
            '''INSERT INTO selections (round_number, pick_number, participant_id, player_id)
               VALUES (?, ?, ?, ?)''',
            (cur_round, cur_pick, participant['id'], auto_player_id)
        )
        picks.append({
            'participant': participant['name'],
            'player_id': auto_player_id,
            'round': cur_round,
            'pick': cur_pick,
        })

        # Advance pick
        next_pick = cur_pick + 1
        next_round = cur_round
        if next_pick > PICKS_PER_ROUND:
            next_pick = 1
            next_round += 1

        if next_round > TOTAL_ROUNDS:
            db.execute(
                'UPDATE game_state SET state_value = "completed" WHERE state_key = "status"'
            )
            break
        else:
            # Check if all players have been selected
            total_players = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
            selected_count = db.execute('SELECT COUNT(*) FROM selections').fetchone()[0]
            if selected_count >= total_players:
                db.execute(
                    'UPDATE game_state SET state_value = "completed" WHERE state_key = "status"'
                )
                break
            else:
                db.execute(
                    'UPDATE game_state SET state_value = ? WHERE state_key = "current_round"',
                    (str(next_round),)
                )
                db.execute(
                    'UPDATE game_state SET state_value = ? WHERE state_key = "current_pick"',
                    (str(next_pick),)
                )

    return picks
