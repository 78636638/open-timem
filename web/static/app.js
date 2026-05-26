class TiMemChat {
    constructor() {
        this.apiUrl = localStorage.getItem('timem_api_url') || window.location.origin;
        this.userId = localStorage.getItem('timem_user_id') || 'web_user';
        this.userName = localStorage.getItem('timem_user_name') || '访客用户';
        this.saveMemory = localStorage.getItem('timem_save_memory') !== 'false';
        this.llmProvider = localStorage.getItem('timem_llm_provider') || 'minimax';
        this.currentSessionId = null;
        this.chatHistory = [];

        this.initElements();
        this.initEventListeners();
        this.loadSettings();
    }

    initElements() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.clearChatBtn = document.getElementById('clearChatBtn');
        this.settingsBtn = document.getElementById('settingsBtn');
        this.settingsModal = document.getElementById('settingsModal');
        this.closeSettingsBtn = document.getElementById('closeSettingsBtn');
        this.saveSettingsBtn = document.getElementById('saveSettingsBtn');
        this.cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.memoryIndicator = document.getElementById('memoryIndicator');
        this.sessionsList = document.getElementById('sessionsList');
        this.chatStatus = document.getElementById('chatStatus');
    }

    initEventListeners() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
        });

        this.newChatBtn.addEventListener('click', () => this.createNewChat());
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.settingsBtn.addEventListener('click', () => this.openSettings());
        this.closeSettingsBtn.addEventListener('click', () => this.closeSettings());
        this.cancelSettingsBtn.addEventListener('click', () => this.closeSettings());
        this.saveSettingsBtn.addEventListener('click', () => this.saveSettings());

        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) {
                this.closeSettings();
            }
        });
    }

    loadSettings() {
        document.getElementById('settingUserId').value = this.userId;
        document.getElementById('settingUsername').value = this.userName;
        document.getElementById('settingApiUrl').value = this.apiUrl;
        document.getElementById('settingSaveMemory').checked = this.saveMemory;

        document.getElementById('userName').textContent = this.userName;
        this.updateMemoryIndicator();
        this.checkApiStatus();
    }

    updateMemoryIndicator() {
        if (this.saveMemory) {
            this.memoryIndicator.innerHTML = '🧠 记忆已开启';
        } else {
            this.memoryIndicator.innerHTML = '📝 记忆已关闭';
        }
    }

    async checkApiStatus() {
        try {
            const response = await fetch(`${this.apiUrl}/api/v1/health`);
            if (response.ok) {
                this.chatStatus.textContent = '在线';
                this.chatStatus.style.color = '#10B981';
            } else {
                this.chatStatus.textContent = '离线';
                this.chatStatus.style.color = '#EF4444';
            }
        } catch (error) {
            this.chatStatus.textContent = '离线';
            this.chatStatus.style.color = '#EF4444';
        }
    }

    openSettings() {
        this.settingsModal.classList.add('active');
    }

    closeSettings() {
        this.settingsModal.classList.remove('active');
    }

    saveSettings() {
        this.userId = document.getElementById('settingUserId').value || 'web_user';
        this.userName = document.getElementById('settingUsername').value || '访客用户';
        this.apiUrl = document.getElementById('settingApiUrl').value || window.location.origin;
        this.saveMemory = document.getElementById('settingSaveMemory').checked;

        localStorage.setItem('timem_user_id', this.userId);
        localStorage.setItem('timem_user_name', this.userName);
        localStorage.setItem('timem_api_url', this.apiUrl);
        localStorage.setItem('timem_save_memory', this.saveMemory);

        document.getElementById('userName').textContent = this.userName;
        this.updateMemoryIndicator();
        this.checkApiStatus();

        this.closeSettings();
    }

    createNewChat() {
        this.currentSessionId = `session_${Date.now()}`;
        this.chatHistory = [];

        const welcomeMessage = this.chatMessages.querySelector('.message-welcome');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        this.chatMessages.innerHTML = '';
        this.addMessage('assistant', '你好！我是 TiMem AI 助手。有什么我可以帮助你的吗？');

        this.addSessionToList(this.currentSessionId, '新对话');
    }

    addSessionToList(sessionId, title) {
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        sessionItem.dataset.sessionId = sessionId;
        sessionItem.innerHTML = `
            <span class="session-icon">💬</span>
            <span class="session-title">${title}</span>
        `;

        sessionItem.addEventListener('click', () => this.loadSession(sessionId));

        const existingSession = this.sessionsList.querySelector(`[data-session-id="${sessionId}"]`);
        if (existingSession) {
            this.sessionsList.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
            existingSession.classList.add('active');
        } else {
            this.sessionsList.insertBefore(sessionItem, this.sessionsList.firstChild);
            this.sessionsList.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
            sessionItem.classList.add('active');
        }
    }

    loadSession(sessionId) {
        this.currentSessionId = sessionId;
        this.chatMessages.innerHTML = '';
        this.addMessage('assistant', '对话已加载。有什么我可以帮助你的吗？');
    }

    clearChat() {
        if (confirm('确定要清空当前对话吗？')) {
            this.chatMessages.innerHTML = '';
            this.addMessage('assistant', '对话已清空。有什么我可以帮助你的吗？');
        }
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = role === 'user' ? '👤' : '🤖';

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <p>${this.escapeHtml(content).replace(/\n/g, '<br>')}</p>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        return messageDiv;
    }

    addTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        messageDiv.id = 'typingIndicator';

        messageDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        return messageDiv;
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;

        this.addMessage('user', message);
        this.chatHistory.push({ role: 'user', content: message });
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';

        const typingIndicator = this.addTypingIndicator();

        try {
            const response = await fetch(`${this.apiUrl}/api/v1/chat/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId,
                    session_id: this.currentSessionId,
                    save_to_memory: this.saveMemory,
                    llm_provider: this.llmProvider
                })
            });

            this.removeTypingIndicator();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.currentSessionId = data.session_id;
                this.addMessage('assistant', data.response);
                this.chatHistory.push({ role: 'assistant', content: data.response });

                if (data.memories_used > 0) {
                    console.log(`使用了 ${data.memories_used} 条记忆`);
                }
            } else {
                this.addMessage('assistant', '抱歉，发生了错误：' + (data.error || '未知错误'));
            }
        } catch (error) {
            this.removeTypingIndicator();
            console.error('发送消息失败:', error);
            this.addMessage('assistant', '抱歉，无法连接到服务器。请检查网络连接或 API 设置。');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.timemChat = new TiMemChat();
});