/**
 * WebSocket Service for Smart Home Energy Monitoring
 * Handles real-time communication, chat, and live energy updates
 */

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const Redis = require('redis');
const jwt = require('jsonwebtoken');
const cors = require('cors');
const helmet = require('helmet');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

// Configuration
const PORT = process.env.PORT || 8003;
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8000';
const TELEMETRY_SERVICE_URL = process.env.TELEMETRY_SERVICE_URL || 'http://localhost:8001';
const JWT_SECRET = process.env.JWT_SECRET || 'your-super-secret-jwt-key-change-in-production';

// Initialize Express app
const app = express();
const server = http.createServer(app);

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Initialize WebSocket server
const wss = new WebSocket.Server({ server });

// Redis client
let redisClient = null;

// Connection management
const connections = new Map(); // Map to store active connections
const userRooms = new Map(); // Map to store user room subscriptions

// Message types
const MESSAGE_TYPES = {
    CHAT: 'chat',
    ENERGY_UPDATE: 'energy_update',
    DEVICE_STATUS: 'device_status',
    SYSTEM_NOTIFICATION: 'system_notification',
    AUTHENTICATION: 'authentication',
    SUBSCRIBE: 'subscribe',
    UNSUBSCRIBE: 'unsubscribe'
};

// Initialize Redis connection
async function initializeRedis() {
    try {
        redisClient = Redis.createClient({ url: REDIS_URL });
        await redisClient.connect();
        console.log('✅ Redis connected successfully');
        
        // Subscribe to Redis channels for real-time updates
        await redisClient.subscribe('energy_updates', 'device_status', 'system_notifications');
        
        redisClient.on('message', (channel, message) => {
            try {
                const data = JSON.parse(message);
                broadcastToChannel(channel, data);
            } catch (error) {
                console.error('Error parsing Redis message:', error);
            }
        });
        
    } catch (error) {
        console.error('⚠️  Redis connection failed:', error);
        redisClient = null;
    }
}

// JWT verification
function verifyToken(token) {
    try {
        return jwt.verify(token, JWT_SECRET);
    } catch (error) {
        return null;
    }
}

// Connection handling
wss.on('connection', (ws, req) => {
    const connectionId = uuidv4();
    const connection = {
        id: connectionId,
        ws: ws,
        userId: null,
        userEmail: null,
        subscriptions: new Set(),
        isAuthenticated: false,
        connectedAt: new Date()
    };
    
    connections.set(connectionId, connection);
    
    console.log(`🔌 New WebSocket connection: ${connectionId}`);
    
    // Send welcome message
    sendMessage(ws, {
        type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
        message: 'Connected to Smart Home Energy Monitoring',
        timestamp: new Date().toISOString(),
        connectionId: connectionId
    });
    
    // Message handling
    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            await handleMessage(connection, data);
        } catch (error) {
            console.error('Error handling message:', error);
            sendMessage(ws, {
                type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
                message: 'Error processing message',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
    });
    
    // Connection close handling
    ws.on('close', () => {
        console.log(`🔌 WebSocket connection closed: ${connectionId}`);
        
        // Clean up subscriptions
        if (connection.subscriptions.size > 0) {
            connection.subscriptions.forEach(room => {
                removeFromRoom(room, connectionId);
            });
        }
        
        // Remove from user rooms
        if (connection.userId) {
            const userRoom = `user:${connection.userId}`;
            removeFromRoom(userRoom, connectionId);
        }
        
        connections.delete(connectionId);
    });
    
    // Error handling
    ws.on('error', (error) => {
        console.error(`WebSocket error for connection ${connectionId}:`, error);
    });
});

// Message handling
async function handleMessage(connection, data) {
    const { type, payload } = data;
    
    switch (type) {
        case MESSAGE_TYPES.AUTHENTICATION:
            await handleAuthentication(connection, payload);
            break;
            
        case MESSAGE_TYPES.SUBSCRIBE:
            await handleSubscribe(connection, payload);
            break;
            
        case MESSAGE_TYPES.UNSUBSCRIBE:
            await handleUnsubscribe(connection, payload);
            break;
            
        case MESSAGE_TYPES.CHAT:
            await handleChatMessage(connection, payload);
            break;
            
        default:
            sendMessage(connection.ws, {
                type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
                message: 'Unknown message type',
                timestamp: new Date().toISOString()
            });
    }
}

// Handle authentication
async function handleAuthentication(connection, payload) {
    const { token } = payload;
    
    if (!token) {
        sendMessage(connection.ws, {
            type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
            message: 'Authentication token required',
            timestamp: new Date().toISOString()
        });
        return;
    }
    
    const decoded = verifyToken(token);
    if (!decoded) {
        sendMessage(connection.ws, {
            type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
            message: 'Invalid authentication token',
            timestamp: new Date().toISOString()
        });
        return;
    }
    
    // Update connection with user info
    connection.userId = decoded.sub;
    connection.userEmail = decoded.email;
    connection.isAuthenticated = true;
    
    // Add to user room
    const userRoom = `user:${connection.userId}`;
    addToRoom(userRoom, connection.id);
    
    console.log(`🔐 User authenticated: ${connection.userEmail} (${connection.userId})`);
    
    sendMessage(connection.ws, {
        type: MESSAGE_TYPES.AUTHENTICATION,
        message: 'Authentication successful',
        userId: connection.userId,
        userEmail: connection.userEmail,
        timestamp: new Date().toISOString()
    });
}

// Handle subscription
async function handleSubscribe(connection, payload) {
    const { room } = payload;
    
    if (!room) {
        sendMessage(connection.ws, {
            type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
            message: 'Room name required for subscription',
            timestamp: new Date().toISOString()
        });
        return;
    }
    
    // Add to room
    addToRoom(room, connection.id);
    connection.subscriptions.add(room);
    
    console.log(`📡 Connection ${connection.id} subscribed to room: ${room}`);
    
    sendMessage(connection.ws, {
        type: MESSAGE_TYPES.SUBSCRIBE,
        message: `Subscribed to ${room}`,
        room: room,
        timestamp: new Date().toISOString()
    });
}

// Handle unsubscription
async function handleUnsubscribe(connection, payload) {
    const { room } = payload;
    
    if (!room) {
        sendMessage(connection.ws, {
            type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
            message: 'Room name required for unsubscription',
            timestamp: new Date().toISOString()
        });
        return;
    }
    
    // Remove from room
    removeFromRoom(room, connection.id);
    connection.subscriptions.delete(room);
    
    console.log(`📡 Connection ${connection.id} unsubscribed from room: ${room}`);
    
    sendMessage(connection.ws, {
        type: MESSAGE_TYPES.UNSUBSCRIBE,
        message: `Unsubscribed from ${room}`,
        room: room,
        timestamp: new Date().toISOString()
    });
}

// Handle chat messages
async function handleChatMessage(connection, payload) {
    const { message, room = 'general' } = payload;
    
    if (!message || !message.trim()) {
        sendMessage(connection.ws, {
            type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
            message: 'Message content required',
            timestamp: new Date().toISOString()
        });
        return;
    }
    
    const chatMessage = {
        type: MESSAGE_TYPES.CHAT,
        message: message.trim(),
        userId: connection.userId,
        userEmail: connection.userEmail,
        timestamp: new Date().toISOString(),
        messageId: uuidv4()
    };
    
    // Broadcast to room
    broadcastToRoom(room, chatMessage);
    
    // Store in Redis for persistence
    if (redisClient) {
        try {
            await redisClient.lPush(`chat:${room}`, JSON.stringify(chatMessage));
            await redisClient.lTrim(`chat:${room}`, 0, 99); // Keep last 100 messages
        } catch (error) {
            console.error('Error storing chat message in Redis:', error);
        }
    }
    
    console.log(`💬 Chat message in ${room}: ${connection.userEmail}: ${message}`);
}

// Room management
function addToRoom(room, connectionId) {
    if (!userRooms.has(room)) {
        userRooms.set(room, new Set());
    }
    userRooms.get(room).add(connectionId);
}

function removeFromRoom(room, connectionId) {
    if (userRooms.has(room)) {
        userRooms.get(room).delete(connectionId);
        if (userRooms.get(room).size === 0) {
            userRooms.delete(room);
        }
    }
}

// Broadcasting functions
function broadcastToRoom(room, message) {
    if (userRooms.has(room)) {
        userRooms.get(room).forEach(connectionId => {
            const connection = connections.get(connectionId);
            if (connection && connection.ws.readyState === WebSocket.OPEN) {
                sendMessage(connection.ws, message);
            }
        });
    }
}

function broadcastToChannel(channel, message) {
    const room = channel;
    broadcastToRoom(room, {
        type: MESSAGE_TYPES.SYSTEM_NOTIFICATION,
        message: `Update from ${channel}`,
        data: message,
        timestamp: new Date().toISOString()
    });
}

function broadcastToUser(userId, message) {
    const userRoom = `user:${userId}`;
    broadcastToRoom(userRoom, message);
}

// Utility functions
function sendMessage(ws, message) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    }
}

function broadcastToAll(message) {
    connections.forEach(connection => {
        if (connection.ws.readyState === WebSocket.OPEN) {
            sendMessage(connection.ws, message);
        }
    });
}

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'websocket-service',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        connections: connections.size,
        rooms: userRooms.size
    });
});

// Statistics endpoint
app.get('/stats', (req, res) => {
    const stats = {
        totalConnections: connections.size,
        authenticatedConnections: Array.from(connections.values()).filter(c => c.isAuthenticated).length,
        totalRooms: userRooms.size,
        connections: Array.from(connections.values()).map(c => ({
            id: c.id,
            userId: c.userId,
            userEmail: c.userEmail,
            isAuthenticated: c.isAuthenticated,
            subscriptions: Array.from(c.subscriptions),
            connectedAt: c.connectedAt
        }))
    };
    
    res.json(stats);
});

// Start server
async function startServer() {
    try {
        // Initialize Redis
        await initializeRedis();
        
        // Start HTTP server
        server.listen(PORT, () => {
            console.log(`🚀 WebSocket Service started on port ${PORT}`);
            console.log(`📡 WebSocket endpoint: ws://localhost:${PORT}`);
            console.log(`🔍 Health check: http://localhost:${PORT}/health`);
            console.log(`📊 Statistics: http://localhost:${PORT}/stats`);
        });
        
        // Periodic cleanup of stale connections
        setInterval(() => {
            connections.forEach((connection, connectionId) => {
                if (connection.ws.readyState !== WebSocket.OPEN) {
                    connections.delete(connectionId);
                }
            });
        }, 30000); // Every 30 seconds
        
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    
    // Close all WebSocket connections
    connections.forEach(connection => {
        connection.ws.close();
    });
    
    // Close Redis connection
    if (redisClient) {
        await redisClient.quit();
    }
    
    // Close server
    server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', async () => {
    console.log('🛑 Received SIGINT, shutting down gracefully...');
    
    // Close all WebSocket connections
    connections.forEach(connection => {
        connection.ws.close();
    });
    
    // Close Redis connection
    if (redisClient) {
        await redisClient.quit();
    }
    
    // Close server
    server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
    });
});

// Start the server
startServer();
