import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import { ChatResponse } from '../types';
import { ChatMarkdown } from './ChatMarkdown';

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  time: string;
  period?: string;
  model?: string;
  latency?: number;
  isFallback?: boolean;
}

export const FloatingChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: 'Hola. Soy el analista virtual de SismoWatch, respondiendo con las cifras certificadas del sistema. ¿Qué datos sísmicos, comparativas o información de la plataforma necesitas?',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (queryToSend?: string) => {
    const q = (queryToSend || inputQuery).trim();
    if (!q || loading) return;

    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      sender: 'user',
      text: q,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res: ChatResponse = await api.askChat(q);
      const aiMsg: ChatMessage = {
        id: `ai_${Date.now()}`,
        sender: 'ai',
        text: res.answer,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        period: res.period_consulted,
        latency: res.latency_ms,
        isFallback: res.is_fallback,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: 'ai',
        text: `Error de comunicación: ${err.message || 'No se pudo obtener respuesta del modelo de IA.'}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isFallback: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const samplePrompts = [
    'Estado de Red Global',
    'Sismos M>=6.0 últimas 24h',
    'Alertas de tsunami activas',
    'Regiones con mayor frecuencia',
  ];

  return (
    <div className="fixed bottom-margin right-margin z-50">
      <div className="relative">
        {/* Modal Window */}
        {isOpen && (
          <div
            className="absolute bottom-16 right-0 w-[420px] max-w-[92vw] h-[580px] max-h-[85vh] bg-surface-container-low border border-outline-variant rounded-xl shadow-2xl flex flex-col overflow-hidden backdrop-blur-2xl z-50 animate-in fade-in slide-in-from-bottom-4 duration-200"
            id="ai-modal"
          >
            {/* Modal Header */}
            <div className="p-space-md bg-surface-container-high flex items-center justify-between border-b border-outline-variant shrink-0">
              <div className="flex items-center space-x-space-sm">
                <span className="material-symbols-outlined text-primary text-[24px]">
                  smart_toy
                </span>
                <span className="text-headline-sm font-headline-sm text-on-surface">
                  Asistente IA SismoWatch
                </span>
              </div>
              <button
                className="text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors"
                id="close-ai"
                onClick={() => setIsOpen(false)}
                title="Cerrar asistente"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            {/* Message Thread */}
            <div className="flex-1 p-space-md overflow-y-auto space-y-space-md flex flex-col">
              {messages.map((m) => {
                const isUser = m.sender === 'user';
                return (
                  <div
                    key={m.id}
                    className={`p-space-md rounded-xl max-w-[85%] border transition-all ${
                      isUser
                        ? 'self-end bg-primary-container text-on-primary-container border-primary-fixed-dim font-medium shadow-sm'
                        : 'self-start bg-surface-container text-on-surface border-outline-variant shadow-sm'
                    }`}
                  >
                    <ChatMarkdown text={m.text} />
                    {!isUser && (
                      <div className="mt-2 pt-1.5 border-t border-outline-variant/30 flex items-center justify-between text-label-sm font-label-sm text-on-surface-variant">
                        <span>
                          {m.isFallback ? 'Modo Determinista' : 'Motor Analítico SismoWatch'}
                          {m.period && (
                            <span className="ml-2 opacity-70 normal-case">· {m.period}</span>
                          )}
                        </span>
                        {m.latency !== undefined && (
                          <span className="text-primary font-mono">{m.latency.toFixed(0)}ms</span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {loading && (
                <div className="self-start bg-surface-container p-space-md rounded-xl max-w-[85%] border border-outline-variant text-body-md text-on-surface-variant flex items-center space-x-2">
                  <span className="material-symbols-outlined animate-spin text-primary text-[18px]">
                    progress_activity
                  </span>
                  <span>Consultando datos analíticos del sistema...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Suggestions & Input Footer */}
            <div className="p-space-md bg-surface-container-high border-t border-outline-variant flex flex-col space-y-space-sm shrink-0">
              <div className="flex space-x-space-xs overflow-x-auto pb-1 no-scrollbar">
                {samplePrompts.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(p)}
                    className="px-2.5 py-1 bg-surface-container rounded-full text-label-sm text-primary border border-outline-variant whitespace-nowrap hover:bg-surface-container-highest transition-colors"
                  >
                    {p}
                  </button>
                ))}
              </div>

              <form
                className="flex items-center space-x-space-sm"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
              >
                <input
                  className="flex-1 bg-surface-container border border-outline-variant rounded-lg px-space-md py-2 text-body-md text-on-surface focus:outline-none focus:border-primary font-label-md disabled:opacity-50"
                  placeholder="Escribe un comando o consulta..."
                  type="text"
                  value={inputQuery}
                  disabled={loading}
                  onChange={(e) => setInputQuery(e.target.value)}
                />
                <button
                  className="p-2 bg-primary text-on-primary rounded-lg hover:bg-primary-fixed transition-colors disabled:opacity-40"
                  type="submit"
                  disabled={loading || !inputQuery.trim()}
                >
                  <span className="material-symbols-outlined text-[18px]">send</span>
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Floating Launcher Button */}
        <button
          className="w-14 h-14 rounded-full bg-primary-container text-on-primary-container shadow-[0_0_20px_rgba(0,240,255,0.4)] flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
          id="open-ai"
          onClick={() => setIsOpen((prev) => !prev)}
          title="Abrir Asistente IA SismoWatch"
        >
          <span className="material-symbols-outlined text-[28px]">smart_toy</span>
        </button>
      </div>
    </div>
  );
};
