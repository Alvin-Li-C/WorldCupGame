import os
import io
import json
import hashlib
from flask import Flask, render_template, jsonify, request, send_file
from models import get_db, init_db
from game_logic import (
    get_current_state, validate_selection, record_selection, reset_game,
    is_game_over, get_snake_order,
    init_pin_for_participant, verify_pin_for_participant,
    get_queue_for_participant, save_queue_for_participant,
    toggle_auto_draft_for_participant, get_auto_draft_state_for_participant,
    _execute_auto_draft
)
from seed_data import seed_database
import openpyxl

app = Flask(__name__)


def get_teams_with_players():
    db = get_db()
    teams = db.execute('''
        SELECT t.id, t.name, t.group_name, t.flag_emoji
        FROM teams t ORDER BY t.group_name, t.id
    ''').fetchall()

    # Get selected player IDs
    selected_ids = set(
        r['player_id'] for r in db.execute('SELECT player_id FROM selections').fetchall()
    )

    result = []
    for t in teams:
        players = db.execute(
            'SELECT id, name, name_cn, jersey_number, position FROM players WHERE team_id = ? ORDER BY jersey_number',
            (t['id'],)
        ).fetchall()
        result.append({
            'id': t['id'],
            'name': t['name'],
            'group_name': t['group_name'],
            'flag_emoji': t['flag_emoji'],
            'players': [{
                'id': p['id'],
                'name': p['name'],
                'name_cn': p['name_cn'] or p['name'],
                'jersey_number': p['jersey_number'],
                'position': p['position'],
                'selected': p['id'] in selected_ids,
            } for p in players],
        })
    db.close()
    return result


# ========== Routes ==========

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/stats')
def stats():
    import os
    stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'wcq_player_stats_table.html')
    return send_file(stats_path)


@app.route('/teams')
def teams():
    import os
    teams_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'team_ranking_top500.html')
    return send_file(teams_path)


@app.route('/api/state')
def api_state():
    state = get_current_state()
    return jsonify(state)


@app.route('/api/teams')
def api_teams():
    return jsonify(get_teams_with_players())


@app.route('/api/players')
def api_players():
    return jsonify(get_teams_with_players())


@app.route('/api/select', methods=['POST'])
def api_select():
    data = request.get_json(force=True)
    participant_name = data.get('participant_name')
    player_id = data.get('player_id')
    pin = data.get('pin', '')

    if not participant_name or not player_id:
        return jsonify({'success': False, 'error': '\u7f3a\u5c11\u53c2\u6570'}), 400

    # Verify PIN before allowing selection
    if not verify_pin_for_participant(participant_name, pin):
        return jsonify({'success': False, 'error': 'PIN\u9a8c\u8bc1\u5931\u8d25'}), 403

    validation = validate_selection(participant_name, player_id)
    if not validation['valid']:
        return jsonify({'success': False, 'error': validation['error']}), 400

    auto_picks = record_selection(participant_name, player_id)
    return jsonify({'success': True, 'auto_picks': auto_picks, 'state': get_current_state()})


@app.route('/api/selections')
def api_selections():
    state = get_current_state()
    return jsonify(state['selections'])


@app.route('/api/export')
def api_export():
    db = get_db()
    # Build grid: rows = rounds, cols = participants
    participants = db.execute(
        'SELECT id, name, draft_order FROM participants ORDER BY draft_order'
    ).fetchall()

    selections = db.execute('''
        SELECT s.round_number, s.pick_number,
               p.name AS participant_name, pl.name AS player_name,
               pl.jersey_number, t.name AS team_name
        FROM selections s
        JOIN participants p ON s.participant_id = p.id
        JOIN players pl ON s.player_id = pl.id
        JOIN teams t ON pl.team_id = t.id
        ORDER BY s.round_number, s.pick_number
    ''').fetchall()

    # Build round × participant grid
    grid = {}
    for s in selections:
        r = s['round_number']
        order = None
        for p in participants:
            if p['name'] == s['participant_name']:
                order = p['draft_order']
                break
        if order:
            # figure out column based on snake rule
            snake = get_snake_order(r)
            col = snake.index(order) + 2  # col 0=round, col 6=6th participant (none)
            if r not in grid:
                grid[r] = {}
            grid[r][col] = f"{s['player_name']} #{s['jersey_number']} ({s['team_name']})"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '选秀结果'

    # Header
    ws.cell(1, 1, '轮次')
    for i, p in enumerate(participants):
        ws.cell(1, i + 2, p['name'])

    # Data
    for r in range(1, 16):
        ws.cell(r + 1, 1, r)
        for cp in range(2, 7):
            if r in grid and cp in grid[r]:
                ws.cell(r + 1, cp, grid[r][cp])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    db.close()
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='选秀结果.xlsx')


@app.route('/api/reset', methods=['POST'])
def api_reset():
    seed_database()
    return jsonify({'success': True})


@app.route('/api/preselect/init-pin', methods=['POST'])
def api_init_pin():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'success': False, 'error': '无法解析JSON: ' + str(request.data)[:200]}), 400
    name = data.get('participant_name')
    pin = data.get('pin')
    if not name or not pin:
        return jsonify({'success': False, 'error': '缺少参数: name=' + repr(name) + ' pin=' + repr(pin)}), 400
    if init_pin_for_participant(name, pin):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'PIN已存在'}), 400


@app.route('/api/preselect/verify-pin', methods=['POST'])
def api_verify_pin():
    data = request.get_json()
    name = data.get('participant_name')
    pin = data.get('pin')
    if not name or not pin:
        return jsonify({'success': False, 'error': '缺少参数'}), 400
    return jsonify({'success': verify_pin_for_participant(name, pin)})


@app.route('/api/preselect/<name>')
def api_get_preselect(name):
    pin = request.args.get('pin', '')
    db = get_db()
    row = db.execute(
        'SELECT pin_hash, queue_data FROM preselect_queues WHERE participant_name = ?',
        (name,)
    ).fetchone()

    if not row:
        db.close()
        return jsonify({'queue': [], 'has_pin': False})

    if not pin:
        db.close()
        # Only report has_pin if hash is actually set (not just row exists from auto-draft)
        has_pin = bool(row['pin_hash'])
        return jsonify({'queue': [], 'has_pin': has_pin})

    # Verify PIN
    if hashlib.sha256(pin.encode()).hexdigest() != row['pin_hash']:
        db.close()
        return jsonify({'queue': [], 'has_pin': True, 'pin_ok': False}), 403

    # Return queue filtered by already-selected
    selected_ids = set(
        r['player_id'] for r in db.execute('SELECT player_id FROM selections').fetchall()
    )
    db.close()
    queue = json.loads(row['queue_data'])
    filtered = [pid for pid in queue if pid not in selected_ids]
    return jsonify({'queue': filtered, 'has_pin': True, 'pin_ok': True})


@app.route('/api/preselect/<name>', methods=['POST'])
def api_save_preselect(name):
    data = request.get_json(force=True)
    pin = data.get('pin', '')
    queue = data.get('queue', [])
    if save_queue_for_participant(name, pin, queue):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'PIN错误'}), 403


@app.route('/api/auto-draft/toggle', methods=['POST'])
def api_toggle_auto_draft():
    data = request.get_json(force=True)
    name = data.get('participant_name')
    enabled = data.get('enabled', False)
    if not name:
        return jsonify({'success': False, 'error': '缺少参数'}), 400
    toggle_auto_draft_for_participant(name, enabled)
    # On enabling, immediately check if it's this participant's turn
    auto_picks = []
    if enabled:
        db = get_db()
        auto_picks = _execute_auto_draft(db)
        db.commit()
        db.close()
    return jsonify({'success': True, 'auto_picks': auto_picks})


@app.route('/api/auto-draft/state/<name>')
def api_auto_draft_state(name):
    return jsonify({'enabled': get_auto_draft_state_for_participant(name)})


# ========== Init ==========

def ensure_db_initialized():
    """Initialize and seed DB on first run, re-seed if name_cn is missing"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'draft.db')
    if not os.path.exists(db_path):
        seed_database()
        return
    # Check if any players have empty name_cn, re-seed if so
    db = get_db()
    empty_count = db.execute('SELECT COUNT(*) FROM players WHERE name_cn = ""').fetchone()[0]
    db.close()
    if empty_count > 0:
        seed_database()


ensure_db_initialized()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
