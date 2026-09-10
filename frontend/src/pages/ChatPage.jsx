import React, { useState, useRef, useEffect } from 'react';
import { Send, Volume2, Sparkles, MessageSquare, Bot, User, ShieldCheck } from 'lucide-react';
import VoiceButton from '../components/VoiceButton';
import RiskBadge from '../components/RiskBadge';
import ExplainableFactors from '../components/ExplainableFactors';
import SourceAttribution from '../components/SourceAttribution';
import { queryChat } from '../services/api';
import { voiceService } from '../services/voiceService';
import { UI_TRANSLATIONS } from '../utils/constants';

export default function ChatPage({ currentCity, currentLang, coordinates }) {
  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'assistant',
      text: `Hello! I am WeatherGPT, your Conversational Meteorological Decision-Support Assistant for ${currentCity}. You can ask me about forecasts, rain probability, outdoor sports, travel safety, or agricultural advisories in English, हिन्दी, or தமிழ்.`,
      source: 'WeatherGPT Intelligence Gateway',
      factors: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (textToSend) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || loading) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await queryChat(
        query,
        currentCity,
        coordinates?.lat,
        coordinates?.lon,
        currentLang
      );

      const assistantMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: response.answer,
        risk_level: response.risk_level,
        risk_score: response.risk_score,
        factors: response.factors || [],
        recommendation: response.recommendation,
        source: response.source,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMsg]);

      // Automatically speak answer if voice synthesis is active
      // voiceService.speak(response.answer, currentLang);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'assistant',
          text: `I encountered an issue processing your meteorological query: ${err.message}. Please check network connection or backend services.`,
          source: 'System Error Handler',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSpeechInput = (transcript) => {
    setInputMessage(transcript);
    handleSend(transcript);
  };

  const handleSpeakText = (text) => {
    voiceService.speak(text, currentLang);
  };

  const quickPrompts = [
    "Will it rain tomorrow?",
    "How is the weather this weekend?",
    "Will tomorrow be suitable for an outdoor event?",
    "Can I go running tomorrow morning?",
    "Will the temperature be high tomorrow?",
    "Should I carry an umbrella?",
    "Naalaikku mazha varuma?",
    "Kya kal barish hogi?"
  ];

  return (
    <div className="glass-panel chat-container">
      {/* Chat Messages */}
      <div className="chat-messages">
        {messages.map((m) => (
          <div key={m.id} className={`chat-bubble ${m.sender}`}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.8rem' }}>
                {m.sender === 'assistant' ? (
                  <>
                    <Bot size={15} style={{ color: 'var(--accent-cyan)' }} />
                    <span style={{ color: 'var(--accent-cyan)' }}>WeatherGPT</span>
                  </>
                ) : (
                  <>
                    <User size={15} />
                    <span>You</span>
                  </>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {m.risk_level && <RiskBadge level={m.risk_level} score={m.risk_score} />}
                {m.sender === 'assistant' && (
                  <button
                    type="button"
                    onClick={() => handleSpeakText(m.text)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '2px'
                    }}
                    title="Read aloud (Text-to-Speech)"
                  >
                    <Volume2 size={15} />
                  </button>
                )}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{m.timestamp}</span>
              </div>
            </div>

            {/* Content text */}
            <div style={{ fontSize: '0.9rem', lineHeight: '1.5' }}>{m.text}</div>

            {/* Explainable Factors if present */}
            {m.factors && m.factors.length > 0 && (
              <ExplainableFactors
                factors={m.factors}
                recommendation={m.recommendation}
              />
            )}

            {/* Data Source Transparency */}
            {m.source && (
              <SourceAttribution source={m.source} />
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble assistant" style={{ color: 'var(--text-muted)' }}>
            <Sparkles size={16} className="brand-icon" style={{ display: 'inline', marginRight: '6px' }} />
            Analyzing meteorological parameters and synthesizing decision support...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar */}
      <div className="quick-chips-row">
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            className="quick-chip"
            onClick={() => handleSend(p)}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Chat Input Bar with Voice Button */}
      <form
        className="chat-input-bar"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <VoiceButton
          language={currentLang}
          onSpeechResult={handleSpeechInput}
        />

        <input
          type="text"
          className="chat-input"
          placeholder={t.askPlaceholder}
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
        />

        <button
          type="submit"
          className="send-btn"
          disabled={loading || !inputMessage.trim()}
        >
          <Send size={16} />
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
