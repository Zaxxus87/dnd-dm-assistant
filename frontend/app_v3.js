const API_BASE_URL = 'https://dnd-dm-assistant-691169217190.us-central1.run.app';

// Store the last generated NPC
let currentNPC = null;

// Google Drive API Configuration
const CLIENT_ID = '691169217190-k8lv755nt497jqq9fgaq0mdr87r23uoa.apps.googleusercontent.com';
const API_KEY = 'AIzaSyAQ_q5OafH1Z-spa_fx37dZygppGjYFZAI';
const TEMPLATE_ID = '1mxeHjGBSAHXAWbj_hmSZr4ACiJBAszkExB9cIv37s2s';
const FOLDER_ID = '1s9uJh8y864acY1yAv20ughDqwztq6ao3';

// Tab switching
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
}

// NPC Generator Functions
async function generateNPC() {
    const race = document.getElementById('npc-race').value;
    const characterClass = document.getElementById('npc-class').value;
    const alignment = document.getElementById('npc-alignment').value;
    const resultDiv = document.getElementById('npc-result');
    const actionsDiv = document.getElementById('npc-actions');
    
    // Show animated loading
    resultDiv.className = 'result-box show';
        resultDiv.innerHTML = `
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">🎲 Generating your NPC...</p>
            <p class="loading-subtext">Consulting the ancient tomes...</p>
        </div>
    `;
    actionsDiv.style.display = 'none';
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/generate-npc?race=${race}&character_class=${characterClass}&alignment=${alignment}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        currentNPC = {
            text: data.npc,
            race: race,
            class: characterClass,
            alignment: alignment
        };
        
        // Display the generated NPC with formatting
        resultDiv.className = 'result-box show';
        resultDiv.innerHTML = `
            <div class="npc-display">
                <h3>✨ Generated NPC</h3>
                <div class="npc-content">${formatNPCText(data.npc)}</div>
            </div>
        `;
        
        // Show the save button
        actionsDiv.style.display = 'block';
        
    } catch (error) {
        resultDiv.className = 'result-box show';
        resultDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

function formatNPCText(text) {
    // Convert plain text to formatted HTML
    let formatted = text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/\n\n/g, '</p><p>') // Paragraphs
        .replace(/\n/g, '<br>') // Line breaks
        .replace(/•/g, '&bull;'); // Bullets
    
    return `<p>${formatted}</p>`;
}

// Google Drive Integration
let gapiInited = false;
let gisInited = false;
let tokenClient;
let accessToken = null;

function gapiLoaded() {
    gapi.load('client', initializeGapiClient);
}

async function initializeGapiClient() {
    await gapi.client.init({
        apiKey: API_KEY,
        discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/drive/v3/rest',
                       'https://docs.googleapis.com/$discovery/rest?version=v1'],
    });
    gapiInited = true;
}

function gisLoaded() {
    tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/documents',
        callback: '',
    });
    gisInited = true;
}

async function saveNPCToGoogleDrive() {
    if (!currentNPC) {
        alert('Please generate an NPC first!');
        return;
    }
    
    if (!gapiInited || !gisInited) {
        alert('Google Drive integration is loading... Please try again in a moment.');
        gapiLoaded();
        gisLoaded();
        return;
    }
    
    // Show loading in the button
    const actionsDiv = document.getElementById('npc-actions');
    actionsDiv.innerHTML = `
        <div class="saving-status">
            <div class="loading-spinner-small"></div>
            <span>Saving to Google Drive...</span>
        </div>
    `;
    
    tokenClient.callback = async (resp) => {
        if (resp.error !== undefined) {
            throw (resp);
        }
        accessToken = resp.access_token;
        await createNPCDocument();
    };
    
    if (accessToken === null) {
        tokenClient.requestAccessToken({prompt: 'consent'});
    } else {
        tokenClient.requestAccessToken({prompt: ''});
    }
}

async function createNPCDocument() {
    try {
        const nameMatch = currentNPC.text.match(/Name:\s*(.+)/i) || 
                         currentNPC.text.match(/NPC Name:\s*(.+)/i) ||
                         currentNPC.text.match(/^(.+?)\n/);
        const npcName = nameMatch ? nameMatch[1].trim() : 'Unnamed NPC';
        
        const copyResponse = await gapi.client.drive.files.copy({
            fileId: TEMPLATE_ID,
            resource: {
                name: `${npcName} - NPC`,
                parents: [FOLDER_ID]
            }
        });
        
        const newDocId = copyResponse.result.id;
        const npcData = parseNPCText(currentNPC.text);
        await fillNPCTemplate(newDocId, npcData);
        
        const docUrl = `https://docs.google.com/document/d/${newDocId}/edit`;
        const actionsDiv = document.getElementById('npc-actions');
        actionsDiv.innerHTML = `
            <button onclick="saveNPCToGoogleDrive()" class="drive-btn">💾 Save Another Copy</button>
            <div class="success-message">
                ✅ Saved successfully! 
                <a href="${docUrl}" target="_blank" class="doc-link">Open in Google Drive →</a>
            </div>
        `;
        
    } catch (error) {
        const actionsDiv = document.getElementById('npc-actions');
        actionsDiv.innerHTML = `
            <button onclick="saveNPCToGoogleDrive()" class="drive-btn">💾 Try Again</button>
            <div class="error-message">❌ Error: ${error.message}</div>
        `;
        console.error(error);
    }
}

function parseNPCText(text) {
    const data = {};
    const patterns = {
        name: /(?:NPC )?Name:\s*(.+)/i,
        race: /Race:\s*(.+)/i,
        class: /Class:\s*(.+)/i,
        alignment: /Alignment:\s*(.+)/i,
        level: /Level:\s*(.+)/i,
        world_placement: /World Placement:\s*(.+?)(?=\n\n|\nPhysical)/is,
        physical_description: /Physical Description:\s*(.+?)(?=\n\n|\nVoice)/is,
        voice_suggestions: /Voice Suggestions:\s*(.+?)(?=\n\n|\nPersonality)/is,
        personality_traits: /Personality Traits:\s*(.+?)(?=\n\n|\nBackground)/is,
        background: /Background:\s*(.+?)(?=\n\n|\nStr:|Stat Block)/is,
        str: /Str:\s*(\d+)/i,
        dex: /Dex:\s*(\d+)/i,
        con: /Con:\s*(\d+)/i,
        int: /Int:\s*(\d+)/i,
        wis: /Wis:\s*(\d+)/i,
        cha: /Cha:\s*(\d+)/i,
        saving_throws: /Saving Throws:\s*(.+)/i,
        skills: /Skills:\s*(.+)/i,
        senses: /Senses:\s*(.+)/i,
        languages: /Languages:\s*(.+)/i,
        abilities: /Abilities:\s*(.+?)(?=\n\n|\nActions:)/is,
        actions: /Actions:\s*(.+)$/is
    };
    
    for (const [key, pattern] of Object.entries(patterns)) {
        const match = text.match(pattern);
        if (match) {
            let value = match[1].trim();
            value = value.replace(/\*\s+\*\*/g, '• ').replace(/\*\*/g, '');
            data[key] = value;
        }
    }
    
    return data;
}

async function fillNPCTemplate(docId, npcData) {
    const replacements = [];
    const placeholderMap = {
        'NPC_NAME': npcData.name || '',
        'RACE': npcData.race || '',
        'CLASS': npcData.class || '',
        'ALIGNMENT': npcData.alignment || '',
        'LEVEL': npcData.level || '',
        'WORLD_PLACEMENT': npcData.world_placement || '',
        'PHYSICAL_DESCRIPTION': npcData.physical_description || '',
        'VOICE_SUGGESTIONS': npcData.voice_suggestions || '',
        'PERSONALITY_TRAITS': npcData.personality_traits || '',
        'BACKGROUND': npcData.background || '',
        'STR': npcData.str || '',
        'DEX': npcData.dex || '',
        'CON': npcData.con || '',
        'INT': npcData.int || '',
        'WIS': npcData.wis || '',
        'CHA': npcData.cha || '',
        'SAVING_THROWS': npcData.saving_throws || '',
        'SKILLS': npcData.skills || '',
        'SENSES': npcData.senses || '',
        'LANGUAGES': npcData.languages || '',
        'ABILITIES': npcData.abilities || '',
        'ACTIONS': npcData.actions || ''
    };
    
    for (const [placeholder, value] of Object.entries(placeholderMap)) {
        replacements.push({
            replaceAllText: {
                containsText: {
                    text: `{{${placeholder}}}`,
                    matchCase: true
                },
                replaceText: value
            }
        });
    }
    
    await gapi.client.docs.documents.batchUpdate({
        documentId: docId,
        resource: { requests: replacements }
    });
}

window.onload = function() {
    const script1 = document.createElement('script');
    script1.src = 'https://apis.google.com/js/api.js';
    script1.onload = gapiLoaded;
    document.body.appendChild(script1);
    
    const script2 = document.createElement('script');
    script2.src = 'https://accounts.google.com/gsi/client';
    script2.onload = gisLoaded;
    document.body.appendChild(script2);
};

// Campaign Lore Functions
async function addLore() {
    const title = document.getElementById('lore-title').value.trim();
    const category = document.getElementById('lore-category').value;
    const content = document.getElementById('lore-content').value.trim();
    
    if (!title || !content) {
        alert('Please fill in title and content');
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
        alert('❌ Error: ' + error.message);
    }
}

async function loadLore() {
    const listDiv = document.getElementById('lore-list');
    listDiv.innerHTML = '<div class="loading">Loading lore...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/campaign/lore`);
        const data = await response.json();
        
        if (data.lore && data.lore.length > 0) {
            let html = '<h3>Campaign Lore Entries</h3>';
            data.lore.forEach(entry => {
                html += `
                    <div class="lore-entry">
                        <h4>${entry.title} <span class="lore-category">[${entry.category}]</span></h4>
                        <p>${entry.content}</p>
                        <small class="lore-date">Created: ${new Date(entry.created_at.seconds * 1000).toLocaleDateString()}</small>
                    </div>
                `;
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="no-results">No lore entries found. Add your first one above!</div>';
        }
        
    } catch (error) {
        listDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

// Rulebook Search Functions (if not already present)
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
            
            data.results.forEach((result) => {
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

// Chat Functions
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const contextType = document.getElementById('context-type').value;
    const message = input.value.trim();
    
    if (!message) return;
    
    const messagesDiv = document.getElementById('chat-messages');
    messagesDiv.innerHTML += `<div class="message user-message">${message}</div>`;
    
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                context_type: contextType
            })
        });
        
        const data = await response.json();
        messagesDiv.innerHTML += `<div class="message assistant-message">${data.response.replace(/\n/g, '<br>')}</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
    } catch (error) {
        messagesDiv.innerHTML += `<div class="message error-message">❌ Error: ${error.message}</div>`;
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
    
    const rulebookQuery = document.getElementById('rulebook-query');
    if (rulebookQuery) {
        rulebookQuery.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchRulebooks();
        });
    }
});

// ============== MAP GENERATOR ==============

async function generateMap() {
    const description = document.getElementById('map-description').value.trim();
    const size = document.getElementById('map-size').value;
    const style = document.getElementById('map-style').value;
    const grid = document.getElementById('map-grid').checked;
    const resultDiv = document.getElementById('map-result');
    
    if (!description) {
        alert('Please describe the map you want to generate');
        return;
    }
    
    // Show loading animation
    resultDiv.innerHTML = `
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">🗺️ Generating your battle map...</p>
            <p class="loading-subtext">This may take 30-60 seconds...</p>
        </div>
    `;
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/generate-map?description=${encodeURIComponent(description)}&size=${size}&style=${encodeURIComponent(style)}&grid=${grid}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.innerHTML = `
                <div class="map-display">
                    <h3>✨ Generated Battle Map</h3>
                    <div class="map-image-container">
                        <img src="data:image/png;base64,${data.image_base64}" alt="Generated Map" class="generated-map" />
                    </div>
                    <div class="map-actions">
                        <a href="${data.image_url}" download="battle_map.png" class="download-btn">📥 Download PNG</a>
                        <button onclick="copyMapUrl('${data.image_url}')" class="copy-btn">📋 Copy URL</button>
                    </div>
                    <p class="map-info">Size: ${data.dimensions} | <a href="${data.image_url}" target="_blank">Open in new tab</a></p>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `<div class="error">❌ Error: ${data.error || 'Failed to generate map'}</div>`;
        }
        
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}

function copyMapUrl(url) {
    navigator.clipboard.writeText(url).then(() => {
        alert('✅ Map URL copied to clipboard!');
    }).catch(err => {
        alert('Failed to copy URL');
    });
}
