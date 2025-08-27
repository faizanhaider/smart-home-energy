import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ChatService from '../services/chatService';

const Chat = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user } = useAuth();

  
  const loadChatHistory = useCallback(async () => {
    try {
      const history = await ChatService.getChatHistory(user.id, 50);
      
      // Debug: Log the history structure
      console.log('Chat history response:', history);
      
      // Ensure history is an array
      if (!Array.isArray(history)) {
        console.warn('Chat history is not an array:', history);
        setChatHistory([]);
        return;
      }
      
      // Transform the chat history to match our frontend format
      const transformedHistory = history.flatMap(chatRecord => {
        // Skip invalid chat records
        if (!chatRecord || !chatRecord.id || !chatRecord.question) {
          console.warn('Invalid chat record:', chatRecord);
          return [];
        }

        const userMessage = {
          id: chatRecord.id,
          type: 'user',
          content: chatRecord.question,
          timestamp: chatRecord.created_at
        };

        // Handle different response structures in chat history
        let content = 'I processed your request but couldn\'t generate a response.';
        let data = null;
        let recommendations = null;

        if (chatRecord.response && typeof chatRecord.response === 'object') {
          content = chatRecord.response.summary || content;
          data = chatRecord.response.data;
          recommendations = chatRecord.response.recommendations;
        } else if (chatRecord.summary) {
          content = chatRecord.summary;
          data = chatRecord.data;
          recommendations = chatRecord.recommendations;
        }

        const assistantMessage = {
          id: `${chatRecord.id}-response`,
          type: 'assistant',
          content: content,
          timestamp: chatRecord.created_at,
          data: data,
          recommendations: recommendations
        };

        return [userMessage, assistantMessage];
      });

      setChatHistory(transformedHistory);
    } catch (error) {
      console.error('Error loading chat history:', error);
      // Set empty history on error
      setChatHistory([]);
    }
  }, [user]);

  // Load chat history on component mount
  useEffect(() => {
    if (user?.id) {
      // Check if chat service is available before loading history
      ChatService.checkHealth().then(isHealthy => {
        if (isHealthy) {
          loadChatHistory();
        } else {
          console.warn('Chat service is not healthy, skipping history load');
          setChatHistory([]);
        }
      }).catch(() => {
        console.warn('Chat service health check failed, skipping history load');
        setChatHistory([]);
      });
    }
  }, [user, loadChatHistory]);


  const sendMessage = async (question) => {
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await ChatService.sendQuery(question, user?.id);
      
      // Debug: Log the response structure
      console.log('Chat service response:', result);
      
      // Add the new message to chat history
      const newMessage = {
        id: result.id,
        type: 'user',
        content: question,
        timestamp: new Date().toLocaleTimeString()
      };

              // Handle different response structures
        let content = 'I processed your request but couldn\'t generate a response.';
        let data = null;
        let recommendations = null;

        if (result.response && typeof result.response === 'object') {
          content = result.response.summary || content;
          data = result.response.data;
          recommendations = result.response.recommendations;
        } else if (result.summary) {
          content = result.summary;
          data = result.data;
          recommendations = result.recommendations;
        }

        const assistantMessage = {
          id: `${result.id}-response`,
          type: 'assistant',
          content: content,
          timestamp: new Date().toLocaleTimeString(),
          data: data,
          recommendations: recommendations
        };

      setChatHistory(prev => [...prev, newMessage, assistantMessage]);
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
      setError(error.message || 'Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      sendMessage(message);
    }
  };

  const handleSampleQuestion = (question) => {
    setMessage(question);
    // Auto-send after a short delay to show the question being typed
    setTimeout(() => {
      sendMessage(question);
    }, 100);
  };

  const getMessageStyle = (type) => {
    return type === 'user' 
      ? 'bg-blue-600 text-white ml-auto' 
      : 'bg-gray-200 text-gray-900';
  };

  const formatTimestamp = (timestamp) => {
    if (typeof timestamp === 'string') {
      return timestamp;
    }
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return 'Just now';
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">AI Energy Assistant</h1>
      <p className="mt-2 text-gray-600">
        Ask questions about your energy consumption in natural language
      </p>

      {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="mt-6 bg-white rounded-lg shadow">
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-gray-900">Energy AI Assistant</h3>
              <p className="text-sm text-gray-500">Powered by OpenAI</p>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="px-6 py-4 h-96 overflow-y-auto">
          {chatHistory.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <p>No messages yet. Start a conversation by asking about your energy usage!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {chatHistory.map((chat) => (
                <div key={chat.id} className="flex">
                  <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${getMessageStyle(chat.type)}`}>
                    <p className="text-sm">{chat.content}</p>
                    <p className={`text-xs mt-1 ${chat.type === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                      {formatTimestamp(chat.timestamp)}
                    </p>
                    
                    {/* Show recommendations if available */}
                    {chat.type === 'assistant' && chat.recommendations && chat.recommendations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-300">
                        <p className="text-xs font-medium text-gray-700 mb-1">Suggestions:</p>
                        <ul className="text-xs text-gray-600 space-y-1">
                          {chat.recommendations.map((rec, index) => (
                            <li key={index}>• {rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex">
                  <div className="bg-gray-200 text-gray-900 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                      <p className="text-sm">Processing your question...</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Chat Input */}
        <div className="px-6 py-4 border-t border-gray-200">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask about your energy consumption..."
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !message.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </div>

      {/* Sample Questions */}
      <div className="mt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-3">Sample Questions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            'How much energy did my AC use last week?',
            'What\'s my highest-consuming device today?',
            'Compare energy usage of my devices this month',
            'Give me an energy analysis for this week',
            'What\'s my energy cost for today?',
            'Which devices are most efficient?'
          ].map((question, index) => (
            <button
              key={index}
              onClick={() => handleSampleQuestion(question)}
              disabled={isLoading}
              className="text-left p-3 bg-gray-50 hover:bg-gray-100 disabled:bg-gray-100 disabled:cursor-not-allowed rounded-md text-sm text-gray-700 transition-colors"
            >
              {question}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Chat;
