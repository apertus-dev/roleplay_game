from flask import Flask, render_template, request, jsonify, session
import database
from game_engine import GameEngine

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

engine = GameEngine()
database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/game/start', methods=['POST'])
def start_game():
    data = request.json
    state = engine.init_state()
    session['game_state'] = state
    session['player_name'] = data.get('player_name', '匿名玩家')
    
    node = engine.get_node(state['current_node'])
    return jsonify({'state': state, 'node': node})

@app.route('/api/game/choice', methods=['POST'])
def make_choice():
    state = session.get('game_state')
    if not state:
        return jsonify({'error': '游戏未开始'}), 400
    
    choice_index = request.json.get('choice_index')
    state, next_node_id, reaction = engine.make_choice(state, choice_index)
    session['game_state'] = state
    
    is_over, result, reason = engine.check_game_over(state)
    
    if is_over:
        aar = engine.generate_aar(state['tags'], result)
        game_id = database.save_game(
            session.get('player_name', '匿名玩家'),
            state['safety'], state['willingness'], state['rounds'],
            result, state['tags'], state['history'], aar
        )
        next_node = engine.get_node(next_node_id)
        return jsonify({
            'state': state, 'reaction': reaction,
            'node': next_node, 'game_over': True,
            'result': result, 'reason': reason,
            'aar': aar, 'game_id': game_id
        })
    
    next_node = engine.get_node(next_node_id)
    return jsonify({
        'state': state, 'reaction': reaction,
        'node': next_node, 'game_over': False
    })

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/api/history')
def get_history():
    return jsonify(database.get_all_games())

if __name__ == '__main__':
    app.run(debug=True, port=5001)
