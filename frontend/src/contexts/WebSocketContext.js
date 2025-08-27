import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';
import toast from 'react-hot-toast';

// WebSocket configuration
const WS_URL = process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8003';

// Create WebSocket context
const WebSocketContext = createContext();

// Custom hook to use WebSocket context
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// WebSocket provider component
export const WebSocketProvider = ({ children }) => {
  const { user, token, isAuthenticated } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [chatMessages, setChatMessages] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [energyUpdates, setEnergyUpdates] = useState([]);
  const [deviceTelemetry, setDeviceTelemetry] = useState(new Map()); // device_id -> telemetry data
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const subscriptionsRef = useRef(new Set()); // Track active subscriptions

  // Message types
  const MESSAGE_TYPES = {
    CHAT: 'chat',
    ENERGY_UPDATE: 'energy_update',
    DEVICE_STATUS: 'device_status',
    DEVICE_TELEMETRY: 'device_telemetry',
    DEVICE_TELEMETRY_UPDATE: 'device_telemetry_update',
    SYSTEM_NOTIFICATION: 'system_notification',
    AUTHENTICATION: 'authentication',
    SUBSCRIBE: 'subscribe',
    UNSUBSCRIBE: 'unsubscribe'
  };

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setConnectionStatus('connecting');
      wsRef.current = new WebSocket(WS_URL);

      wsRef.current.onopen = () => {
        console.log('🔌 WebSocket connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        
        // Authenticate if user is logged in
        if (isAuthenticated && token) {
          authenticate();
        }
        
        // Subscribe to default channels
        subscribe('general');
        subscribe('energy_updates');
        subscribe('device_status');
        
        // Resubscribe to device telemetry if we have active subscriptions
        if (subscriptionsRef.current.size > 0) {
          subscriptionsRef.current.forEach(subscription => {
            sendMessage({
              type: MESSAGE_TYPES.SUBSCRIBE,
              payload: JSON.parse(subscription)
            });
          });
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Attempt to reconnect if not a clean close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          scheduleReconnect();
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
      scheduleReconnect();
    }
  }, [isAuthenticated, token]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User initiated disconnect');
      wsRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  // Schedule reconnection
  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.log('Max reconnection attempts reached');
      setConnectionStatus('failed');
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
    reconnectAttempts.current += 1;
    
    console.log(`Scheduling reconnection attempt ${reconnectAttempts.current} in ${delay}ms`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect]);

  // Authenticate with WebSocket
  const authenticate = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && token) {
      sendMessage({
        type: MESSAGE_TYPES.AUTHENTICATION,
        payload: { token }
      });
    }
  }, [token]);

  // Subscribe to a channel
  const subscribe = useCallback((room) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendMessage({
        type: MESSAGE_TYPES.SUBSCRIBE,
        payload: { room }
      });
    }
  }, []);

  // Unsubscribe from a channel
  const unsubscribe = useCallback((room) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendMessage({
        type: MESSAGE_TYPES.UNSUBSCRIBE,
        payload: { room }
      });
    }
  }, []);

  // Subscribe to device telemetry updates
  const subscribeToDeviceTelemetry = useCallback((deviceId, userId) => {
    if (!deviceId || !userId) return;
    
    const subscription = {
      type: 'DEVICE_TELEMETRY',
      device_id: deviceId,
      user_id: userId
    };
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendMessage({
        type: MESSAGE_TYPES.SUBSCRIBE,
        payload: subscription
      });
      
      // Track subscription
      subscriptionsRef.current.add(JSON.stringify(subscription));
      console.log('🔌 Subscribed to device telemetry:', deviceId);
    }
  }, []);

  // Unsubscribe from device telemetry updates
  const unsubscribeFromDeviceTelemetry = useCallback((deviceId, userId) => {
    if (!deviceId || !userId) return;
    
    const subscription = {
      type: 'DEVICE_TELEMETRY',
      device_id: deviceId,
      user_id: userId
    };
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendMessage({
        type: MESSAGE_TYPES.UNSUBSCRIBE,
        payload: subscription
      });
      
      // Remove from tracked subscriptions
      subscriptionsRef.current.delete(JSON.stringify(subscription));
      console.log('🔌 Unsubscribed from device telemetry:', deviceId);
    }
  }, []);

  // Send message
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
      toast.error('Connection lost. Please refresh the page.');
    }
  }, []);

  // Send chat message
  const sendChatMessage = useCallback((message, room = 'general') => {
    sendMessage({
      type: MESSAGE_TYPES.CHAT,
      payload: { message, room }
    });
  }, [sendMessage]);

  // Handle incoming messages
  const handleMessage = useCallback((message) => {
    
    switch (message.type) {
      
      case MESSAGE_TYPES.CHAT:
        setChatMessages(prev => [...prev, message]);
        break;
        
      case MESSAGE_TYPES.ENERGY_UPDATE:
        setEnergyUpdates(prev => [message, ...prev.slice(0, 49)]); // Keep last 50
        break;
        
      case MESSAGE_TYPES.DEVICE_STATUS:
        // Handle device status updates
        break;
        
      case MESSAGE_TYPES.DEVICE_TELEMETRY:
        // Handle device telemetry data
        if (message.device_id && message.data) {
          setDeviceTelemetry(prev => {
            const newMap = new Map(prev);
            newMap.set(message.device_id, message.data);
            return newMap;
          });
        }
        break;
        
      case MESSAGE_TYPES.DEVICE_TELEMETRY_UPDATE:
        // Handle real-time device telemetry updates
        if (message.device_id) {
          // Dispatch custom event for components to listen to
          const event = new CustomEvent('websocket-message', { detail: message });
          window.dispatchEvent(event);
          
          // Update local state
          setDeviceTelemetry(prev => {
            const newMap = new Map(prev);
            const existingData = newMap.get(message.device_id) || [];
            const newDataPoint = {
              timestamp: message.timestamp || new Date().toISOString(),
              energy_watts: message.energy_watts,
              device_id: message.device_id
            };
            
            // Add new data point and keep only last 100 points
            const updatedData = [...existingData, newDataPoint].slice(-100);
            newMap.set(message.device_id, updatedData);
            return newMap;
          });
        }
        break;
        
      case MESSAGE_TYPES.SYSTEM_NOTIFICATION:
        if (message.message.includes('Error')) {
          toast.error(message.message);
        } else if (message.message.includes('successful')) {
          toast.success(message.message);
        } else {
          toast(message.message);
        }
        break;
        
      case MESSAGE_TYPES.AUTHENTICATION:
        if (message.message === 'Authentication successful') {
          console.log('🔐 WebSocket authenticated successfully');
        }
        break;
        
      default:
        console.log('Unknown message type:', message.type);
    }
  }, []);

  // Connect when user authenticates
  useEffect(() => {
    if (isAuthenticated && token) {
      connect();
    } else {
      disconnect();
    }
  }, [isAuthenticated, token, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Context value
  const value = {
    isConnected,
    connectionStatus,
    chatMessages,
    onlineUsers,
    energyUpdates,
    deviceTelemetry,
    connect,
    disconnect,
    sendMessage,
    sendChatMessage,
    subscribe,
    unsubscribe,
    subscribeToDeviceTelemetry,
    unsubscribeFromDeviceTelemetry,
    MESSAGE_TYPES
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};
