// API Base URL - update this with your Cloud Run URL
const API_BASE_URL = 'https://dnd-dm-assistant-691169217190.us-central1.run.app';

// Tab switching
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
}

// Chat functionality
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const contextType = document.getElementById('context-type').value;
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    input.value = '';
    
    // Show loading
    const loadingDiv = addMessageToChat('assistant', '🎲 Thinking...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                context_type: contextType
            })
        });
        
        const data = await response.json();
        
        // Remove loading message
        loadingDiv.remove();
        
        // Add assistant response
        addMessageToChat('assistant', data.response);
        
    } catch (error) {
        loadingDiv.remove();
        addMessageToChat('assistant', '❌ Error: ' + error.message);
    }
}

function addMessageToChat(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    if (role === 'assistant') {
        messageDiv.innerHTML = `<strong>DM Assistant:</strong><br>${content}`;
    } else {
        messageDiv.textContent = content;
    }
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    return messageDiv;
}

// Allow Enter key to send message
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});

// NPC Generator
async function generateNPC() {
    const race = document.getElementById('npc-race').value || 'random';
    const npcClass = document.getElementById('npc-class').value || 'random';
    const alignment = document.getElementById('npc-alignment').value || 'random';
    const resultDiv = document.getElementById('npc-result');
    
    resultDiv.textContent = '🎲 Generating NPC...';
    resultDiv.classList.add('show');
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/generate-npc?race=${encodeURIComponent(race)}&character_class=${encodeURIComponent(npcClass)}&alignment=${encodeURIComponent(alignment)}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        resultDiv.textContent = data.npc;
        
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

// Campaign Lore
async function addLore() {
    const title = document.getElementById('lore-title').value.trim();
    const category = document.getElementById('lore-category').value;
    const content = document.getElementById('lore-content').value.trim();
    
    if (!title || !content) {
        alert('Please fill in both title and content');
        return;
    }
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/campaign/lore?title=${encodeURIComponent(title)}&content=${encodeURIComponent(content)}&category=${category}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        alert('✅ Lore entry added successfully!');
        
        // Clear form
        document.getElementById('lore-title').value = '';
        document.getElementById('lore-content').value = '';
        
        // Reload lore list
        loadLore();
        
    } catch (error) {
        alert('❌ Error adding lore: ' + error.message);
    }
}

async function loadLore() {
    const loreList = document.getElementById('lore-list');
    loreList.innerHTML = '<div class="loading">📚 Loading campaign lore...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/campaign/lore`);
        const data = await response.json();
        
        if (data.lore.length === 0) {
            loreList.innerHTML = '<p style="text-align: center; color: #999;">No lore entries yet. Add your first one above!</p>';
            return;
        }
        
        loreList.innerHTML = '';
        data.lore.forEach(entry => {
            const loreItem = document.createElement('div');
            loreItem.className = 'lore-item';
            loreItem.innerHTML = `
                <h3>${entry.title}</h3>
                <span class="category">${entry.category}</span>
                <div class="content">${entry.content}</div>
            `;
            loreList.appendChild(loreItem);
        });
        
    } catch (error) {
        loreList.innerHTML = `<div class="error">❌ Error loading lore: ${error.message}</div>`;
    }
}

// Rulebook Search Functions
async function searchRulebooks() {
    const query = document.getElementById('rulebook-query').value.trim();
    const resultsDiv = document.getElementById('rulebook-results');
    
    if (!query) {
        alert('Please enter a search query');
        return;
    }
    
    resultsDiv.innerHTML = '<div class="loading">🔍 Searching rulebooks...</div>';
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/search-rulebooks?query=${encodeURIComponent(query)}&n_results=5`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            let html = `<h3>Found ${data.count} results for "${data.query}"</h3>`;
            
            data.results.forEach((result, index) => {
                const similarity = (result.similarity * 100).toFixed(1);
                html += `
                    <div class="search-result">
                        <div class="source-info">
                            <span class="source">${result.source}</span>
                            <span class="page">Page ${result.page_number}</span>
                            <span class="similarity-badge">${similarity}% match</span>
                        </div>
                        <div class="text">${result.text}</div>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = '<div class="no-results">No results found. Try different keywords.</div>';
        }
        
    } catch (error) {
        resultsDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

async function askRulebook() {
    const query = document.getElementById('rulebook-query').value.trim();
    const resultsDiv = document.getElementById('rulebook-results');
    
    if (!query) {
        alert('Please enter a question');
        return;
    }
    
    resultsDiv.innerHTML = '<div class="loading">🤖 AI is analyzing rulebooks...</div>';
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/chat-with-rulebooks?message=${encodeURIComponent(query)}`,
            { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }
        );
        
        const data = await response.json();
        
        let html = `
            <div class="ai-answer">
                <h3>🤖 AI Answer:</h3>
                <div>${data.response.replace(/\n/g, '<br>')}</div>
            </div>
        `;
        
        if (data.sources && data.sources.length > 0) {
            html += `<h3>📚 Sources Referenced:</h3>`;
            data.sources.forEach(source => {
                html += `
                    <div class="search-result">
                        <div class="source-info">
                            <span class="source">${source.source}</span>
                            <span class="page">Page ${source.page_number}</span>
                        </div>
                        <div class="text">${source.text}</div>
                    </div>
                `;
            });
        }
        
        resultsDiv.innerHTML = html;
        
    } catch (error) {
        resultsDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

// Allow Enter key for rulebook search
document.addEventListener('DOMContentLoaded', () => {
    const rulebookQuery = document.getElementById('rulebook-query');
    if (rulebookQuery) {
        rulebookQuery.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchRulebooks();
            }
        });
    }
});
