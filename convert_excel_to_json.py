import pandas as pd
import json
import re

df = pd.read_excel('剧情树Excel设计与开发建议.xlsx', sheet_name='剧情树Excel设计与开发建议')

story_tree = {}
current_node_id = None
current_node = None

for idx, row in df.iterrows():
    node_name = row['剧情节点 (回合)']
    
    # 新节点开始
    if pd.notna(node_name):
        # 保存上一个节点
        if current_node_id and current_node:
            story_tree[current_node_id] = current_node
        
        # 提取 node_id (如 "1.0" -> "node_1_0")
        match = re.search(r'(\d+\.\d+[a-z]*)', node_name)
        if match:
            node_id_raw = match.group(1).replace('.', '_')
            current_node_id = f"node_{node_id_raw}"
        else:
            current_node_id = f"node_{idx}"
        
        current_node = {
            "node_id": current_node_id,
            "title": node_name,
            "npc_dialogue": row['NPC 动作与台词 (严格遵循Prompt规则)'],
            "choices": []
        }
    
    # 添加选项
    if pd.notna(row['玩家选项话术']):
        # 提取跳转目标
        next_node_raw = row['跳转走向 (分支线)']
        next_node = None
        
        if pd.notna(next_node_raw):
            # 提取 "跳转至 X.X" 中的 X.X
            match = re.search(r'(\d+\.\d+[a-z]*)', str(next_node_raw))
            if match:
                next_node = f"node_{match.group(1).replace('.', '_')}"
            elif '胜利' in str(next_node_raw) or 'NPC台词' in str(next_node_raw):
                next_node = "ending_win"
            elif '对话结束' in str(next_node_raw):
                next_node = "ending_lose"
        
        # 提取选项类型
        choice_type = row['选项分类']
        if pd.notna(choice_type):
            if '破局' in choice_type:
                tag_prefix = "correct"
            elif '踩雷' in choice_type:
                tag_prefix = "trap"
            else:
                tag_prefix = "neutral"
        else:
            tag_prefix = "neutral"
        
        # 生成 tag
        tag = row['触发隐藏状态'] if pd.notna(row['触发隐藏状态']) else ""
        
        choice = {
            "text": row['玩家选项话术'],
            "type": choice_type if pd.notna(choice_type) else "",
            "impact": {
                "safety": int(row['安全感']) if pd.notna(row['安全感']) else 0,
                "willingness": int(row['意愿值']) if pd.notna(row['意愿值']) else 0
            },
            "tag": tag,
            "next_node": next_node
        }
        
        if current_node:
            current_node["choices"].append(choice)

# 保存最后一个节点
if current_node_id and current_node:
    story_tree[current_node_id] = current_node

# 添加结局节点
story_tree["ending_win"] = {
    "node_id": "ending_win",
    "title": "胜利",
    "npc_dialogue": "行，我会考虑你说的伊赫莱 9mg 和 3mg 双规格的院内正式准入。",
    "choices": []
}

story_tree["ending_lose"] = {
    "node_id": "ending_lose",
    "title": "失败",
    "npc_dialogue": "(站起身) 今天就先聊到这里吧。",
    "choices": []
}

# 保存为 JSON
with open('data/story_tree.json', 'w', encoding='utf-8') as f:
    json.dump(story_tree, f, ensure_ascii=False, indent=2)

print("✅ 转换完成！生成了", len(story_tree), "个节点")
print("节点列表:", list(story_tree.keys()))
