import os
import io
from flask import Flask, render_template, jsonify, request, send_file
from models import get_db, init_db
from game_logic import get_current_state, validate_selection, record_selection, reset_game, is_game_over, get_snake_order
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
            'SELECT id, name, jersey_number, position FROM players WHERE team_id = ? ORDER BY jersey_number',
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
    data = request.get_json()
    participant_name = data.get('participant_name')
    player_id = data.get('player_id')

    if not participant_name or not player_id:
        return jsonify({'success': False, 'error': '缺少参数'}), 400

    validation = validate_selection(participant_name, player_id)
    if not validation['valid']:
        return jsonify({'success': False, 'error': validation['error']}), 400

    record_selection(participant_name, player_id)
    return jsonify({'success': True, 'state': get_current_state()})


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


# ========== Init ==========

def ensure_db_initialized():
    """Initialize and seed DB on first run"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'draft.db')
    if not os.path.exists(db_path):
        seed_database()


ensure_db_initialized()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
