/**
 * Chat Service API client
 * Handles communication with the chat service backend
 */

import axios from 'axios';

const CHAT_SERVICE_URL = process.env.REACT_APP_CHAT_API_URL || 'http://localhost:8002';

// Helper function to get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('token');
};

// Helper function to create axios instance with auth headers
const createAuthenticatedRequest = () => {
  const token = getAuthToken();
  const config = {
    headers: {}
  };
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
};

class ChatService {
  /**
   * Send a chat query to the AI assistant
   * @param {string} question - The user's question
   * @param {string} userId - The user's ID (optional)
   * @returns {Promise<Object>} The AI response
   */
  static async sendQuery(question, userId = null) {
    try {
      const config = createAuthenticatedRequest();
      config.headers['Content-Type'] = 'application/json';
      
      const response = await axios.post(`${CHAT_SERVICE_URL}/query`, {
        question: question,
        user_id: userId
      }, config);

      return response.data;
    } catch (error) {
      console.error('Error sending chat query:', error);
      throw error;
    }
  }

  /**
   * Get chat history for a user
   * @param {string} userId - The user's ID
   * @param {number} limit - Maximum number of messages to return
   * @param {number} offset - Number of messages to skip
   * @returns {Promise<Array>} Array of chat messages
   */
  static async getChatHistory(userId, limit = 50, offset = 0) {
    try {
      const response = await axios.get(
        `${CHAT_SERVICE_URL}/history?user_id=${userId}&limit=${limit}&offset=${offset}`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching chat history:', error);
      throw error;
    }
  }

  /**
   * Get supported query intents and examples
   * @returns {Promise<Object>} Supported intents and examples
   */
  static async getSupportedIntents() {
    try {
      const response = await axios.get(
        `${CHAT_SERVICE_URL}/intents`,
        createAuthenticatedRequest()
      );

      return response.data;
    } catch (error) {
      console.error('Error fetching supported intents:', error);
      throw error;
    }
  }

  /**
   * Check if the chat service is healthy
   * @returns {Promise<boolean>} True if service is healthy
   */
  static async checkHealth() {
    try {
      const response = await axios.get(`${CHAT_SERVICE_URL}/health`);
      return response.status === 200;
    } catch (error) {
      console.error('Error checking chat service health:', error);
      return false;
    }
  }
}

export default ChatService;
