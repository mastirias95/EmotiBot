/**
 * EmotiBot - Main JavaScript
 * Handles the chat interface and emotion detection
 */

// DOM Elements
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const messagesContainer = document.getElementById('messages');
const avatar = document.getElementById('avatar');
const emotionLabel = document.getElementById('emotion-label');
const currentEmotion = document.getElementById('current-emotion');
const confidenceElement = document.getElementById('confidence');
const polarityElement = document.getElementById('polarity');
const subjectivityElement = document.getElementById('subjectivity');

// Bot responses based on emotions
const botResponses = {
    'happy': [
        "You seem happy! That's great to hear!",
        "Your positive energy is contagious!",
        "I'm glad things are going well for you!"
    ],
    'sad': [
        "I'm sorry to hear you're feeling down.",
        "It's okay to feel sad sometimes. Is there anything I can help with?",
        "I'm here for you if you need someone to talk to."
    ],
    'angry': [
        "I understand you're frustrated right now.",
        "Let's take a deep breath together.",
        "I see you're upset. Would you like to talk about what's bothering you?"
    ],
    'surprised': [
        "Wow! That is surprising!",
        "I didn't expect that either!",
        "That's quite a revelation!"
    ],
    'fearful': [
        "It's okay to be worried, but remember you're not alone.",
        "I understand that can be scary. Let's think about it together.",
        "What specifically are you concerned about?"
    ],
    'neutral': [
        "Thanks for sharing that with me.",
        "I understand what you're saying.",
        "Tell me more about that."
    ]
};

// Initialize the chat
document.addEventListener('DOMContentLoaded', () => {
    // Focus on input field
    messageInput.focus();
    
    // Add event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});

/**
 * Send a user message and get response
 */
function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Clear input field
    messageInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to API for emotion analysis
    analyzeEmotion(message)
        .then(response => {
            // Update avatar and emotion stats
            updateEmotionDisplay(response);
            
            // Generate bot response based on emotion
            const botMessage = generateBotResponse(response.emotion);
            
            // Remove typing indicator and add bot response
            removeTypingIndicator();
            addMessage(botMessage, 'bot');
        })
        .catch(error => {
            console.error('Error analyzing emotion:', error);
            removeTypingIndicator();
            addMessage("I'm sorry, I couldn't process that. Could you try again?", 'bot');
        });
}

/**
 * Add a message to the chat
 * @param {string} text - Message text
 * @param {string} sender - 'user' or 'bot'
 */
function addMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    
    const contentElement = document.createElement('div');
    contentElement.classList.add('message-content');
    contentElement.textContent = text;
    
    messageElement.appendChild(contentElement);
    messagesContainer.appendChild(messageElement);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const typingElement = document.createElement('div');
    typingElement.classList.add('message', 'bot', 'typing-indicator');
    
    const contentElement = document.createElement('div');
    contentElement.classList.add('message-content');
    contentElement.textContent = 'Typing...';
    
    typingElement.appendChild(contentElement);
    messagesContainer.appendChild(typingElement);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

/**
 * Analyze emotion using the API
 * @param {string} text - Text to analyze
 * @returns {Promise} - Emotion analysis result
 */
async function analyzeEmotion(text) {
    try {
        // Prepare headers
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add auth token if available
        if (window.authToken) {
            headers['Authorization'] = `Bearer ${window.authToken}`;
        }
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ text })
        });
        
        if (!response.ok) {
            throw new Error('API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error calling API:', error);
        throw error;
    }
}

/**
 * Update the avatar and emotion display
 * @param {Object} emotionData - Emotion analysis result
 */
function updateEmotionDisplay(emotionData) {
    const { emotion, confidence, polarity, subjectivity } = emotionData;
    
    // Update avatar
    avatar.className = 'avatar ' + emotion;
    
    // Update emotion label
    emotionLabel.textContent = emotion;
    
    // Update emotion stats
    currentEmotion.textContent = emotion;
    confidenceElement.textContent = Math.round(confidence * 100) + '%';
    polarityElement.textContent = polarity.toFixed(2);
    subjectivityElement.textContent = subjectivity.toFixed(2);
}

/**
 * Generate a bot response based on detected emotion
 * @param {string} emotion - Detected emotion
 * @returns {string} - Bot response
 */
function generateBotResponse(emotion) {
    const responses = botResponses[emotion] || botResponses.neutral;
    const randomIndex = Math.floor(Math.random() * responses.length);
    return responses[randomIndex];
} 