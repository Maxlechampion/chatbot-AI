let currentSessionId = null;
let sessionsList = [];
let webSearchEnabled = false;
let reasoningEnabled = false;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

// INITIALISATION
async function initApp() {
    await loadSessions();
    
    // Charger la session à partir de l'URL hash ou la dernière active
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
    // Formulaire d'envoi
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleSendMessage();
    });

    // Auto-ajustement de la hauteur du textarea
    const userInput = document.getElementById('user-input');
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Envoyer sur Entrée (sans Shift)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });

    // Toggle Recherche Web
    const searchBtn = document.getElementById('search-toggle');
    searchBtn.addEventListener('click', () => {
        webSearchEnabled = !webSearchEnabled;
        searchBtn.classList.toggle('border-amber-500/40', webSearchEnabled);
        searchBtn.classList.toggle('bg-amber-500/5', webSearchEnabled);
        searchBtn.classList.toggle('text-amber-400', webSearchEnabled);
        const icon = searchBtn.querySelector('i');
        icon.classList.toggle('text-amber-400', webSearchEnabled);
    });

    // Toggle Mode Raisonnement
    const reasoningBtn = document.getElementById('reasoning-toggle');
    reasoningBtn.addEventListener('click', () => {
        reasoningEnabled = !reasoningEnabled;
        reasoningBtn.classList.toggle('border-amber-500/40', reasoningEnabled);
        reasoningBtn.classList.toggle('bg-amber-500/5', reasoningEnabled);
        reasoningBtn.classList.toggle('text-amber-400', reasoningEnabled);
        const icon = reasoningBtn.querySelector('i');
        icon.classList.toggle('text-amber-400', reasoningEnabled);
    });

    // Synchronisation des changements de modèle et longueur
    document.getElementById('model-selector').addEventListener('change', syncSessionParams);
    document.getElementById('length-selector').addEventListener('change', syncSessionParams);

    // Sidebar Mobile Drawer Event
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

    openMobileBtn.addEventListener('click', () => toggleMobileMenu(true));
    closeMobileBtn.addEventListener('click', () => toggleMobileMenu(false));
    mobileBackdrop.addEventListener('click', () => toggleMobileMenu(false));
}

// CHARGER LES DISCUSSIONS
async function loadSessions() {
    try {
        const res = await fetch('/api/sessions');
        sessionsList = await res.json();
        renderSessions();
    } catch (err) {
        console.error("Erreur lors du chargement des sessions:", err);
    }
}

// GENERER LA LISTE DES DISCUSSIONS (DESKTOP ET MOBILE)
function renderSessions() {
    const renderTarget = (containerId) => {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        sessionsList.forEach(session => {
            const isActive = String(session.id) === String(currentSessionId);
            const activeClass = isActive 
                ? 'bg-[#27272a] text-amber-400 border-l-2 border-amber-500' 
                : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-white';

            const item = document.createElement('div');
            item.className = `group flex items-center justify-between px-3 py-2.5 rounded-xl transition duration-150 cursor-pointer ${activeClass}`;
            item.setAttribute('data-session-id', session.id);
            
            item.innerHTML = `
                <div class="flex items-center space-x-3 truncate flex-1" onclick="selectSession('${session.id}')">
                    <i class="fa-regular fa-comment text-sm shrink-0 ${isActive ? 'text-amber-500' : 'text-zinc-500'}"></i>
                    <span class="text-xs font-medium truncate select-text" id="session-name-text-${session.id}" ondblclick="enableRename('${session.id}')">${escapeHtml(session.name)}</span>
                </div>
                <div class="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
                    <button onclick="enableRename('${session.id}')" class="p-1 hover:text-amber-400 text-zinc-500 rounded transition" title="Renommer">
                        <i class="fa-solid fa-pen text-[10px]"></i>
                    </button>
                    <button onclick="deleteSession('${session.id}')" class="p-1 hover:text-red-400 text-zinc-500 rounded transition" title="Supprimer">
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

// CRÉATION DE SESSION
async function createNewSession() {
    try {
        const res = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: "Nouvelle discussion" })
        });
        const data = await res.json();
        await loadSessions();
        selectSession(data.session_id);
    } catch (err) {
        console.error("Échec de création de session:", err);
    }
}

// SELECTIONNER UNE DISCUSSION
async function selectSession(sessionId) {
    currentSessionId = sessionId;
    window.location.hash = `#session-${sessionId}`;
    
    // Mise à jour de l'historique visuellement
    renderSessions();
    
    // Fermeture du menu mobile s'il est ouvert
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    if (!backdrop.classList.contains('hidden')) {
        backdrop.click();
    }

    try {
        const res = await fetch(`/api/sessions/${sessionId}/messages`);
        const data = await res.json();
        
        // Mettre à jour le titre actif
        const sessionObj = sessionsList.find(s => String(s.id) === String(sessionId));
        document.getElementById('active-session-title').innerText = sessionObj ? sessionObj.name : "Discussion";

        // Mettre à jour les sélecteurs
        document.getElementById('model-selector').value = data.model;
        document.getElementById('length-selector').value = data.length;

        // Rendu des messages
        const wrapper = document.getElementById('messages-wrapper');
        const emptyState = document.getElementById('empty-state');
        wrapper.innerHTML = '';

        if (data.messages && data.messages.length > 0) {
            emptyState.classList.add('hidden');
            data.messages.forEach(msg => {
                appendMessageToDOM(msg.role, msg.content);
            });
            scrollToBottom();
        } else {
            emptyState.classList.remove('hidden');
        }
    } catch (err) {
        console.error("Échec du chargement des messages:", err);
    }
}

// SYNCHRONISATION DES OPTIONS DE L'IA
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
        console.error("Échec de mise à jour des paramètres:", err);
    }
}

// SUPPRESSION DE SESSION
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
        console.error("Échec de suppression:", err);
    }
}

// RENOMMAGE DOUBLE CLIC
function enableRename(sessionId) {
    const textEl = document.getElementById(`session-name-text-${sessionId}`);
    const originalText = textEl.innerText;
    
    const input = document.createElement('input');
    input.type = 'text';
    input.value = originalText;
    input.className = "bg-zinc-800 border border-amber-500 rounded px-1.5 py-0.5 text-xs text-white outline-none w-full";
    
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
            // Mettre à jour le header principal s'il s'agit de la session active
            if (String(sessionId) === String(currentSessionId)) {
                document.getElementById('active-session-title').innerText = newName;
            }
            loadSessions();
        } catch (err) {
            console.error("Échec du renommage:", err);
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

// ENVOI DE MESSAGE ET DISPATCHING MULTIMÉDIA
async function handleSendMessage() {
    const inputField = document.getElementById('user-input');
    const message = inputField.value.trim();
    if (!message || !currentSessionId) return;

    // Masquer l'écran vide
    document.getElementById('empty-state').classList.add('hidden');

    // Vider l'input et réinitialiser sa taille
    inputField.value = '';
    inputField.style.height = 'auto';

    // Ajouter message utilisateur
    appendMessageToDOM('user', message);
    scrollToBottom();

    // Ajouter indicateur d'écriture
    const loadingId = appendLoadingIndicator();
    scrollToBottom();

    // Verrouiller les contrôles
    setControlsLocked(true);

    try {
        // Détections de commandes multimédias
        if (message.startsWith('/image ')) {
            const prompt = message.substring(7);
            const res = await fetch('/api/generate-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
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
            const res = await fetch('/api/generate-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
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
            // Requête Chat classique
            const payload = {
                message: message,
                session_id: currentSessionId,
                model: document.getElementById('model-selector').value,
                length: document.getElementById('length-selector').value,
                enable_search: webSearchEnabled,
                enable_reasoning: reasoningEnabled
            };

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            removeLoadingIndicator(loadingId);

            if (data.reply) {
                appendMessageToDOM('assistant', data.reply);
                if (data.conversation_name) {
                    document.getElementById('active-session-title').innerText = data.conversation_name;
                    loadSessions();
                }
            } else {
                appendMessageToDOM('assistant', `❌ Erreur: ${data.error || "Pas de réponse reçue"}`);
            }
        }
    } catch (err) {
        console.error(err);
        removeLoadingIndicator(loadingId);
        appendMessageToDOM('assistant', "❌ Erreur de réseau ou serveur injoignable.");
    } finally {
        setControlsLocked(false);
        scrollToBottom();
    }
}

// INJECTION DES MESSAGES DANS LE DOM
function appendMessageToDOM(role, content) {
    const wrapper = document.getElementById('messages-wrapper');
    const msgBlock = document.createElement('div');
    
    const isUser = role === 'user';
    msgBlock.className = `flex items-start space-x-3 md:space-x-4 max-w-4xl animate-fade-in ${isUser ? 'self-end flex-row-reverse space-x-reverse ml-auto' : ''}`;
    
    const avatar = isUser 
        ? `<div class="w-8 h-8 rounded-xl bg-amber-500 flex-shrink-0 flex items-center justify-center text-zinc-950 text-xs font-bold shadow-md shadow-amber-500/10">U</div>`
        : `<div class="w-8 h-8 rounded-xl bg-[#1c1c1e] border border-zinc-800 flex-shrink-0 flex items-center justify-center text-amber-500 text-xs font-bold shadow-md">IA</div>`;

    const bubbleStyle = isUser
        ? `bg-[#1c1c1e] text-zinc-100 border border-zinc-800 rounded-2xl rounded-tr-none px-4 py-3 max-w-[85%] text-sm shadow-md`
        : `bg-transparent text-zinc-200 px-1 py-1 max-w-full text-sm leading-relaxed flex-1 overflow-x-auto`;

    const bodyContent = isUser 
        ? `<p class="whitespace-pre-wrap">${escapeHtml(content)}</p>`
        : `<div class="markdown-content">${formatMarkdown(content)}</div>`;

    msgBlock.innerHTML = `
        ${avatar}
        <div class="${bubbleStyle}">
            ${bodyContent}
        </div>
    `;
    
    wrapper.appendChild(msgBlock);
}

// INJECTER IMAGE GÉNÉRÉE
function appendImageMessage(imageUrl, prompt) {
    const wrapper = document.getElementById('messages-wrapper');
    const block = document.createElement('div');
    block.className = "flex items-start space-x-4 max-w-4xl animate-fade-in";
    block.innerHTML = `
        <div class="w-8 h-8 rounded-xl bg-[#1c1c1e] border border-zinc-800 flex-shrink-0 flex items-center justify-center text-amber-500 text-xs font-bold">IA</div>
        <div class="bg-[#121214] border border-zinc-800/80 p-3 rounded-2xl rounded-tl-none shadow-xl max-w-[80%] flex flex-col space-y-2">
            <span class="text-xs text-zinc-500 italic">" ${escapeHtml(prompt)} "</span>
            <img src="${imageUrl}" class="rounded-xl max-h-96 w-full object-cover border border-zinc-800 shadow-md cursor-pointer hover:opacity-95 transition" onclick="window.open('${imageUrl}')"/>
            <a href="${imageUrl}" download="generation.jpg" class="text-xs text-amber-400 hover:text-amber-300 font-semibold flex items-center space-x-1 self-start pt-1">
                <i class="fa-solid fa-download"></i>
                <span>Télécharger l'image</span>
            </a>
        </div>
    `;
    wrapper.appendChild(block);
}

// INJECTER VIDÉO GÉNÉRÉE
function appendVideoMessage(videoUrl, prompt) {
    const wrapper = document.getElementById('messages-wrapper');
    const block = document.createElement('div');
    block.className = "flex items-start space-x-4 max-w-4xl animate-fade-in";
    block.innerHTML = `
        <div class="w-8 h-8 rounded-xl bg-[#1c1c1e] border border-zinc-800 flex-shrink-0 flex items-center justify-center text-amber-500 text-xs font-bold">IA</div>
        <div class="bg-[#121214] border border-zinc-800/80 p-3 rounded-2xl rounded-tl-none shadow-xl max-w-[80%] flex flex-col space-y-2">
            <span class="text-xs text-zinc-500 italic">" ${escapeHtml(prompt)} "</span>
            <video src="${videoUrl}" controls autoplay loop class="rounded-xl max-h-96 w-full border border-zinc-800 shadow-md"></video>
            <a href="${videoUrl}" download="video.mp4" class="text-xs text-amber-400 hover:text-amber-300 font-semibold flex items-center space-x-1 self-start pt-1">
                <i class="fa-solid fa-download"></i>
                <span>Télécharger la vidéo</span>
            </a>
        </div>
    `;
    wrapper.appendChild(block);
}

// GESTION DU REBOND EN COULISSE (Indicateur de chargement d'IA)
function appendLoadingIndicator() {
    const wrapper = document.getElementById('messages-wrapper');
    const loadingId = 'loading-' + Date.now();
    const block = document.createElement('div');
    block.className = "flex items-start space-x-4 max-w-xl animate-fade-in";
    block.id = loadingId;
    block.innerHTML = `
        <div class="w-8 h-8 rounded-xl bg-[#1c1c1e] border border-zinc-800 flex-shrink-0 flex items-center justify-center text-amber-500 text-xs font-bold">IA</div>
        <div class="bg-[#121214] border border-zinc-800/60 px-4 py-3 rounded-2xl rounded-tl-none flex items-center space-x-1.5 shadow-md">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;
    wrapper.appendChild(block);
    return loadingId;
}

function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// SÉCURITÉ ET RENDU UTILS
function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function scrollToBottom() {
    const container = document.getElementById('chat-container');
    container.scrollTop = container.scrollHeight;
}

function setControlsLocked(lock) {
    document.getElementById('user-input').disabled = lock;
    document.getElementById('submit-btn').disabled = lock;
    document.getElementById('submit-btn').style.opacity = lock ? '0.5' : '1';
}

function appendPrefix(prefix) {
    const input = document.getElementById('user-input');
    input.value = prefix + input.value;
    input.focus();
}

function fillPrompt(text) {
    const input = document.getElementById('user-input');
    input.value = text;
    input.focus();
}

// ==========================================
// PARSEUR MARKDOWN AVANCÉ ET INTELLIGENT
// ==========================================
function formatMarkdown(text) {
    if (!text) return "";
    let html = text;

    // Parser pour le bloc de Raisonnement DeepSeek R1 (**🧠 Raisonnement :**)
    const reasoningRegex = /\*\*🧠 Raisonnement :\*\*([\s\S]*?)\*\*💡 Réponse :\*\*/g;
    const singleReasoningRegex = /\*\*🧠 Raisonnement :\*\*([\s\S]*)$/g;

    if (html.match(reasoningRegex)) {
        html = html.replace(reasoningRegex, (match, p1) => {
            return `<div class="reasoning-box"><div class="font-bold text-xs text-zinc-400 mb-1 flex items-center space-x-1.5"><i class="fa-solid fa-brain"></i> <span>RAISONNEMENT DE L'IA</span></div>${formatMarkdownTextOnly(p1)}</div><div class="font-bold text-xs text-amber-400 mb-1 flex items-center space-x-1.5"><i class="fa-solid fa-bolt-lightning"></i> <span>RÉPONSE FINALE</span></div>`;
        });
    } else if (html.match(singleReasoningRegex)) {
        html = html.replace(singleReasoningRegex, (match, p1) => {
            return `<div class="reasoning-box"><div class="font-bold text-xs text-zinc-400 mb-1 flex items-center space-x-1.5"><i class="fa-solid fa-brain"></i> <span>RAISONNEMENT DE L'IA</span></div>${formatMarkdownTextOnly(p1)}</div>`;
        });
    }

    return formatMarkdownTextOnly(html);
}

function formatMarkdownTextOnly(text) {
    let html = text;

    // 1. Code Blocks (```lang ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/gm, (match, lang, code) => {
        const escapedCode = escapeHtml(code.trim());
        return `<pre class="bg-zinc-900 border border-zinc-800 rounded-xl p-4 my-3.5 overflow-x-auto text-xs text-amber-200 font-mono"><code class="language-${lang}">${escapedCode}</code></pre>`;
    });

    // 2. Inline Code (`code`)
    html = html.replace(/`([^`\n]+)`/g, '<code class="bg-zinc-800 text-amber-300 px-1.5 py-0.5 rounded-lg font-mono text-xs">$1</code>');

    // 3. Headers (### text)
    html = html.replace(/^\s*###\s+(.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^\s*##\s+(.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^\s*#\s+(.+)$/gm, '<h1>$1</h1>');

    // 4. Bold / Strong (**text**)
    html = html.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>');

    // 5. Italic (*text*)
    html = html.replace(/\*([\s\S]+?)\*/g, '<em class="text-zinc-300 italic">$1</em>');

    // 6. Blockquotes (> text)
    html = html.replace(/^\s*&gt;\s+(.+)$/gm, '<blockquote>$1</blockquote>');

    // 7. Listes à Puces Unordonnées (- ou *)
    html = html.replace(/^\s*[-*]\s+(.+)$/gm, '<li>$1</li>');
    // On englobe les blocs consécutifs de <li> dans un <ul>
    html = html.replace(/(<li>[\s\S]*?<\/li>)+/g, (match) => `<ul class="space-y-1 my-2">${match}</ul>`);

    // 8. Tableaux Markdown (Support Basique)
    // Identifie les lignes contenant au moins un | et des diviseurs |---|
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
            // Ignorer la ligne de diviseur |---|
            if (line.includes('---')) continue;

            const cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
            const tag = tableHtml === "<table>" ? 'th' : 'td';
            tableHtml += `<tr>${cells.map(c => `<${tag}>${c}</${tag}>`).join('')}</tr>`;
            lines[i] = ""; // Vider la ligne traitée
        } else {
            if (insideTable) {
                insideTable = false;
                tableHtml += "</table>";
                lines[i] = tableHtml + "\n" + lines[i];
            }
        }
    }
    html = lines.filter(l => l !== "").join('\n');

    // 9. Paragraphes simples (deux sauts de lignes consécutifs)
    html = html.split('\n\n').map(p => {
        const trimmed = p.trim();
        if (!trimmed) return "";
        // Ne pas entourer de <p> si c'est déjà un conteneur HTML complexe
        if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol') || trimmed.startsWith('<pre') || trimmed.startsWith('<table') || trimmed.startsWith('<div')) {
            return trimmed;
        }
        return `<p>${trimmed}</p>`;
    }).join('\n');

    return html;
}