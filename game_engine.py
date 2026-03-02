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
    
    def check_game_over(self, state):
        if state['safety'] <= 0:
            return True, 'lose', '院方安全感归零——对方失去了所有耐心，谈判破裂。'
        if state['current_node'] == 'ending_win':
            if state['willingness'] >= 50:
                return True, 'win', '谈判成功！你达成了预期目标。'
            else:
                return True, 'lose', '虽然完成了对话，但意愿度不足，对方不会真正推动。'
        if state['current_node'] == 'ending_lose':
            return True, 'lose', '未能在关键时刻提出完整诉求，谈判未达成目标。'
        if state['rounds'] >= state.get('max_rounds', 10):
            return True, 'lose', '对话回合耗尽，对方已经没有时间继续听下去了。'
        return False, None, None
    
    def generate_aar(self, tags, result):
        correct = [t for t in tags if any(k in t for k in ['认可', '成功', '打通', '修复', '验证', '拉满', '绝地', '理清', '完美', '契合'])]
        wrong = [t for t in tags if any(k in t for k in ['反感', '警惕', '丧失', '缺乏', '怀疑', '恐慌', '判定', '空洞', '触发违禁', '敏感', '彻底', '未满足'])]
        
        positive = f"✅ 你做对了：{correct[0].split('：')[1]}" if correct and '：' in correct[0] else "✅ 你做对了：在高压环境下坚持完成了整场对话，这本身就需要勇气。"
        negative = f"❌ 你踩坑了：{wrong[0].split('：')[1]}" if wrong and '：' in wrong[0] else "❌ 需要注意：整体表现平稳，但缺少让对方眼前一亮的关键突破点。"
        
        question = ("💡 灵魂追问：如果对方突然提出新的反对意见，你准备好了 Plan B 吗？" if result == 'win'
                    else "💡 灵魂追问：回顾整场对话，哪个瞬间你感觉到对方态度发生了转折？如果重来，你会做出什么不同的选择？")
        
        return f"{positive}\n\n{negative}\n\n{question}"
