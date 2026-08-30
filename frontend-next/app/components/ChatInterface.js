"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Send, Briefcase, Bot, User, Search, MapPin, Loader2 } from 'lucide-react';
import styles from './ChatInterface.module.css';

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I can search for jobs, review companies, analyze resumes, and help with account tasks. How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Pointing to FastAPI backend running on port 8000
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (error) {
      console.error('Error fetching chat response:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error connecting to the server. Please ensure the backend is running.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const tools = [
    "job_search", "company_research", "resume_extract", 
    "interview_prep", "ats_resume_scorer", "save_job_application",
    "location_based_job_search", "salary_research", "extract_notice_period",
    "parse_work_logs"
  ];

  return (
    <div className={styles.container}>
      <div className={`${styles.sidebar} glass`}>
        <div className={styles.logo}>
          <Briefcase size={24} />
          <span>Job AI Agent</span>
        </div>
        
        <div>
          <h3 style={{ fontSize: '0.875rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '12px' }}>
            Capabilities
          </h3>
          <div className={styles.toolsList}>
            {tools.map(tool => (
              <div key={tool} className={styles.toolItem}>
                • {tool.replace(/_/g, ' ')}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={`${styles.mainArea} glass`}>
        <div className={styles.header}>
          <h2>Career Assistant</h2>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Powered by LangGraph</span>
        </div>

        <div className={styles.messages}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`${styles.messageWrapper} ${styles[msg.role]} animate-fade-in`}>
              <div className={`${styles.message} ${styles[msg.role]}`}>
                {msg.content.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    <br />
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className={`${styles.messageWrapper} assistant animate-fade-in`}>
              <div className={`${styles.message} assistant`}>
                <div className={styles.typingIndicator}>
                  <div className={styles.dot}></div>
                  <div className={styles.dot}></div>
                  <div className={styles.dot}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className={styles.inputArea}>
          <form onSubmit={handleSubmit} className={styles.inputForm}>
            <input 
              type="text" 
              className={styles.input} 
              placeholder="Ask about jobs, companies, or resume tips..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
            <button type="submit" className={styles.sendButton} disabled={!input.trim() || isLoading}>
              {isLoading ? <Loader2 className="animate-spin" /> : <Send size={20} />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
