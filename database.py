import sqlite3
import json

DB_PATH = 'data/game.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '💼',
            story_file TEXT,
            initial_safety INTEGER DEFAULT 30,
            initial_willingness INTEGER DEFAULT 10,
            max_rounds INTEGER DEFAULT 10,
            win_threshold INTEGER DEFAULT 50,
            enabled INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            -- 场景文案
            location TEXT,
            intro_text TEXT,
            lose_safety_text TEXT,
            lose_willingness_text TEXT,
            lose_timeout_text TEXT,
            lose_ending_text TEXT,
            win_text TEXT,
            aar_win_question TEXT,
            aar_lose_question TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS game_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id INTEGER,
            player_name TEXT,
            final_safety INTEGER,
            final_willingness INTEGER,
            rounds_played INTEGER,
            result TEXT,
            tags TEXT,
            history TEXT,
            aar_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
        )
    ''')
    
    # 初始化 8 个场景
    c.execute('SELECT COUNT(*) FROM scenarios')
    if c.fetchone()[0] == 0:
        # 产品准入沟通 - 完整文案
        c.execute('''
            INSERT INTO scenarios (name, description, icon, story_file, enabled, sort_order,
                initial_safety, initial_willingness, max_rounds, win_threshold,
                location, intro_text, lose_safety_text, lose_willingness_text, lose_timeout_text,
                lose_ending_text, win_text, aar_win_question, aar_lose_question)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            '产品准入沟通',
            '与院长助理谈判，争取伊赫莱双规格院内准入',
            '🏥',
            'story_tree.json',
            1, 3,
            30, 10, 10, 50,
            '市第一人民医院 · 行政楼三层 · 院长助理办公室',
            '你是罗氏制药的大客户经理。今天下午，你将走进市第一人民医院王副院长的办公室，为伊赫莱争取双规格院内准入。\n\n每一句话都可能改变局势。选错了，不会立刻出局——但压力会层层叠加。',
            '院方安全感归零——王副院长失去了所有耐心，谈判破裂。',
            '虽然完成了对话，但准入意愿度不足，院长不会真正推动。',
            '对话回合耗尽，王副院长已经没有时间继续听下去了。',
            '未能在关键时刻提出完整的准入诉求，谈判未达成目标。',
            '你成功说服了王副院长支持伊赫莱双规格院内准入！',
            '如果王副院长突然说「药事会上其他领导反对怎么办」，你准备好了 Plan B 吗？',
            '回顾整场对话，哪个瞬间你感觉到王副院长的态度发生了转折？如果重来，你会在那个节点做出什么不同的选择？',
        ))
        
        # 其余 7 个场景 - 基础信息
        others = [
            ('信息探寻', '通过有效提问获取关键信息，建立客户画像', '🔍', 1),
            ('产品价值传递', '精准传递产品核心价值，应对客户质疑', '💎', 2),
            ('院长层面战略合作沟通', '与院长进行高层战略对话，推动长期合作', '🤝', 4),
            ('医务处医保办沟通', '与医务处和医保办沟通，解决政策与报销问题', '📋', 5),
            ('科研沟通', '推动临床科研合作，助力医院学术发展', '🔬', 6),
            ('项目推进及落地', '确保合作项目按计划推进并成功落地', '🚀', 7),
            ('跨部门协作', '协调多方资源，推动跨部门协同合作', '🔗', 8),
        ]
        c.executemany('''
            INSERT INTO scenarios (name, description, icon, sort_order) VALUES (?, ?, ?, ?)
        ''', others)
    
    conn.commit()
    conn.close()

# === 场景 ===
def get_all_scenarios():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM scenarios ORDER BY sort_order').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_scenario(scenario_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM scenarios WHERE id = ?', (scenario_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# === 游戏记录 ===
def save_game(scenario_id, player_name, final_safety, final_willingness, rounds_played, result, tags, history, aar_text):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO game_sessions (scenario_id, player_name, final_safety, final_willingness, rounds_played, result, tags, history, aar_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (scenario_id, player_name, final_safety, final_willingness, rounds_played, result,
          json.dumps(tags, ensure_ascii=False),
          json.dumps(history, ensure_ascii=False),
          aar_text))
    conn.commit()
    game_id = c.lastrowid
    conn.close()
    return game_id

def get_all_games(scenario_id=None):
    conn = get_conn()
    if scenario_id:
        rows = conn.execute('''
            SELECT g.*, s.name as scenario_name FROM game_sessions g
            LEFT JOIN scenarios s ON g.scenario_id = s.id
            WHERE g.scenario_id = ? ORDER BY g.created_at DESC
        ''', (scenario_id,)).fetchall()
    else:
        rows = conn.execute('''
            SELECT g.*, s.name as scenario_name FROM game_sessions g
            LEFT JOIN scenarios s ON g.scenario_id = s.id
            ORDER BY g.created_at DESC
        ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]
