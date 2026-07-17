let currentSessionId = null;
let sessionsList = [];
let webSearchEnabled = false;
let reasoningEnabled = false;

console.log("🚀 scripts.js chargé");

document.addEventListener('DOMContentLoaded', () => {
    console.log("✅ DOM prêt");
    initApp();
    setupEventListeners();
});

// INITIALISATION
async function initApp() {
    console.log("🔄 initApp");
    await loadSessions();
    
    const hash = window.location.hash;
    if (hash && hash.startsWith('#session-')) {
        const sessionId = hash.split('-')[1];
        selectSession(sessionId);
    } else if (sessionsList.length > 0) {
        selectSession(sessionsList[0].id);
    } else {
        createNewSession();
    }
}

// CONFIGURATION DES LISTENERS
function setupEventListeners() {
    console.log("⚙️ setupEventListeners");
    const chatForm = document.getElementById('chat-form');
    if (!chatForm) {
        console.error("❌ Formulaire #chat-form introuvable !");
        return;
    }
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        console.log("📤 Formulaire soumis");
        handleSendMessage();
    });
    console.log("✅ Événement submit attaché");

    const userInput = document.getElementById('user-input');
    if (userInput) {
        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.requestSubmit();
            }
        });
    }

    const searchBtn = document.getElementById('search-toggle');
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            webSearchEnabled = !webSearchEnabled;
            searchBtn.classList.toggle('active', webSearchEnabled);
        });
    }

    const reasoningBtn = document.getElementById('reasoning-toggle');
    if (reasoningBtn) {
        reasoningBtn.addEventListener('click', () => {
            reasoningEnabled = !reasoningEnabled;
            reasoningBtn.classList.toggle('active', reasoningEnabled);
        });
    }

    const modelSelector = document.getElementById('model-selector');
    if (modelSelector) {
        modelSelector.addEventListener('change', syncSessionParams);
    }
    const lengthSelector = document.getElementById('length-selector');
    if (lengthSelector) {
        lengthSelector.addEventListener('change', syncSessionParams);
    }

    // Mobile sidebar
    const mobileBackdrop = document.getElementById('mobile-sidebar-backdrop');
    const mobileSidebar = document.getElementById('mobile-sidebar');
    const openMobileBtn = document.getElementById('open-mobile-sidebar');
    const closeMobileBtn = document.getElementById('close-mobile-sidebar');

    function toggleMobileMenu(open) {
        if (open) {
            mobileBackdrop.classList.remove('hidden');
            setTimeout(() => mobileBackdrop.classList.remove('opacity-0'), 10);
            mobileSidebar.classList.remove('-translate-x-full');
        } else {
            mobileBackdrop.classList.add('opacity-0');
            mobileSidebar.classList.add('-translate-x-full');
            setTimeout(() => mobileBackdrop.classList.add('hidden'), 300);
        }
    }

    if (openMobileBtn) {
        openMobileBtn.addEventListener('click', () => toggleMobileMenu(true));
    }
    if (closeMobileBtn) {
        closeMobileBtn.addEventListener('click', () => toggleMobileMenu(false));
    }
    if (mobileBackdrop) {
        mobileBackdrop.addEventListener('click', () => toggleMobileMenu(false));
    }
}

// CHARGER LES DISCUSSIONS
async function loadSessions() {
    try {
        console.log("📡 Chargement des sessions...");
        const res = await fetch('/api/sessions');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        sessionsList = await res.json();
        console.log(`✅ ${sessionsList.length} sessions chargées`);
        renderSessions();
    } catch (err) {
        console.error("❌ Erreur lors du chargement des sessions:", err);
        sessionsList = [];
    }
}

function renderSessions() {
    const renderTarget = (containerId) => {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        
        sessionsList.forEach(session => {
            const isActive = String(session.id) === String(currentSessionId);
            const activeClass = isActive ? 'active' : '';

            const item = document.createElement('div');
            item.className = `session-item flex items-center justify-between ${activeClass}`;
            item.setAttribute('data-session-id', session.id);
            
            item.innerHTML = `
                <div class="flex items-center space-x-3 truncate flex-1" onclick="selectSession('${session.id}')">
                    <i class="fa-regular fa-comment text-sm shrink-0 ${isActive ? 'text-[#f5b342]' : 'text-[#5a7a9e]'}"></i>
                    <span class="session-name select-text" id="session-name-text-${session.id}" ondblclick="enableRename('${session.id}')">${escapeHtml(session.name)}</span>
                </div>
                <div class="session-actions flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
                    <button onclick="enableRename('${session.id}')" class="p-1 hover:text-[#f5b342] text-[#5a7a9e] rounded transition" title="Renommer">
                        <i class="fa-solid fa-pen text-[10px]"></i>
                    </button>
                    <button onclick="deleteSession('${session.id}')" class="p-1 hover:text-red-400 text-[#5a7a9e] rounded transition" title="Supprimer">
                        <i class="fa-solid fa-trash-can text-[10px]"></i>
                    </button>
                </div>
            `;
            container.appendChild(item);
        });
    };

    renderTarget('sessions-list');
    renderTarget('mobile-sessions-list');
}

async function createNewSession() {
    try {
        console.log("🆕 Création d'une nouvelle session");
        const res = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: "Nouvelle discussion" })
        });
        const data = await res.json();
        await loadSessions();
        selectSession(data.session_id);
    } catch (err) {
        console.error("❌ Échec de création de session:", err);
    }
}

async function selectSession(sessionId) {
    console.log(`📂 Sélection de la session ${sessionId}`);
    currentSessionId = sessionId;
    window.location.hash = `#session-${sessionId}`;
    
    renderSessions();
    
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    if (backdrop && !backdrop.classList.contains('hidden')) {
        backdrop.click();
    }

    try {
        const res = await fetch(`/api/sessions/${sessionId}/messages`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        const sessionObj = sessionsList.find(s => String(s.id) === String(sessionId));
        document.getElementById('active-session-title').innerText = sessionObj ? sessionObj.name : "Discussion";

        document.getElementById('model-selector').value = data.model || 'openrouter/free';
        document.getElementById('length-selector').value = data.length || 'medium';

        const wrapper = document.getElementById('messages-wrapper');
        const emptyState = document.getElementById('empty-state');
        if (!wrapper) return;

        // On supprime uniquement les messages, pas l'empty-state
        wrapper.querySelectorAll('.message-wrapper').forEach(el => el.remove());

        if (data.messages && data.messages.length > 0) {
            if (emptyState) emptyState.classList.add('hidden');
            data.messages.forEach(msg => {
                appendMessageToDOM(msg.role, msg.content);
            });
            scrollToBottom();
        } else {
            if (emptyState) emptyState.classList.remove('hidden');
        }
    } catch (err) {
        console.error("❌ Échec du chargement des messages:", err);
    }
}

async function syncSessionParams() {
    if (!currentSessionId) return;
    const model = document.getElementById('model-selector').value;
    const length = document.getElementById('length-selector').value;
    
    try {
        await fetch(`/api/sessions/${currentSessionId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model, length })
        });
    } catch (err) {
        console.error("❌ Échec de mise à jour des paramètres:", err);
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Voulez-vous vraiment supprimer cette conversation ?")) return;
    try {
        await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        await loadSessions();
        if (String(currentSessionId) === String(sessionId)) {
            currentSessionId = null;
            if (sessionsList.length > 0) {
                selectSession(sessionsList[0].id);
            } else {
                createNewSession();
            }
        }
    } catch (err) {
        console.error("❌ Échec de suppression:", err);
    }
}

function enableRename(sessionId) {
    const textEl = document.getElementById(`session-name-text-${sessionId}`);
    if (!textEl) return;
    const originalText = textEl.innerText;
    
    const input = document.createElement('input');
    input.type = 'text';
    input.value = originalText;
    input.className = "bg-[#0e1f36] border border-[#f5b342] rounded px-1.5 py-0.5 text-xs text-white outline-none w-full";
    
    const saveRename = async () => {
        const newName = input.value.trim() || originalText;
        textEl.innerText = newName;
        input.replaceWith(textEl);
        
        try {
            await fetch(`/api/sessions/${sessionId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName })
            });
            if (String(sessionId) === String(currentSessionId)) {
                document.getElementById('active-session-title').innerText = newName;
            }
            loadSessions();
        } catch (err) {
            console.error("❌ Échec du renommage:", err);
        }
    };

    input.addEventListener('blur', saveRename);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') saveRename();
    });
    
    textEl.replaceWith(input);
    input.focus();
    input.select();
}

async function handleSendMessage() {
    console.log("📨 handleSendMessage appelé");
    const inputField = document.getElementById('user-input');
    if (!inputField) {
        console.error("❌ #user-input introuvable");
        return;
    }
    const message = inputField.value.trim();
    if (!message) {
        console.log("⏭️ Message vide, ignore");
        return;
    }
    if (!currentSessionId) {
        console.error("❌ Aucune session active !");
        alert("Veuillez créer ou sélectionner une conversation avant d'envoyer un message.");
        return;
    }

    console.log(`📤 Envoi du message : "${message}" (session ${currentSessionId})`);

    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.classList.add('hidden');

    inputField.value = '';
    inputField.style.height = 'auto';

    appendMessageToDOM('user', message);
    scrollToBottom();

    const loadingId = appendLoadingIndicator();
    scrollToBottom();

    setControlsLocked(true);

    try {
        if (message.startsWith('/image ')) {
            const prompt = message.substring(7);
            console.log("🖼️ Génération d'image pour :", prompt);
            const res = await fetch('/api/generate-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, session_id: currentSessionId })
            });
            const data = await res.json();
            removeLoadingIndicator(loadingId);
            
            if (data.image_url) {
                appendImageMessage(data.image_url, prompt);
            } else {
                appendMessageToDOM('assistant', "❌ Impossible de générer l'image.");
            }
        } 
        else if (message.startsWith('/video ')) {
            const prompt = message.substring(7);
            console.log("🎬 Génération de vidéo pour :", prompt);
            const res = await fetch('/api/generate-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, session_id: currentSessionId })
            });
            const data = await res.json();
            removeLoadingIndicator(loadingId);
            
            if (data.video_url) {
                appendVideoMessage(data.video_url, prompt);
            } else {
                appendMessageToDOM('assistant', `❌ Échec: ${data.error || "Une erreur est survenue."}`);
            }
        } 
        else {
            const payload = {
                message: message,
                session_id: currentSessionId,
                model: document.getElementById('model-selector').value,
                length: document.getElementById('length-selector').value,
                enable_search: webSearchEnabled,
                enable_reasoning: reasoningEnabled
            };
            console.log("📡 Envoi au backend :", payload);

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            removeLoadingIndicator(loadingId);

            if (data.reply) {
                console.log("✅ Réponse reçue");
                appendMessageToDOM('assistant', data.reply);
                if (data.conversation_name) {
                    document.getElementById('active-session-title').innerText = data.conversation_name;
                    loadSessions();
                }
            } else {
                console.error("❌ Pas de reply dans la réponse :", data);
                appendMessageToDOM('assistant', `❌ Erreur: ${data.error || "Pas de réponse reçue"}`);
            }
        }
    } catch (err) {
        console.error("❌ Erreur lors de l'envoi :", err);
        removeLoadingIndicator(loadingId);
        appendMessageToDOM('assistant', "❌ Erreur de réseau ou serveur injoignable.");
    } finally {
        setControlsLocked(false);
        scrollToBottom();
    }
}

// ==========================================
// AJOUT DE MESSAGES DANS LE DOM
// ==========================================
function appendMessageToDOM(role, content) {
    console.log(`➕ Ajout d'un message ${role}`);
    const wrapper = document.getElementById('messages-wrapper');
    if (!wrapper) {
        console.error("❌ #messages-wrapper introuvable !");
        return;
    }
    const wrapperDiv = document.createElement('div');
    wrapperDiv.className = `message-wrapper ${role === 'user' ? 'user' : 'assistant'}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'U' : 'IA';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    if (role === 'user') {
        bubble.textContent = content;
    } else {
        const formatted = formatMarkdown(content);
        const sanitized = DOMPurify ? DOMPurify.sanitize(formatted) : formatted;
        bubble.innerHTML = `<div class="markdown-content">${sanitized}</div>`;
    }
    
    wrapperDiv.appendChild(avatar);
    wrapperDiv.appendChild(bubble);
    wrapper.appendChild(wrapperDiv);
}

function appendImageMessage(imageUrl, prompt) {
    const wrapper = document.getElementById('messages-wrapper');
    if (!wrapper) return;
    const wrapperDiv = document.createElement('div');
    wrapperDiv.className = 'message-wrapper assistant';
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = 'IA';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `
        <span class="text-xs text-[#94a9c9] italic">" ${escapeHtml(prompt)} "</span>
        <img src="${imageUrl}" class="rounded-xl max-h-80 w-full object-cover border border-[#2a3f5a] shadow-md cursor-pointer hover:opacity-95 transition" onclick="window.open('${imageUrl}')" />
        <a href="${imageUrl}" download="generation.jpg" class="text-xs text-[#f5b342] hover:text-[#e6a130] font-semibold flex items-center space-x-1 self-start pt-1">
            <i class="fa-solid fa-download"></i> Télécharger l'image
        </a>
    `;
    
    wrapperDiv.appendChild(avatar);
    wrapperDiv.appendChild(bubble);
    wrapper.appendChild(wrapperDiv);
}

function appendVideoMessage(videoUrl, prompt) {
    const wrapper = document.getElementById('messages-wrapper');
    if (!wrapper) return;
    const wrapperDiv = document.createElement('div');
    wrapperDiv.className = 'message-wrapper assistant';
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = 'IA';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `
        <span class="text-xs text-[#94a9c9] italic">" ${escapeHtml(prompt)} "</span>
        <video src="${videoUrl}" controls autoplay loop class="rounded-xl max-h-80 w-full border border-[#2a3f5a] shadow-md"></video>
        <a href="${videoUrl}" download="video.mp4" class="text-xs text-[#f5b342] hover:text-[#e6a130] font-semibold flex items-center space-x-1 self-start pt-1">
            <i class="fa-solid fa-download"></i> Télécharger la vidéo
        </a>
    `;
    
    wrapperDiv.appendChild(avatar);
    wrapperDiv.appendChild(bubble);
    wrapper.appendChild(wrapperDiv);
}

function appendLoadingIndicator() {
    const wrapper = document.getElementById('messages-wrapper');
    if (!wrapper) return null;
    const loadingId = 'loading-' + Date.now();
    const wrapperDiv = document.createElement('div');
    wrapperDiv.className = 'message-wrapper assistant typing-indicator';
    wrapperDiv.id = loadingId;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = 'IA';
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    `;
    
    wrapperDiv.appendChild(avatar);
    wrapperDiv.appendChild(bubble);
    wrapper.appendChild(wrapperDiv);
    return loadingId;
}

function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function scrollToBottom() {
    const container = document.getElementById('chat-container');
    if (container) container.scrollTop = container.scrollHeight;
}

function setControlsLocked(lock) {
    const input = document.getElementById('user-input');
    const btn = document.getElementById('submit-btn');
    if (input) input.disabled = lock;
    if (btn) {
        btn.disabled = lock;
        btn.style.opacity = lock ? '0.5' : '1';
    }
}

function appendPrefix(prefix) {
    const input = document.getElementById('user-input');
    if (input) {
        input.value = prefix + input.value;
        input.focus();
    }
}

function fillPrompt(text) {
    const input = document.getElementById('user-input');
    if (input) {
        input.value = text;
        input.focus();
    }
}

// ==========================================
// PARSEUR MARKDOWN
// ==========================================
function formatMarkdown(text) {
    if (!text) return "";
    let html = text;

    const reasoningRegex = /\*\*🧠 Raisonnement :\*\*([\s\S]*?)\*\*💡 Réponse :\*\*/g;
    const singleReasoningRegex = /\*\*🧠 Raisonnement :\*\*([\s\S]*)$/g;

    if (html.match(reasoningRegex)) {
        html = html.replace(reasoningRegex, (match, p1) => {
            return `<div class="reasoning-box"><div class="font-bold text-xs text-[#94a9c9] mb-1 flex items-center space-x-1.5"><i class="fa-solid fa-brain"></i> <span>RAISONNEMENT DE L'IA</span></div>${formatMarkdownTextOnly(p1)}</div><div class="font-bold text-xs text-[#f5b342] mb-1 flex items-center space-x-1.5"><i class="fa-solid fa-bolt-lightning"></i> <span>RÉPONSE FINALE</span></div>`;
        });
    } else if (html.match(singleReasoningRegex)) {
        html = html.replace(singleReasoningRegex, (match, p1) => {
            return `<div class="reasoning-box"><div class="font-bold text-xs text-[#94a9c9] mb-1 flex items-center space-x-1.5"><i class="fa-solid fa-brain"></i> <span>RAISONNEMENT DE L'IA</span></div>${formatMarkdownTextOnly(p1)}</div>`;
        });
    }

    return formatMarkdownTextOnly(html);
}

function formatMarkdownTextOnly(text) {
    let html = text;

    html = html.replace(/```(\w*)\n([\s\S]*?)```/gm, (match, lang, code) => {
        const escapedCode = escapeHtml(code.trim());
        return `<pre class="bg-[#0a1522] border border-[#2a3f5a] rounded-xl p-4 my-3.5 overflow-x-auto text-xs text-[#c8d6e5] font-mono"><code class="language-${lang}">${escapedCode}</code></pre>`;
    });

    html = html.replace(/`([^`\n]+)`/g, '<code class="bg-[#0a1522] text-[#f5b342] px-1.5 py-0.5 rounded-lg font-mono text-xs">$1</code>');

    html = html.replace(/^\s*###\s+(.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^\s*##\s+(.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^\s*#\s+(.+)$/gm, '<h1>$1</h1>');

    html = html.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([\s\S]+?)\*/g, '<em class="text-[#94a9c9] italic">$1</em>');

    html = html.replace(/^\s*&gt;\s+(.+)$/gm, '<blockquote>$1</blockquote>');
    html = html.replace(/^\s*[-*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)+/g, (match) => `<ul class="space-y-1 my-2">${match}</ul>`);

    // Tableaux
    const lines = html.split('\n');
    let insideTable = false;
    let tableHtml = "";
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('|') && line.endsWith('|')) {
            if (!insideTable) {
                insideTable = true;
                tableHtml = "<table>";
            }
            if (line.includes('---')) continue;

            const cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
            const tag = tableHtml === "<table>" ? 'th' : 'td';
            tableHtml += `<tr>${cells.map(c => `<${tag}>${c}</${tag}>`).join('')}</tr>`;
            lines[i] = "";
        } else {
            if (insideTable) {
                insideTable = false;
                tableHtml += "</table>";
                lines[i] = tableHtml + "\n" + lines[i];
            }
        }
    }
    html = lines.filter(l => l !== "").join('\n');

    html = html.split('\n\n').map(p => {
        const trimmed = p.trim();
        if (!trimmed) return "";
        if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol') || trimmed.startsWith('<pre') || trimmed.startsWith('<table') || trimmed.startsWith('<div')) {
            return trimmed;
        }
        return `<p>${trimmed}</p>`;
    }).join('\n');

    return html;
}