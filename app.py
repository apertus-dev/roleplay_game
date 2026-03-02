import os
from flask import Flask, render_template, request, jsonify, session
import database
from game_engine import GameEngine

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

engine = GameEngine()
database.init_db()

# === 页面路由 ===
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/play/<int:scenario_id>')
def play(scenario_id):
    scenario = database.get_scenario(scenario_id)
    if not scenario or not scenario['enabled']:
        return render_template('home.html')
    return render_template('index.html', scenario=scenario)

@app.route('/history')
def history():
    return render_template('history.html')

# === 场景 API ===
@app.route('/api/scenarios')
def get_scenarios():
    return jsonify(database.get_all_scenarios())

# === 游戏 API ===
@app.route('/api/game/start', methods=['POST'])
def start_game():
    data = request.json
    scenario_id = data.get('scenario_id')
    scenario = database.get_scenario(scenario_id)
    if not scenario or not scenario['story_file']:
        return jsonify({'error': '场景不可用'}), 400
    
    state = engine.init_state(scenario)
    session['game_state'] = state
    session['player_name'] = data.get('player_name', '匿名玩家')
    session['scenario_id'] = scenario_id
    session['story_file'] = scenario['story_file']
    
    node = engine.get_node(scenario['story_file'], state['current_node'])
    return jsonify({'state': state, 'node': node})

@app.route('/api/game/choice', methods=['POST'])
def make_choice():
    state = session.get('game_state')
    story_file = session.get('story_file')
    if not state or not story_file:
        return jsonify({'error': '游戏未开始'}), 400
    
    choice_index = request.json.get('choice_index')
    state, next_node_id, reaction = engine.make_choice(state, story_file, choice_index)
    session['game_state'] = state
    
    scenario = database.get_scenario(session.get('scenario_id'))
    is_over, result, reason = engine.check_game_over(state, scenario)
    
    if is_over:
        aar = engine.generate_aar(state['tags'], result, scenario)
        game_id = database.save_game(
            session.get('scenario_id'), session.get('player_name', '匿名玩家'),
            state['safety'], state['willingness'], state['rounds'],
            result, state['tags'], state['history'], aar
        )
        next_node = engine.get_node(story_file, next_node_id)
        return jsonify({
            'state': state, 'reaction': reaction, 'node': next_node,
            'game_over': True, 'result': result, 'reason': reason,
            'aar': aar, 'game_id': game_id
        })
    
    next_node = engine.get_node(story_file, next_node_id)
    return jsonify({'state': state, 'reaction': reaction, 'node': next_node, 'game_over': False})

# === 历史 API ===
@app.route('/api/history')
def get_history():
    scenario_id = request.args.get('scenario_id')
    return jsonify(database.get_all_games(scenario_id))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
