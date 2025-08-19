// DOM Elements
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const chatMessages = document.getElementById("chatMessages");
const charCount = document.getElementById("charCount");
const aiStatus = document.getElementById("aiStatus");
const welcomeSection = document.getElementById("welcomeSection");
const questionChips = document.querySelectorAll(".question-chip");
const healthAlert = document.getElementById("healthAlert");
const healthAlertText = document.getElementById("healthAlertText");
const typingIndicator = document.getElementById("typingIndicator");
const loadingOverlay = document.getElementById("loadingOverlay");
const errorModal = document.getElementById("errorModal");
const errorMessage = document.getElementById("errorMessage");
const refreshDataBtn = document.getElementById("refreshDataBtn");
const clearChatBtn = document.getElementById("clearChatBtn");
const showStatsBtn = document.getElementById("showStatsBtn");
const statsSidebar = document.getElementById("statsSidebar");
const toggleStatsBtn = document.getElementById("toggleStatsBtn");
const inputSuggestions = document.getElementById("inputSuggestions");
const suggestionBtns = document.querySelectorAll(".suggestion-btn");

// Chat state
let isTyping = false;
let messageCount = 0;
let chatbotData = null;
let isStatsVisible = false;

// Initialize chatbot (single init)
document.addEventListener("DOMContentLoaded", async function () {
  setupEventListeners();
  updateCharCount();
  await checkChatbotStatus();
  await loadAnalytics();
  initializeChat();
});

// Event Listeners
function setupEventListeners() {
  // Input events
  chatInput.addEventListener("input", handleInputChange);
  chatInput.addEventListener("keypress", handleKeyPress);
  chatInput.addEventListener("focus", showInputSuggestions);
  chatInput.addEventListener("blur", hideInputSuggestions);

  // Send button
  sendBtn.addEventListener("click", sendMessage);

  // Question chips
  questionChips.forEach((chip) => {
    chip.addEventListener("click", function () {
      const question = this.getAttribute("data-question");
      chatInput.value = question;
      updateCharCount();
      sendMessage();
    });
  });

  // Suggestion buttons
  suggestionBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      const suggestion = this.getAttribute("data-suggestion");
      chatInput.value = suggestion;
      updateCharCount();
      sendMessage();
    });
  });

  // Header buttons
  if (refreshDataBtn) {
    refreshDataBtn.addEventListener("click", refreshData);
  }

  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", clearChat);
  }

  // Stats sidebar
  if (showStatsBtn) {
    showStatsBtn.addEventListener("click", toggleStats);
  }

  if (toggleStatsBtn) {
    toggleStatsBtn.addEventListener("click", toggleStats);
  }

  // Error modal
  const closeErrorModal = document.getElementById("closeErrorModal");
  const dismissErrorBtn = document.getElementById("dismissErrorBtn");
  const retryBtn = document.getElementById("retryBtn");

  if (closeErrorModal) {
    closeErrorModal.addEventListener("click", hideErrorModal);
  }

  if (dismissErrorBtn) {
    dismissErrorBtn.addEventListener("click", hideErrorModal);
  }

  if (retryBtn) {
    retryBtn.addEventListener("click", () => {
      hideErrorModal();
      checkChatbotStatus();
    });
  }
}

// Handle input changes
function handleInputChange() {
  updateCharCount();
  updateSendButton();
}

// Handle key press
function handleKeyPress(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// Update character count
function updateCharCount() {
  const count = chatInput.value.length;
  charCount.textContent = `${count}/500`;

  if (count > 400) {
    charCount.style.color = "var(--error-color)";
  } else {
    charCount.style.color = "var(--text-muted)";
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
    welcomeSection.style.display = "none";
  }

  // Hide input suggestions
  hideInputSuggestions();

  // Add user message
  addMessage(message, "user");

  // Clear input
  chatInput.value = "";
  updateCharCount();
  updateSendButton();

  // Show typing indicator
  showTypingIndicator();

  try {
    const response = await fetch("/api/chatbot/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    hideTypingIndicator();

    if (data.success) {
      addMessage(data.response, "ai");
    } else {
      addMessage(
        data.response || "I apologize, but I could not process your request.",
        "ai"
      );
    }
  } catch (error) {
    hideTypingIndicator();
    addMessage(
      "Sorry, I encountered an error while processing your request. Please try again.",
      "ai"
    );
    console.error("Chat error:", error);
    showErrorModal(
      "Failed to send message. Please check your connection and try again."
    );
  }

  updateAIStatus();
}

// Add message to chat
function addMessage(text, sender) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";

  if (sender === "user") {
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

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  // Format message (preserve line breaks, format JSON, etc.)
  bubble.innerHTML = formatMessage(text);

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  bubble.appendChild(time);
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(bubble);

  chatMessages.appendChild(messageDiv);

  // Add copy button for JSON responses
  addCopyButton(messageDiv);

  scrollToBottom();

  messageCount++;
}

// Check chatbot status and data availability
async function checkChatbotStatus() {
  try {
    showLoadingOverlay();
    const response = await fetch("/api/chatbot/status");
    const data = await response.json();

    if (data.status === "active" && data.data_available) {
      healthAlert.style.display = "none";
      aiStatus.textContent = "Ready to analyze your transactions";
      chatInput.disabled = false;
      updateSendButton();
      chatbotData = data;
    } else {
      healthAlert.style.display = "block";
      healthAlertText.textContent =
        data.error ||
        "Transaction data not found. Please upload and process your bank statement first.";
      aiStatus.textContent = "Data unavailable";
      chatInput.disabled = true;
      sendBtn.disabled = true;
    }
  } catch (error) {
    console.error("Status check error:", error);
    healthAlert.style.display = "block";
    healthAlertText.textContent = "Unable to reach chatbot service.";
    aiStatus.textContent = "Service unreachable";
    chatInput.disabled = true;
    sendBtn.disabled = true;
    showErrorModal(
      "Failed to connect to the chatbot service. Please refresh the page and try again."
    );
  } finally {
    hideLoadingOverlay();
  }
}

// Load analytics data for stats sidebar
async function loadAnalytics() {
  try {
    const response = await fetch("/api/chatbot/analytics");
    
    if (!response.ok) {
      console.error("Analytics response not ok:", response.status, response.statusText);
      // Show default values
      updateStatsDisplay({
        summary: {
          total_transactions: 0,
          total_debits: 0,
          total_credits: 0,
          current_balance: 0
        }
      });
      return;
    }
    
    const data = await response.json();

    // Always update stats display, even if data is not successful
    if (data.analytics) {
      updateStatsDisplay(data.analytics);
    } else {
      console.warn("Analytics data not available:", data.message || "Unknown reason");
      // Show default values
      updateStatsDisplay({
        summary: {
          total_transactions: 0,
          total_debits: 0,
          total_credits: 0,
          current_balance: 0
        }
      });
    }
  } catch (error) {
    console.error("Analytics load error:", error);
    // Show default values on error
    updateStatsDisplay({
      summary: {
        total_transactions: 0,
        total_debits: 0,
        total_credits: 0,
        current_balance: 0
      }
    });
  }
}

// Format message content
function formatMessage(text) {
  // Try to detect and format JSON
  try {
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const jsonPart = JSON.parse(jsonMatch[0]);
      const formattedJson = JSON.stringify(jsonPart, null, 2);
      return text.replace(
        jsonMatch[0],
        `<pre class="json-response">${formattedJson}</pre>`
      );
    }
  } catch (e) {
    // Not JSON, continue with regular formatting
  }

  // Format regular text (preserve line breaks)
  return text.replace(/\n/g, "<br>");
}

// Show typing indicator
function showTypingIndicator() {
  isTyping = true;
  updateSendButton();
  updateAIStatus("Thinking...");

  if (typingIndicator) {
    typingIndicator.style.display = "flex";
    scrollToBottom();
  }
}

// Hide typing indicator
function hideTypingIndicator() {
  isTyping = false;
  updateSendButton();
  updateAIStatus("Ready to analyze your transactions");

  if (typingIndicator) {
    typingIndicator.style.display = "none";
  }
}

// Update AI status
function updateAIStatus(status = "Ready to analyze your transactions") {
  aiStatus.textContent = status;
}

// Scroll to bottom of chat
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove mock fallback now that backend endpoints exist

// Enhanced error handling
window.addEventListener("error", function (e) {
  console.error("Global error:", e.error);
  if (isTyping) {
    hideTypingIndicator();
    addMessage("Sorry, something went wrong. Please try again.", "ai");
  }
});

// Prevent form submission on enter
document.addEventListener("keydown", function (e) {
  if (e.target === chatInput && e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
  }
});

// Auto-resize chat input (if we decide to use textarea later)
function autoResizeInput() {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
}

// Copy message functionality (for JSON responses)
function addCopyButton(messageDiv) {
  const jsonElement = messageDiv.querySelector(".json-response");
  if (jsonElement) {
    const copyBtn = document.createElement("button");
    copyBtn.className = "copy-btn";
    copyBtn.title = "Copy to clipboard";
    copyBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
        `;

    copyBtn.onclick = function () {
      navigator.clipboard
        .writeText(jsonElement.textContent)
        .then(() => {
          copyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                        <polyline points="20,6 9,17 4,12"/>
                    </svg>
                `;
          copyBtn.title = "Copied!";
          setTimeout(() => {
            copyBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                    `;
            copyBtn.title = "Copy to clipboard";
          }, 2000);
        })
        .catch(() => {
          // Fallback for browsers that don't support clipboard API
          try {
            const textArea = document.createElement("textarea");
            textArea.value = jsonElement.textContent;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand("copy");
            document.body.removeChild(textArea);

            copyBtn.innerHTML = `
                      <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                          <polyline points="20,6 9,17 4,12"/>
                      </svg>
                  `;
            copyBtn.title = "Copied!";
            setTimeout(() => {
              copyBtn.innerHTML = `
                          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2 2v1"/>
                          </svg>
                      `;
              copyBtn.title = "Copy to clipboard";
            }, 2000);
          } catch (err) {
            console.warn('Copy to clipboard failed:', err);
            copyBtn.title = "Copy failed";
          }
        });
    };

    jsonElement.appendChild(copyBtn);
  }
}

// Initialize chat with welcome message from AI
function initializeChat() {
  if (chatbotData && chatbotData.data_available) {
    setTimeout(() => {
      const welcomeMsg = `Hello! I'm your Financial AI Assistant. I've analyzed your transaction data and found ${chatbotData.total_transactions} transactions. I'm ready to answer any questions you have about your spending patterns, income, or financial habits. What would you like to know?`;
      addMessage(welcomeMsg, "ai");
    }, 1000);
  }
}

// Stats sidebar functions
function toggleStats() {
  isStatsVisible = !isStatsVisible;
  if (isStatsVisible) {
    statsSidebar.classList.add("active");
  } else {
    statsSidebar.classList.remove("active");
  }
}

function updateStatsDisplay(analytics) {
  const totalSpent = document.getElementById("totalSpent");
  const totalReceived = document.getElementById("totalReceived");
  const currentBalance = document.getElementById("currentBalance");
  const totalTransactions = document.getElementById("totalTransactions");

  if (analytics && analytics.summary) {
    if (totalSpent) {
      const spentValue = Math.abs(analytics.summary.total_debits || 0);
      totalSpent.textContent = `₹${formatNumber(spentValue)}`;
    }
    
    if (totalReceived) {
      const receivedValue = analytics.summary.total_credits || 0;
      totalReceived.textContent = `₹${formatNumber(receivedValue)}`;
    }
    
    if (currentBalance) {
      const balanceValue = analytics.summary.current_balance || 0;
      currentBalance.textContent = `₹${formatNumber(balanceValue)}`;
    }
    
    if (totalTransactions) {
      const transactionCount = analytics.summary.total_transactions || 0;
      totalTransactions.textContent = formatNumber(transactionCount);
    }
  } else {
    // Set default values when no analytics available
    if (totalSpent) totalSpent.textContent = "₹0";
    if (totalReceived) totalReceived.textContent = "₹0";
    if (currentBalance) currentBalance.textContent = "₹0";
    if (totalTransactions) totalTransactions.textContent = "0";
  }
}

// Refresh data function
async function refreshData() {
  try {
    showLoadingOverlay();
    const response = await fetch("/api/chatbot/reload-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await response.json();

    if (data.success) {
      await checkChatbotStatus();
      await loadAnalytics();
      addMessage(
        "Data refreshed successfully! I now have access to your latest transaction data.",
        "ai"
      );
    } else {
      showErrorModal("Failed to refresh data. Please try again.");
    }
  } catch (error) {
    console.error("Refresh data error:", error);
    showErrorModal(
      "Failed to refresh data. Please check your connection and try again."
    );
  } finally {
    hideLoadingOverlay();
  }
}

// Clear chat function
function clearChat() {
  chatMessages.innerHTML = "";
  messageCount = 0;
  welcomeSection.style.display = "block";
  initializeChat();
}

// Input suggestions functions
function showInputSuggestions() {
  if (inputSuggestions && messageCount > 0) {
    inputSuggestions.style.display = "flex";
  }
}

function hideInputSuggestions() {
  if (inputSuggestions) {
    inputSuggestions.style.display = "none";
  }
}

// Loading overlay functions
function showLoadingOverlay() {
  if (loadingOverlay) {
    loadingOverlay.style.display = "flex";
  }
}

function hideLoadingOverlay() {
  if (loadingOverlay) {
    loadingOverlay.style.display = "none";
  }
}

// Error modal functions
function showErrorModal(message) {
  if (errorModal && errorMessage) {
    errorMessage.textContent = message;
    errorModal.style.display = "flex";
  }
}

function hideErrorModal() {
  if (errorModal) {
    errorModal.style.display = "none";
  }
}

// Utility functions
function formatNumber(num) {
  if (num >= 10000000) {
    return (num / 10000000).toFixed(1) + "Cr";
  } else if (num >= 100000) {
    return (num / 100000).toFixed(1) + "L";
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toLocaleString("en-IN");
}
