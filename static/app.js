// Antigravity Ultra - Frontend Application

class AntigravityUltra {
    constructor() {
        this.ws = null;
        this.conversationId = null;
        this.isStreaming = false;
        this.currentMessageEl = null;

        this.init();
    }

    init() {
        this.connectWebSocket();
        this.loadConversations();
        this.setupEventListeners();
        this.autoResizeTextarea();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateStatus('Connecté', 'ready');
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateStatus('Déconnecté', 'error');
            // Reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Erreur de connexion', 'error');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'conversation_id':
                this.conversationId = data.conversation_id;
                break;

            case 'chunk':
                this.appendToCurrentMessage(data.content);
                break;

            case 'tool_call':
                this.showToolCall(data.name, data.arguments);
                break;

            case 'tool_result':
                this.showToolResult(data.name, data.result);
                break;

            case 'status':
                this.updateStatus(this.getStatusText(data.status), data.status);
                break;

            case 'done':
                this.finishMessage();
                break;

            case 'error':
                this.showError(data.message);
                break;
        }
    }

    getStatusText(status) {
        const statusTexts = {
            'thinking': 'Réflexion...',
            'tool_calling': 'Utilisation d\'outils...',
            'ready': 'Prêt'
        };
        return statusTexts[status] || status;
    }

    updateStatus(text, status) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = indicator.querySelector('.status-text');
        statusText.textContent = text;

        indicator.className = 'status-indicator';
        if (status === 'thinking' || status === 'tool_calling') {
            indicator.classList.add('thinking');
        }
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message || this.isStreaming) return;

        // Clear input
        input.value = '';
        input.style.height = 'auto';

        // Hide welcome message
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        // Add user message
        this.addMessage('user', message);

        // Create assistant message placeholder
        this.createAssistantMessage();

        // Send to server
        this.isStreaming = true;
        this.updateStatus('Réflexion...', 'thinking');

        const model = document.getElementById('modelSelect').value;
        const useAgent = document.getElementById('agentMode').checked;

        this.ws.send(JSON.stringify({
            message: message,
            conversation_id: this.conversationId,
            model: model,
            use_agent: useAgent
        }));
    }

    addMessage(role, content) {
        const container = document.getElementById('messagesContainer');

        const messageEl = document.createElement('div');
        messageEl.className = `message ${role}`;

        const avatar = role === 'assistant' ? '⚡' : '👤';

        messageEl.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${this.renderMarkdown(content)}</div>
        `;

        container.appendChild(messageEl);
        this.scrollToBottom();
    }

    createAssistantMessage() {
        const container = document.getElementById('messagesContainer');

        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant';
        messageEl.innerHTML = `
            <div class="message-avatar">⚡</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;

        container.appendChild(messageEl);
        this.currentMessageEl = messageEl.querySelector('.message-content');
        this.currentMessageContent = '';
        this.scrollToBottom();
    }

    appendToCurrentMessage(content) {
        if (!this.currentMessageEl) return;

        // Remove typing indicator on first content
        const typing = this.currentMessageEl.querySelector('.typing-indicator');
        if (typing) typing.remove();

        this.currentMessageContent += content;
        this.currentMessageEl.innerHTML = this.renderMarkdown(this.currentMessageContent);
        this.scrollToBottom();
    }

    showToolCall(name, args) {
        if (!this.currentMessageEl) return;

        const toolEl = document.createElement('div');
        toolEl.className = 'tool-call';
        toolEl.innerHTML = `
            <div class="tool-call-header">
                <span class="tool-call-icon">🔧</span>
                <span>${name}</span>
            </div>
            <div class="tool-result" id="tool-${Date.now()}">
                Arguments: ${JSON.stringify(args, null, 2)}
            </div>
        `;

        this.currentMessageEl.appendChild(toolEl);
        this.scrollToBottom();
    }

    showToolResult(name, result) {
        // Find the last tool call and update it
        const toolCalls = this.currentMessageEl.querySelectorAll('.tool-call');
        if (toolCalls.length > 0) {
            const lastTool = toolCalls[toolCalls.length - 1];
            const resultEl = lastTool.querySelector('.tool-result');
            if (resultEl) {
                resultEl.textContent = result;
            }
        }
        this.scrollToBottom();
    }

    finishMessage() {
        this.isStreaming = false;
        this.currentMessageEl = null;
        this.updateStatus('Prêt', 'ready');

        // Highlight code blocks
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

        // Refresh conversations list
        this.loadConversations();
    }

    showError(message) {
        this.isStreaming = false;
        if (this.currentMessageEl) {
            this.currentMessageEl.innerHTML = `<div style="color: var(--error);">Erreur: ${message}</div>`;
        }
        this.updateStatus('Erreur', 'error');
    }

    renderMarkdown(text) {
        if (!text) return '';

        // Remove tool blocks from display
        text = text.replace(/```tool\n[\s\S]*?\n```/g, '');

        // Use marked for markdown rendering
        try {
            return marked.parse(text);
        } catch (e) {
            return text.replace(/\n/g, '<br>');
        }
    }

    scrollToBottom() {
        const container = document.getElementById('messagesContainer');
        container.scrollTop = container.scrollHeight;
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const data = await response.json();

            const list = document.getElementById('conversationsList');
            list.innerHTML = '';

            data.conversations.forEach(conv => {
                const item = document.createElement('div');
                item.className = 'conversation-item';
                if (conv.id === this.conversationId) {
                    item.classList.add('active');
                }

                item.innerHTML = `
                    <span class="conv-icon">💬</span>
                    <span class="conv-title">${conv.title || 'Conversation'}</span>
                `;

                item.onclick = () => this.loadConversation(conv.id);
                list.appendChild(item);
            });
        } catch (e) {
            console.error('Failed to load conversations:', e);
        }
    }

    async loadConversation(convId) {
        try {
            const response = await fetch(`/api/conversations/${convId}`);
            const data = await response.json();

            this.conversationId = convId;

            // Clear messages
            const container = document.getElementById('messagesContainer');
            container.innerHTML = '';

            // Add messages
            data.messages.forEach(msg => {
                this.addMessage(msg.role, msg.content);
            });

            this.loadConversations();
        } catch (e) {
            console.error('Failed to load conversation:', e);
        }
    }

    newConversation() {
        this.conversationId = null;

        const container = document.getElementById('messagesContainer');
        container.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">🚀</div>
                <h2>Bienvenue sur Antigravity Ultra</h2>
                <p>IA autonome ultra-performante avec capacités d'agent</p>
                <div class="capabilities">
                    <div class="capability">
                        <span class="cap-icon">🔍</span>
                        <span>Recherche Web</span>
                    </div>
                    <div class="capability">
                        <span class="cap-icon">📁</span>
                        <span>Fichiers</span>
                    </div>
                    <div class="capability">
                        <span class="cap-icon">💻</span>
                        <span>Code Python</span>
                    </div>
                    <div class="capability">
                        <span class="cap-icon">🧠</span>
                        <span>Mémoire</span>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('chatTitle').textContent = 'Nouvelle conversation';
        this.loadConversations();
    }

    setupEventListeners() {
        // Auto-resize textarea
        const textarea = document.getElementById('messageInput');
        textarea.addEventListener('input', () => this.autoResizeTextarea());
    }

    autoResizeTextarea() {
        const textarea = document.getElementById('messageInput');
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
}

// Global functions for HTML onclick handlers
function sendMessage() {
    app.sendMessage();
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function newConversation() {
    app.newConversation();
}

// Initialize app
const app = new AntigravityUltra();
