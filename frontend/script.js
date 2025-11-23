// LangGraph 研究助手前端 JavaScript (修复版本)
class ResearchAssistant {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.currentStageMessage = null;
        this.messageHistory = [];

        // DOM 元素
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            chatHistory: document.getElementById('chatHistory'),
            progressContainer: document.getElementById('progressContainer'),
            questionInput: document.getElementById('questionInput'),
            sendButton: document.getElementById('sendButton'),
            buttonText: document.querySelector('.button-text'),
            loadingSpinner: document.querySelector('.loading-spinner'),
            charCount: document.getElementById('charCount'),

            // 进度步骤
            stepPlan: document.getElementById('stepPlan'),
            stepResearch: document.getElementById('stepResearch'),
            stepReport: document.getElementById('stepReport')
        };

        this.init();
    }

    init() {
        this.connectWebSocket();
        this.bindEvents();
        this.updateCharCount();
    }

    // WebSocket 连接
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/research`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('已连接', 'connected');
                this.enableInput();
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleServerMessage(data);
                } catch (error) {
                    console.error('解析服务器消息失败:', error);
                }
            };

            this.ws.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus('连接断开', 'disconnected');
                this.disableInput();

                // 3秒后尝试重连
                setTimeout(() => {
                    if (!this.isConnected) {
                        this.updateConnectionStatus('重新连接中...', 'connecting');
                        this.connectWebSocket();
                    }
                }, 3000);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                this.updateConnectionStatus('连接错误', 'error');
            };

        } catch (error) {
            console.error('WebSocket 连接失败:', error);
            this.updateConnectionStatus('连接失败', 'error');
        }
    }

    // 处理服务器消息
    handleServerMessage(data) {
        switch (data.type) {
            case 'start':
                this.handleStartMessage(data);
                break;
            case 'status':
                this.handleStatusMessage(data);
                break;
            case 'plan':
                this.handlePlanMessage(data);
                break;
            case 'research':
                this.handleResearchMessage(data);
                break;
            case 'report':
                this.handleReportMessage(data);
                break;
            case 'complete':
                this.handleCompleteMessage(data);
                break;
            case 'error':
                this.handleErrorMessage(data);
                break;
            case 'node_update':
                this.handleNodeUpdate(data);
                break;
            default:
                console.log('未知消息类型:', data.type);
        }
    }

    // 开始研究
    handleStartMessage(data) {
        this.showProgress();
        this.addStageMessage('start', '🚀', '研究开始', data.content);
    }

    // 状态消息
    handleStatusMessage(data) {
        this.updateStageStatus(data.content);

        // 更新进度条
        switch (data.stage) {
            case 'plan':
                this.updateProgress('plan');
                break;
            case 'research':
                this.updateProgress('research');
                break;
            case 'report':
                this.updateProgress('report');
                break;
        }
    }

    // 研究计划消息 (修复版本)
    handlePlanMessage(data) {
        // 如果当前没有计划阶段的消息框，或者阶段不匹配，创建新的
        if (!this.currentStageMessage || this.currentStageMessage.stage !== 'plan') {
            this.currentStageMessage = this.addStageMessage('plan', '📋', '制定研究计划', '');
        }

        // 追加内容到现有的计划消息框
        this.appendToStageMessage(this.currentStageMessage, data.content);
        this.updateProgress('plan');
    }

    // 研究分析消息 (修复版本)
    handleResearchMessage(data) {
        const stageKey = `research_${data.question_index}`;
        const stageTitle = data.question ? `分析子问题 ${data.question_index}: ${data.question}` : '深度分析';

        // 如果当前没有对应的研究阶段消息框，创建新的
        if (!this.currentStageMessage || this.currentStageMessage.stage !== stageKey) {
            this.currentStageMessage = this.addStageMessage(stageKey, '🔍', stageTitle, '');
        }

        // 追加内容到现有的研究消息框
        this.appendToStageMessage(this.currentStageMessage, data.content);
        this.updateProgress('research');
    }

    // 报告生成消息 (修复版本)
    handleReportMessage(data) {
        // 如果当前没有报告阶段的消息框，创建新的
        if (!this.currentStageMessage || this.currentStageMessage.stage !== 'report') {
            this.currentStageMessage = this.addStageMessage('report', '📄', '生成研究报告', '');
        }

        // 追加内容到现有的报告消息框
        this.appendToStageMessage(this.currentStageMessage, data.content);
        this.updateProgress('report');
    }

    // 完成消息
    handleCompleteMessage(data) {
        this.hideProgress();
        this.enableInput();
        this.showCompletionMessage();
    }

    // 错误消息
    handleErrorMessage(data) {
        this.addMessage('error', data.content);
        this.hideProgress();
        this.enableInput();
    }

    // 节点更新
    handleNodeUpdate(data) {
        this.updateStageStatus(`正在执行: ${this.getStageDisplayName(data.node)}`);
    }

    // 添加用户问题到聊天历史
    addUserQuestion(question) {
        this.addMessage('user', question);

        // 隐藏欢迎消息
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
    }

    // 添加消息
    addMessage(type, content) {
        const template = document.getElementById('messageTemplate');
        const message = template.content.cloneNode(true);

        const messageDiv = message.querySelector('.message');
        messageDiv.classList.add(`message-${type}`);

        const role = message.querySelector('.message-role');
        const time = message.querySelector('.message-time');
        const contentDiv = message.querySelector('.message-content');

        // 设置角色和时间
        if (type === 'user') {
            role.textContent = '👤 用户';
        } else if (type === 'assistant') {
            role.textContent = '🤖 助手';
        } else if (type === 'error') {
            role.textContent = '❌ 错误';
        }

        time.textContent = this.getCurrentTime();
        contentDiv.textContent = content;

        this.elements.chatHistory.appendChild(message);
        this.scrollToBottom();

        // 保存到历史记录
        this.messageHistory.push({ type, content, time: Date.now() });
    }

    // 添加阶段消息 (修复版本)
    addStageMessage(stage, icon, title, initialContent = '') {
        const template = document.getElementById('stageMessageTemplate');
        const stageMessage = template.content.cloneNode(true);

        const stageDiv = stageMessage.querySelector('.stage-message');
        stageDiv.dataset.stage = stage;

        const stageIcon = stageDiv.querySelector('.stage-icon');
        const stageTitle = stageDiv.querySelector('.stage-title');
        const stageStatus = stageDiv.querySelector('.stage-status');
        const contentDiv = stageDiv.querySelector('.stage-content');

        stageIcon.textContent = icon;
        stageTitle.textContent = title;
        stageStatus.textContent = '进行中...';
        if (initialContent) {
            contentDiv.textContent = initialContent;
        }

        this.elements.chatHistory.appendChild(stageMessage);
        this.scrollToBottom();

        return {
            element: stageDiv,
            stage: stage,
            contentDiv: contentDiv,
            statusDiv: stageStatus
        };
    }

    // 追加内容到阶段消息 (修复版本)
    appendToStageMessage(stageMessage, content) {
        if (stageMessage && stageMessage.contentDiv) {
            // 确保内容是字符串，避免undefined或null
            const contentToAdd = content || '';

            // 追加内容到现有文本
            stageMessage.contentDiv.textContent += contentToAdd;

            // 滚动到底部
            this.scrollToBottom();
        }
    }

    // 更新阶段状态
    updateStageStatus(status) {
        if (this.currentStageMessage && this.currentStageMessage.statusDiv) {
            this.currentStageMessage.statusDiv.textContent = status;
        }
    }

    // 显示完成消息
    showCompletionMessage() {
        const completionDiv = document.createElement('div');
        completionDiv.className = 'completion-message';
        completionDiv.innerHTML = `
            <div class="completion-content">
                <span class="completion-icon">✅</span>
                <span class="completion-text">研究完成！如果您还有其他问题，请继续提问。</span>
            </div>
        `;

        this.elements.chatHistory.appendChild(completionDiv);
        this.scrollToBottom();
    }

    // 更新进度条
    updateProgress(stage) {
        // 移除所有活动状态
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.remove('active');
        });

        // 设置当前阶段为活动状态
        switch (stage) {
            case 'plan':
                this.elements.stepPlan.classList.add('active');
                break;
            case 'research':
                this.elements.stepResearch.classList.add('active');
                break;
            case 'report':
                this.elements.stepReport.classList.add('active');
                break;
        }
    }

    // 显示/隐藏进度条
    showProgress() {
        this.elements.progressContainer.style.display = 'block';
    }

    hideProgress() {
        // 延迟隐藏，让用户看到最终状态
        setTimeout(() => {
            this.elements.progressContainer.style.display = 'none';
        }, 2000);
    }

    // 更新连接状态
    updateConnectionStatus(text, status) {
        this.elements.statusText.textContent = text;
        this.elements.statusDot.className = `status-dot status-${status}`;
    }

    // 获取阶段显示名称
    getStageDisplayName(stage) {
        const names = {
            'plan': '研究计划',
            'research': '深度分析',
            'report': '报告生成'
        };
        return names[stage] || stage;
    }

    // 获取当前时间
    getCurrentTime() {
        return new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 滚动到底部
    scrollToBottom() {
        this.elements.chatHistory.scrollTop = this.elements.chatHistory.scrollHeight;
    }

    // 启用/禁用输入
    enableInput() {
        this.elements.questionInput.disabled = false;
        this.elements.sendButton.disabled = false;
        this.elements.buttonText.style.display = 'inline';
        this.elements.loadingSpinner.style.display = 'none';
    }

    disableInput() {
        this.elements.questionInput.disabled = true;
        this.elements.sendButton.disabled = true;
        this.elements.buttonText.style.display = 'none';
        this.elements.loadingSpinner.style.display = 'inline';
    }

    // 发送问题
    sendQuestion() {
        const question = this.elements.questionInput.value.trim();

        if (!question || !this.isConnected) {
            return;
        }

        // 添加用户问题到历史
        this.addUserQuestion(question);

        // 清空输入框
        this.elements.questionInput.value = '';
        this.updateCharCount();

        // 禁用输入
        this.disableInput();

        // 发送到服务器
        this.ws.send(JSON.stringify({
            type: 'question',
            content: question
        }));
    }

    // 更新字符计数
    updateCharCount() {
        const length = this.elements.questionInput.value.length;
        this.elements.charCount.textContent = `${length}/1000`;

        if (length >= 1000) {
            this.elements.charCount.style.color = '#ef4444';
        } else if (length >= 800) {
            this.elements.charCount.style.color = '#f59e0b';
        } else {
            this.elements.charCount.style.color = '#6b7280';
        }
    }

    // 设置示例问题
    setExampleQuestion(question) {
        this.elements.questionInput.value = question;
        this.updateCharCount();
        this.elements.questionInput.focus();
    }

    // 绑定事件
    bindEvents() {
        // 发送按钮
        this.elements.sendButton.addEventListener('click', () => {
            this.sendQuestion();
        });

        // 输入框回车发送
        this.elements.questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendQuestion();
            }
        });

        // 字符计数更新
        this.elements.questionInput.addEventListener('input', () => {
            this.updateCharCount();
        });

        // 自动聚焦输入框
        this.elements.questionInput.focus();
    }
}

// 全局函数供HTML调用
function setExampleQuestion(question) {
    if (window.researchAssistant) {
        window.researchAssistant.setExampleQuestion(question);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.researchAssistant = new ResearchAssistant();
});