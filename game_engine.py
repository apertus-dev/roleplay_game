import json
import os

class GameEngine:
    def __init__(self):
        self.stories = {}
    
    def load_story(self, story_file):
        if story_file in self.stories:
            return self.stories[story_file]
        path = os.path.join('data', story_file)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            self.stories[story_file] = json.load(f)
        return self.stories[story_file]
    
    def get_node(self, story_file, node_id):
        tree = self.load_story(story_file)
        return tree.get(node_id) if tree else None
    
    def init_state(self, scenario):
        return {
            'current_node': 'node_1_0',
            'safety': scenario.get('initial_safety', 30),
            'willingness': scenario.get('initial_willingness', 10),
            'max_rounds': scenario.get('max_rounds', 10),
            'rounds': 0,
            'tags': [],
            'history': []
        }
    
    def make_choice(self, state, story_file, choice_index):
        node = self.get_node(story_file, state['current_node'])
        if not node or choice_index >= len(node['choices']):
            return state, None, None
        
        choice = node['choices'][choice_index]
        
        state['safety'] = max(0, min(100, state['safety'] + choice['impact']['safety']))
        state['willingness'] = max(0, min(100, state['willingness'] + choice['impact']['willingness']))
        state['rounds'] += 1
        
        if choice.get('tag'):
            state['tags'].append(choice['tag'])
        
        state['history'].append({
            'node_title': node.get('title', ''),
            'npc_action': node.get('npc_action', ''),
            'npc_dialogue': node['npc_dialogue'],
            'player_choice': choice['text'],
            'choice_type': choice['type'],
            'safety_delta': choice['impact']['safety'],
            'willingness_delta': choice['impact']['willingness']
        })
        
        reaction = choice.get('npc_reaction', {})
        state['current_node'] = choice['next_node']
        return state, choice['next_node'], reaction
    
    def check_game_over(self, state, scenario):
        if state['safety'] <= 0:
            return True, 'lose', scenario.get('lose_safety_text') or '安全感归零，谈判破裂。'
        if state['current_node'] == 'ending_win':
            threshold = scenario.get('win_threshold', 50)
            if state['willingness'] >= threshold:
                return True, 'win', scenario.get('win_text') or '谈判成功！'
            else:
                return True, 'lose', scenario.get('lose_willingness_text') or '意愿度不足，未能达成目标。'
        if state['current_node'] == 'ending_lose':
            return True, 'lose', scenario.get('lose_ending_text') or '未能达成目标。'
        if state['rounds'] >= state.get('max_rounds', 10):
            return True, 'lose', scenario.get('lose_timeout_text') or '对话回合耗尽。'
        return False, None, None
    
    def generate_aar(self, tags, result, scenario):
        correct = [t for t in tags if any(k in t for k in ['认可', '成功', '打通', '修复', '验证', '拉满', '绝地', '理清', '完美', '契合'])]
        wrong = [t for t in tags if any(k in t for k in ['反感', '警惕', '丧失', '缺乏', '怀疑', '恐慌', '判定', '空洞', '触发违禁', '敏感', '彻底', '未满足'])]
        
        positive = f"✅ 你做对了：{correct[0].split('：')[1]}" if correct and '：' in correct[0] else "✅ 你做对了：在高压环境下坚持完成了整场对话，这本身就需要勇气。"
        negative = f"❌ 你踩坑了：{wrong[0].split('：')[1]}" if wrong and '：' in wrong[0] else "❌ 需要注意：整体表现平稳，但缺少让对方眼前一亮的关键突破点。"
        
        if result == 'win':
            q = scenario.get('aar_win_question') or '如果对方突然提出新的反对意见，你准备好了 Plan B 吗？'
        else:
            q = scenario.get('aar_lose_question') or '回顾整场对话，哪个瞬间是转折点？如果重来，你会做出什么不同的选择？'
        
        return f"{positive}\n\n{negative}\n\n💡 灵魂追问：{q}"
