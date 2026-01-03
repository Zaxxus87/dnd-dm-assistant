const API_BASE_URL = 'https://dnd-dm-assistant-691169217190.us-central1.run.app';

// Store the last generated NPC
let currentNPC = null;

// Google Drive API Configuration
const CLIENT_ID = '691169217190-k8lv755nt497jqq9fgaq0mdr87r23uoa.apps.googleusercontent.com'; // We'll get this in a moment
const API_KEY = 'AIzaSyAQ_q5OafH1Z-spa_fx37dZygppGjYFZAI'; // We'll get this in a moment
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

document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// NPC Generator Functions
async function generateNPC() {
    const race = document.getElementById('npc-race').value;
    const characterClass = document.getElementById('npc-class').value;
    const alignment = document.getElementById('npc-alignment').value;
    const resultDiv = document.getElementById('npc-result');
    const actionsDiv = document.getElementById('npc-actions');
    
    resultDiv.innerHTML = '<div class="loading">🎲 Generating NPC...</div>';
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
        
        resultDiv.innerHTML = `<div class="npc-content">${data.npc.replace(/\n/g, '<br>')}</div>`;
        actionsDiv.style.display = 'block';
        
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
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
        callback: '', // defined later
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
        // Initialize Google APIs
        gapiLoaded();
        gisLoaded();
        return;
    }
    
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
        // Parse NPC name from the generated text
        const nameMatch = currentNPC.text.match(/Name:\s*(.+)/i) || 
                         currentNPC.text.match(/NPC Name:\s*(.+)/i) ||
                         currentNPC.text.match(/^(.+?)\n/);
        const npcName = nameMatch ? nameMatch[1].trim() : 'Unnamed NPC';
        
        // Copy the template
        const copyResponse = await gapi.client.drive.files.copy({
            fileId: TEMPLATE_ID,
            resource: {
                name: `${npcName} - NPC`,
                parents: [FOLDER_ID]
            }
        });
        
        const newDocId = copyResponse.result.id;
        
        // Parse the NPC data
        const npcData = parseNPCText(currentNPC.text);
        
        // Fill the template
        await fillNPCTemplate(newDocId, npcData);
        
        // Show success message with link
        const docUrl = `https://docs.google.com/document/d/${newDocId}/edit`;
        const actionsDiv = document.getElementById('npc-actions');
        actionsDiv.innerHTML = `
            <button onclick="saveNPCToGoogleDrive()" class="drive-btn">💾 Save Another Copy</button>
            <div style="margin-top: 15px; padding: 15px; background: #e8f5e9; border-radius: 8px;">
                ✅ Saved! <a href="${docUrl}" target="_blank" style="color: #4285f4; font-weight: 600;">Open in Google Drive</a>
            </div>
        `;
        
    } catch (error) {
        alert('Error saving to Google Drive: ' + error.message);
        console.error(error);
    }
}

function parseNPCText(text) {
    const data = {};
    
    // Simple parsing - extract values after labels
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
            // Clean up markdown
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
        resource: {
            requests: replacements
        }
    });
}

// Load Google API on page load
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

document.getElementById('rulebook-query')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchRulebooks();
});

// Campaign Lore Functions
async function addLore() {
    const title = document.getElementById('lore-title').value;
    const category = document.getElementById('lore-category').value;
    const content = document.getElementById('lore-content').value;
    
    if (!title || !content) {
        alert('Please fill in title and content');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/campaign/lore?title=${encodeURIComponent(title)}&content=${encodeURIComponent(content)}&category=${category}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        alert('✅ Lore entry added successfully!');
        
        document.getElementById('lore-title').value = '';
        document.getElementById('lore-content').value = '';
        
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
                        <h4>${entry.title} <span class="lore-category">${entry.category}</span></h4>
                        <p>${entry.content}</p>
                    </div>
                `;
            });
            listDiv.innerHTML = html;
        } else {
            listDiv.innerHTML = '<div class="no-results">No lore entries found.</div>';
        }
        
    } catch (error) {
        listDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
    }
}
