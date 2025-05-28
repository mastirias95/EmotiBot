class EmotiBotWebSocket {
    constructor(token) {
        this.socket = null;
        this.token = token;
        this.connected = false;
        this.typingTimeout = null;
        this.previewTimeout = null;
        this.callbacks = {
            onConnect: () => {},
            onDisconnect: () => {},
            onError: () => {},
            onEmotionAnalysis: () => {},
            onEmotionPreview: () => {},
            onTyping: () => {},
            onConnectionStatus: () => {}
        };
    }

    connect() {
        // Initialize socket connection with authentication token
        this.socket = io(window.location.origin, {
            auth: {
                token: this.token
            },
            query: {
                token: this.token
            },
            transports: ['websocket', 'polling']
        });

        // Set up event listeners
        this.socket.on('connect', () => {
            console.log('Connected to WebSocket server');
            this.connected = true;
            this.callbacks.onConnect();
            this.callbacks.onConnectionStatus('connected');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from WebSocket server');
            this.connected = false;
            this.callbacks.onDisconnect();
            this.callbacks.onConnectionStatus('disconnected');
        });

        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
            this.callbacks.onError(error);
        });

        this.socket.on('emotion_analysis_response', (data) => {
            console.log('Received emotion analysis:', data);
            this.callbacks.onEmotionAnalysis(data);
        });

        this.socket.on('emotion_preview', (data) => {
            console.log('Received emotion preview:', data);
            this.callbacks.onEmotionPreview(data);
        });

        this.socket.on('user_typing', (data) => {
            console.log('User typing status:', data);
            this.callbacks.onTyping(data);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.callbacks.onError(error);
            this.callbacks.onConnectionStatus('error');
        });

        this.socket.on('connection_response', (data) => {
            console.log('Connection response:', data);
        });

        this.socket.on('room_joined', (data) => {
            console.log('Joined room:', data);
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }

    analyzeEmotion(text) {
        if (!this.connected) {
            throw new Error('Not connected to WebSocket server');
        }
        this.socket.emit('analyze_emotion', { text });
    }

    sendLiveEmotionPreview(text) {
        if (!this.connected) {
            return;
        }

        // Debounce the preview requests
        if (this.previewTimeout) {
            clearTimeout(this.previewTimeout);
        }

        this.previewTimeout = setTimeout(() => {
            this.socket.emit('live_emotion_preview', { text });
        }, 300); // 300ms debounce
    }

    setTyping(isTyping) {
        if (!this.connected) {
            return;
        }

        // Clear existing timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        // Emit typing status
        this.socket.emit('typing', { typing: isTyping });

        // Automatically clear typing status after 2 seconds of no updates
        if (isTyping) {
            this.typingTimeout = setTimeout(() => {
                this.socket.emit('typing', { typing: false });
            }, 2000);
        }
    }

    joinRoom(roomName) {
        if (!this.connected) {
            return;
        }
        this.socket.emit('join_room', { room: roomName });
    }

    // Callback setters
    onConnect(callback) {
        this.callbacks.onConnect = callback;
    }

    onDisconnect(callback) {
        this.callbacks.onDisconnect = callback;
    }

    onError(callback) {
        this.callbacks.onError = callback;
    }

    onEmotionAnalysis(callback) {
        this.callbacks.onEmotionAnalysis = callback;
    }

    onEmotionPreview(callback) {
        this.callbacks.onEmotionPreview = callback;
    }

    onTyping(callback) {
        this.callbacks.onTyping = callback;
    }

    onConnectionStatus(callback) {
        this.callbacks.onConnectionStatus = callback;
    }

    // Utility methods
    isConnected() {
        return this.connected;
    }

    getConnectionStatus() {
        return this.connected ? 'connected' : 'disconnected';
    }
} 