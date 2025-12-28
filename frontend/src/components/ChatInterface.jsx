import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, Loader, Bot, User } from 'lucide-react';
import './ChatInterface.css';

const EXAMPLE_QUESTIONS = [
  "How many S2_V1 scooters can we build right now?",
  "Which materials are running low on stock?",
  "What's our current inventory value?",
  "Show me supplier performance",
  "What are the critical alerts I should know about?",
  "Calculate build capacity for all scooter models",
];

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm Hugo, your AI procurement assistant for Voltway. I can help you with inventory analysis, build capacity calculations, supplier performance, and more. What would you like to know?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat', {
        question: input
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        data: response.data.data,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
        error: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleExampleClick = (question) => {
    setInput(question);
  };

  return (
    <div className="chat-interface">
      <div className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? <User size={20} /> : <Bot size={20} />}
              </div>
              <div className="message-content">
                <div className="message-text">
                  {message.content}
                </div>
                {message.data && (
                  <div className="message-data">
                    <details>
                      <summary>View Data</summary>
                      <pre>{JSON.stringify(message.data, null, 2)}</pre>
                    </details>
                  </div>
                )}
                <div className="message-time">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <div className="message-avatar">
                <Bot size={20} />
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <Loader className="spinner" size={16} />
                  <span>Hugo is thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {messages.length === 1 && (
          <div className="examples">
            <p className="examples-title">Try asking:</p>
            <div className="examples-grid">
              {EXAMPLE_QUESTIONS.map((question, index) => (
                <button
                  key={index}
                  className="example-button"
                  onClick={() => handleExampleClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="input-container">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask Hugo anything about inventory, suppliers, build capacity..."
            rows={1}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="send-button"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;