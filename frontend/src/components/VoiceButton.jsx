import React, { useState } from 'react';
import { Mic, MicOff, Volume2 } from 'lucide-react';
import { voiceService } from '../services/voiceService';

export default function VoiceButton({ language = 'en', onSpeechResult, title = "Voice input" }) {
  const [isListening, setIsListening] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const toggleListening = () => {
    if (isListening) {
      voiceService.stopListening();
      setIsListening(false);
    } else {
      setErrorMsg(null);
      setIsListening(true);
      voiceService.startListening(
        language,
        (transcript) => {
          setIsListening(false);
          if (onSpeechResult) onSpeechResult(transcript);
        },
        (err) => {
          setIsListening(false);
          setErrorMsg(err);
        },
        () => {
          setIsListening(false);
        }
      );
    }
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        className={`mic-btn ${isListening ? 'listening' : ''}`}
        onClick={toggleListening}
        title={isListening ? "Listening... Click to stop" : title}
        aria-label="Voice Query"
      >
        {isListening ? <MicOff size={20} /> : <Mic size={20} />}
      </button>

      {isListening && (
        <span style={{
          position: 'absolute',
          bottom: '-22px',
          left: '50%',
          transform: 'translateX(-50%)',
          fontSize: '0.65rem',
          color: 'var(--accent-rose)',
          fontWeight: 700,
          whiteSpace: 'nowrap'
        }}>
          Listening...
        </span>
      )}

      {errorMsg && (
        <span style={{
          position: 'absolute',
          bottom: '-22px',
          left: '50%',
          transform: 'translateX(-50%)',
          fontSize: '0.65rem',
          color: 'var(--accent-amber)',
          whiteSpace: 'nowrap'
        }}>
          {errorMsg}
        </span>
      )}
    </div>
  );
}
