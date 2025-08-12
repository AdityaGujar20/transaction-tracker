// DOM Elements
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const charCount = document.getElementById('charCount');
const aiStatus = document.getElementById('aiStatus');
const welcomeSection = document.getElementById('welcomeSection');
const questionChips = document.querySelectorAll('.question-chip');

// Chat state
let isTyping = false;
let messageCount = 0;

// Initialize chatbot
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    updateCharCount();
    console.log('Financial AI Assistant initialized successfully!');
});

// Event Listeners
function setupEventListeners() {
    // Input events
    chatInput.addEventListener('input', handleInputChange);
    chatInput.addEventListener('keypress', handleKeyPress);
    
    // Send button
    sendBtn.addEventListener('click', sendMessage);
    
    // Question chips
    questionChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const question = this.getAttribute('data-question');
            chatInput.value = question;
            updateCharCount();
            sendMessage();
        });
    });
}

// Handle input changes
function handleInputChange() {
    updateCharCount();
    updateSendButton();
}

// Handle key press
function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// Update character count
function updateCharCount() {
    const count = chatInput.value.length;
    charCount.textContent = `${count}/500`;
    
    if (count > 400) {
        charCount.style.color = 'var(--error-color)';
    } else {
        charCount.style.color = 'var(--text-muted)';
    }
}

// Update send button state
function updateSendButton() {
    const hasText = chatInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || isTyping;
}

// Send message
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isTyping) return;
    
    // Hide welcome section on first message
    if (messageCount === 0) {
        welcomeSection.style.display = 'none';
    }
    
    // Add user message
    addMessage(message, 'user');
    
    // Clear input
    chatInput.value = '';
    updateCharCount();
    updateSendButton();
    
    // Show typing indicator
    showTypingIndicator();
    
    // Simulate AI thinking time
    setTimeout(async () => {
        try {
            // Try to send to backend first
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add AI response
            addMessage(data.response || data.message || 'I apologize, but I could not process your request.', 'ai');
            
        } catch (error) {
            console.error('Chat error:', error);
            console.log('Using mock response as fallback...');
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Use mock response as fallback
            const mockResponse = getMockResponse(message);
            addMessage(mockResponse, 'ai');
        }
        
        // Update AI status
        updateAIStatus();
    }, 1000 + Math.random() * 2000); // Random delay between 1-3 seconds for realistic feel
}

// Add message to chat
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    if (sender === 'user') {
        avatar.innerHTML = `
            <svg viewBox="0 0 24 24">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
            </svg>
        `;
    } else {
        avatar.innerHTML = `
            <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="3"/>
                <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"/>
            </svg>
        `;
    }
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Format message (preserve line breaks, format JSON, etc.)
    bubble.innerHTML = formatMessage(text);
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    bubble.appendChild(time);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(bubble);
    
    chatMessages.appendChild(messageDiv);
    
    // Add copy button for JSON responses
    addCopyButton(messageDiv);
    
    scrollToBottom();
    
    messageCount++;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    updateCharCount();
    
    // Initialize with a welcome message after a short delay
    initializeChat();
    
    console.log('Financial AI Assistant initialized successfully!');
});

// Format message content
function formatMessage(text) {
    // Try to detect and format JSON
    try {
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            const jsonPart = JSON.parse(jsonMatch[0]);
            const formattedJson = JSON.stringify(jsonPart, null, 2);
            return text.replace(jsonMatch[0], `<pre class="json-response">${formattedJson}</pre>`);
        }
    } catch (e) {
        // Not JSON, continue with regular formatting
    }
    
    // Format regular text (preserve line breaks)
    return text.replace(/\n/g, '<br>');
}

// Show typing indicator
function showTypingIndicator() {
    isTyping = true;
    updateSendButton();
    updateAIStatus('Thinking...');
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai typing-message';
    typingDiv.id = 'typingIndicator';
    
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="3"/>
                <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"/>
            </svg>
        </div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    scrollToBottom();
}

// Hide typing indicator
function hideTypingIndicator() {
    isTyping = false;
    updateSendButton();
    updateAIStatus('Ready to analyze your transactions');
    
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Update AI status
function updateAIStatus(status = 'Ready to analyze your transactions') {
    aiStatus.textContent = status;
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Mock responses for testing (remove when backend is ready)
const mockResponses = {
    "what's my total spending": "Based on your transaction data, your total spending is $2,450.75 across all categories.",
    "which category do i spend most on": "Your highest spending category is Food & Dining with $890.25 (36.3% of total expenses).",
    "what was my highest single expense": "Your highest single transaction was $285.00 at Electronics Store on March 15th.",
    "show me my income vs expenses": "Income: $3,200.00\nExpenses: $2,450.75\nNet Savings: $749.25 (23.4% savings rate)",
    "default": "I can help you analyze your financial data. Try asking about your spending patterns, categories, income, or specific transactions!"
};

// Get mock response (temporary function)
function getMockResponse(message) {
    const lowerMessage = message.toLowerCase();
    
    for (const [key, response] of Object.entries(mockResponses)) {
        if (key !== 'default' && lowerMessage.includes(key.toLowerCase())) {
            return response;
        }
    }
    
    return mockResponses.default;
}

// Enhanced error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    if (isTyping) {
        hideTypingIndicator();
        addMessage('Sorry, something went wrong. Please try again.', 'ai');
    }
});

// Prevent form submission on enter
document.addEventListener('keydown', function(e) {
    if (e.target === chatInput && e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
    }
});

// Auto-resize chat input (if we decide to use textarea later)
function autoResizeInput() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
}

// Copy message functionality (for JSON responses)
function addCopyButton(messageDiv) {
    const jsonElement = messageDiv.querySelector('.json-response');
    if (jsonElement) {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
        `;
        
        copyBtn.onclick = function() {
            navigator.clipboard.writeText(jsonElement.textContent).then(() => {
                copyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="14" height="14">
                        <polyline points="20,6 9,17 4,12"/>
                    </svg>
                `;
                setTimeout(() => {
                    copyBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="14" height="14">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                    `;
                }, 2000);
            });
        };
        
        jsonElement.style.position = 'relative';
        jsonElement.appendChild(copyBtn);
    }
}

// Initialize chat with welcome message from AI
function initializeChat() {
    setTimeout(() => {
        addMessage("Hello! I'm your Financial AI Assistant. I've analyzed your transaction data and I'm ready to answer any questions you have about your spending patterns, income, or financial habits. What would you like to know?", 'ai');
    }, 1000);
}