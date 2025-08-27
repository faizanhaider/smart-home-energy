import React, { useState } from 'react';

const Chat = () => {
  const [message, setMessage] = useState('');
  const [chatHistory] = useState([
    {
      id: 1,
      type: 'user',
      content: 'How much energy did my AC use last week?',
      timestamp: '2 minutes ago'
    },
    {
      id: 2,
      type: 'assistant',
      content: 'Your AC consumed 45.2 kWh last week, which is about $6.78 at current rates. This is 15% higher than the previous week, likely due to warmer weather.',
      timestamp: '1 minute ago'
    },
    {
      id: 3,
      type: 'user',
      content: 'What\'s my most efficient device?',
      timestamp: 'Just now'
    },
    {
      id: 4,
      type: 'assistant',
      content: 'Your refrigerator is your most efficient device, operating at 92% efficiency. It uses only 0.8 kW and has maintained consistent performance over the past month.',
      timestamp: 'Just now'
    }
  ]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      // Here you would typically send the message to the chat service
      console.log('Sending message:', message);
      setMessage('');
    }
  };

  const getMessageStyle = (type) => {
    return type === 'user' 
      ? 'bg-blue-600 text-white ml-auto' 
      : 'bg-gray-200 text-gray-900';
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">AI Energy Assistant</h1>
      <p className="mt-2 text-gray-600">
        Ask questions about your energy consumption in natural language
      </p>

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
          <div className="space-y-4">
            {chatHistory.map((chat) => (
              <div key={chat.id} className="flex">
                <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${getMessageStyle(chat.type)}`}>
                  <p className="text-sm">{chat.content}</p>
                  <p className={`text-xs mt-1 ${chat.type === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                    {chat.timestamp}
                  </p>
                </div>
              </div>
            ))}
          </div>
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
            />
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Send
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
              onClick={() => setMessage(question)}
              className="text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-md text-sm text-gray-700 transition-colors"
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
