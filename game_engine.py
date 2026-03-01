import json

class GameEngine:
    def __init__(self):
        with open('data/story_tree.json', 'r', encoding='utf-8') as f:
            self.story_tree = json.load(f)
    
    def get_node(self, node_id):
        return self.story_tree.get(node_id)
    
    def init_state(self):
        return {
            'current_node': 'node_1_0',
            'safety': 30,
            'willingness': 10,
            'rounds': 0,
            'tags': [],
            'history': []
        }
    
    def make_choice(self, state, choice_index):
        node = self.get_node(state['current_node'])
        if not node or choice_index >= len(node['choices']):
            return state, None, None
        
        choice = node['choices'][choice_index]
        
        old_safety = state['safety']
        old_willingness = state['willingness']
        
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
            return True, 'lose', '院方安全感归零——王副院长失去了所有耐心，谈判破裂。'
        if state['current_node'] == 'ending_win':
            if state['willingness'] >= 50:
                return True, 'win', '你成功说服了王副院长支持伊赫莱双规格院内准入！'
            else:
                return True, 'lose', '虽然完成了对话，但准入意愿度不足，院长不会真正推动。'
        if state['current_node'] == 'ending_lose':
            return True, 'lose', '未能在关键时刻提出完整的准入诉求，谈判未达成目标。'
        if state['rounds'] >= 10:
            return True, 'lose', '对话回合耗尽，王副院长已经没有时间继续听下去了。'
        return False, None, None
    
    def generate_aar(self, tags, result):
        correct = [t for t in tags if any(k in t for k in ['认可', '成功', '打通', '修复', '验证', '拉满', '绝地', '理清', '完美', '契合'])]
        wrong = [t for t in tags if any(k in t for k in ['反感', '警惕', '丧失', '缺乏', '怀疑', '恐慌', '判定', '空洞', '触发违禁', '敏感', '彻底', '未满足'])]
        
        if correct:
            positive = f"✅ 你做对了：{correct[0].split('：')[1] if '：' in correct[0] else correct[0]}"
        else:
            positive = "✅ 你做对了：在高压环境下坚持完成了整场对话，这本身就需要勇气。"
        
        if wrong:
            negative = f"❌ 你踩坑了：{wrong[0].split('：')[1] if '：' in wrong[0] else wrong[0]}"
        else:
            negative = "❌ 需要注意：整体表现平稳，但缺少让院长眼前一亮的关键突破点。"
        
        soul_questions = {
            'win': "💡 灵魂追问：如果王副院长突然说「药事会上其他领导反对怎么办」，你准备好了 Plan B 吗？",
            'lose': "💡 灵魂追问：回顾整场对话，哪个瞬间你感觉到王副院长的态度发生了转折？如果重来，你会在那个节点做出什么不同的选择？"
        }
        
        return f"{positive}\n\n{negative}\n\n{soul_questions.get(result, soul_questions['lose'])}"
