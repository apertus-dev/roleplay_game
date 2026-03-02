let gameState = null;

function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

// 打字机效果
async function typeText(element, text, speed = 30) {
    element.textContent = '';
    for (let i = 0; i < text.length; i++) {
        element.textContent += text[i];
        await sleep(speed);
    }
}

// 更新仪表盘
function updateMeters(state, oldState) {
    document.getElementById('round-badge').textContent = `ROUND ${state.rounds}/${state.max_rounds || 10}`;
    
    const safetyBar = document.getElementById('safety-bar');
    const willBar = document.getElementById('willingness-bar');
    const safetyVal = document.getElementById('safety-value');
    const willVal = document.getElementById('willingness-value');
    
    safetyBar.style.width = `${state.safety}%`;
    willBar.style.width = `${state.willingness}%`;
    safetyVal.textContent = state.safety;
    willVal.textContent = state.willingness;
    
    // 数值变化闪烁
    if (oldState) {
        if (state.safety !== oldState.safety) {
            const cls = state.safety > oldState.safety ? 'flash-up' : 'flash-down';
            safetyVal.classList.add(cls);
            setTimeout(() => safetyVal.classList.remove(cls), 800);
        }
        if (state.willingness !== oldState.willingness) {
            const cls = state.willingness > oldState.willingness ? 'flash-up' : 'flash-down';
            willVal.classList.add(cls);
            setTimeout(() => willVal.classList.remove(cls), 800);
        }
    }
    
    // 低值警告色
    safetyBar.style.background = state.safety <= 15 ? 'var(--accent-red)' : 'var(--accent-green)';
}

// 渲染场景叙述
async function renderScene(node) {
    const area = document.getElementById('narrative-area');
    area.innerHTML = '';
    
    if (!node.scene) return;
    
    // 地点
    if (node.scene.location) {
        document.getElementById('location-text').textContent = node.scene.location;
    }
    
    // 叙述文字 - 打字机效果
    if (node.scene.narration) {
        const narDiv = document.createElement('div');
        narDiv.className = 'scene-narration';
        area.appendChild(narDiv);
        await typeText(narDiv, node.scene.narration, 25);
        await sleep(400);
    }
}

// 渲染 NPC 对话
async function renderDialogue(node) {
    const area = document.getElementById('dialogue-area');
    area.innerHTML = '';
    
    const block = document.createElement('div');
    block.className = 'npc-block';
    
    // NPC 动作
    if (node.npc_action) {
        const actionDiv = document.createElement('div');
        actionDiv.className = 'npc-action';
        actionDiv.textContent = node.npc_action;
        block.appendChild(actionDiv);
    }
    
    // NPC 对话框
    const dialogueDiv = document.createElement('div');
    dialogueDiv.className = 'npc-dialogue';
    
    const nameDiv = document.createElement('div');
    nameDiv.className = 'npc-name';
    nameDiv.textContent = '王副院长';
    dialogueDiv.appendChild(nameDiv);
    
    const textDiv = document.createElement('div');
    dialogueDiv.appendChild(textDiv);
    block.appendChild(dialogueDiv);
    area.appendChild(block);
    
    await typeText(textDiv, node.npc_dialogue, 30);
    await sleep(300);
}

// 渲染选项
function renderChoices(choices) {
    const area = document.getElementById('choices-area');
    area.innerHTML = '';
    
    choices.forEach((choice, i) => {
        const btn = document.createElement('button');
        btn.className = 'choice-btn';
        btn.textContent = choice.text;
        btn.onclick = () => makeChoice(i);
        area.appendChild(btn);
    });
}

// 显示玩家选择回显
function showPlayerEcho(text) {
    const area = document.getElementById('dialogue-area');
    const echo = document.createElement('div');
    echo.className = 'player-echo';
    echo.innerHTML = `
        <div class="player-echo-label">你的回应</div>
        <div class="player-echo-text">${text}</div>
    `;
    area.appendChild(echo);
}

// 显示 NPC 反应
async function showReaction(reaction) {
    if (!reaction || !reaction.action) return;
    
    const area = document.getElementById('dialogue-area');
    const block = document.createElement('div');
    block.className = 'reaction-block';
    
    const actionDiv = document.createElement('div');
    actionDiv.className = 'reaction-action';
    block.appendChild(actionDiv);
    area.appendChild(block);
    
    await typeText(actionDiv, reaction.action, 35);
    
    if (reaction.thought) {
        await sleep(800);
        const thoughtDiv = document.createElement('div');
        thoughtDiv.className = 'reaction-thought';
        block.appendChild(thoughtDiv);
        await typeText(thoughtDiv, reaction.thought, 40);
    }
    
    await sleep(600);
}

// 过场转场
async function transition(text = '...') {
    const overlay = document.createElement('div');
    overlay.className = 'transition-overlay';
    overlay.innerHTML = `<div class="transition-text">${text}</div>`;
    document.body.appendChild(overlay);
    
    await sleep(100);
    overlay.classList.add('active');
    await sleep(1500);
    overlay.classList.remove('active');
    await sleep(600);
    overlay.remove();
}

// 开始游戏
async function startGame() {
    const name = document.getElementById('player-name').value.trim() || '匿名玩家';
    const scenarioId = document.getElementById('scenario-id').value;
    
    const res = await fetch('/api/game/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: name, scenario_id: parseInt(scenarioId) })
    });
    const data = await res.json();
    
    gameState = data.state;
    showScreen('game-screen');
    updateMeters(gameState);
    
    await renderScene(data.node);
    await renderDialogue(data.node);
    renderChoices(data.node.choices);
}

// 做出选择
async function makeChoice(index) {
    // 禁用按钮 & 高亮选中
    const btns = document.querySelectorAll('.choice-btn');
    btns.forEach((btn, i) => {
        btn.disabled = true;
        if (i === index) btn.classList.add('selected');
    });
    
    const oldState = { ...gameState };
    
    const res = await fetch('/api/game/choice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ choice_index: index })
    });
    const data = await res.json();
    
    gameState = data.state;
    
    // 1. 选中选项短暂停留
    await sleep(400);
    const choiceText = btns[index].textContent;
    document.getElementById('choices-area').innerHTML = '';
    showPlayerEcho(choiceText);
    
    // 2. 更新数值
    await sleep(500);
    updateMeters(gameState, oldState);
    
    // 3. 显示 NPC 反应
    await sleep(600);
    await showReaction(data.reaction);
    
    // 4. 停顿后过场
    await sleep(800);
    
    if (data.game_over) {
        await transition(data.result === 'win' ? '谈判结束' : '...');
        showEndScreen(data);
    } else {
        // 过场开始时清空旧内容
        document.getElementById('narrative-area').innerHTML = '';
        document.getElementById('dialogue-area').innerHTML = '';
        document.getElementById('choices-area').innerHTML = '';
        
        await transition();
        
        await renderScene(data.node);
        await renderDialogue(data.node);
        renderChoices(data.node.choices);
    }
}

// 结算界面
function showEndScreen(data) {
    showScreen('end-screen');
    
    const isWin = data.result === 'win';
    document.getElementById('end-icon').textContent = isWin ? '🤝' : '🚪';
    
    const title = document.getElementById('end-title');
    title.textContent = isWin ? '谈判成功' : '谈判失败';
    title.className = `end-title ${data.result}`;
    
    document.getElementById('end-reason').textContent = data.reason;
    
    document.getElementById('end-stats').innerHTML = `
        <div class="end-stat">
            <div class="end-stat-value">${gameState.rounds}</div>
            <div class="end-stat-label">回合数</div>
        </div>
        <div class="end-stat">
            <div class="end-stat-value">${gameState.safety}</div>
            <div class="end-stat-label">安全感</div>
        </div>
        <div class="end-stat">
            <div class="end-stat-value">${gameState.willingness}</div>
            <div class="end-stat-label">意愿度</div>
        </div>
    `;
    
    document.getElementById('aar-content').textContent = data.aar;
}
