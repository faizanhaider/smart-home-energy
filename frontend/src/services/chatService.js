/**
 * Chat Service API client
 * Handles communication with the chat service backend
 */

const CHAT_SERVICE_URL = process.env.REACT_APP_CHAT_SERVICE_URL || 'http://localhost:8002';

class ChatService {
  /**
   * Send a chat query to the AI assistant
   * @param {string} question - The user's question
   * @param {string} userId - The user's ID (optional)
   * @returns {Promise<Object>} The AI response
   */
  static async sendQuery(question, userId = null) {
    try {
      const response = await fetch(`${CHAT_SERVICE_URL}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          user_id: userId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
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
      const response = await fetch(
        `${CHAT_SERVICE_URL}/history?user_id=${userId}&limit=${limit}&offset=${offset}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
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
      const response = await fetch(`${CHAT_SERVICE_URL}/intents`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
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
      const response = await fetch(`${CHAT_SERVICE_URL}/health`);
      return response.ok;
    } catch (error) {
      console.error('Error checking chat service health:', error);
      return false;
    }
  }
}

export default ChatService;
