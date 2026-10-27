import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import { ChatMessage } from '../types';
import { MessageSquareCode, Send, Sparkles, Cpu, Clock, CheckCircle2, ShieldCheck, CornerDownLeft, Loader2 } from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  '¿Cuántos sismos se registraron durante las últimas 24 horas?',
  '¿Cuál fue la magnitud máxima registrada hoy?',
  '¿Qué regiones presentaron mayor actividad?',
  '¿Qué eventos tienen alertas de tsunami?',
  '¿Cómo ha cambiado la actividad sísmica durante la última semana?',
  '¿Qué anomalías se han detectado recientemente?'
];

export const ChatAIPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: '¡Hola! Soy SismoWatch AI asistido por Google Gemini. Consulto exclusivamente información analítica certificada para responder tus preguntas operativas sobre actividad sísmica, magnitudes, anomalías y alertas de tsunami.',
      timestamp: new Date().toLocaleTimeString(),
      period_consulted: 'Datos en tiempo real',
      is_fallback: false,
      ai_model: 'gemini-3.5-flash-lite'
    }
  ]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  const handleSendMessage = async (qText: string) => {
    const question = qText.trim();
    if (!question || sending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: question,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuestion('');
    setSending(true);

    try {
      const res = await api.sendChatMessage(question);
      const assistantMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString(),
        period_consulted: res.period_consulted,
        data_points: res.data_points,
        is_fallback: res.is_fallback,
        ai_model: res.ai_model,
        latency_ms: res.latency_ms
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `Lo siento, ocurrió un error al consultar los datos analíticos: ${err.message || 'Error de conexión'}.`,
        timestamp: new Date().toLocaleTimeString(),
        is_fallback: true
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col rounded-2xl bg-sismo-surface/80 border border-slate-800 overflow-hidden shadow-2xl">
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-800 bg-sismo-darker/60 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 border border-violet-500/30 text-violet-400 shadow-glow-violet">
            <MessageSquareCode className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Asistente Conversacional Inteligente
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/80">
                Google Gemini
              </span>
            </h2>
            <p className="text-[11px] text-slate-400 font-mono">
              Respuestas analíticas redactadas por Google Gemini con cifras matemáticamente certificadas
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 hidden sm:flex">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span>Validación Activa</span>
        </div>
      </div>

      {/* Suggested Questions Quick Chips */}
      <div className="px-4 py-2.5 bg-slate-900/50 border-b border-slate-800/60 overflow-x-auto flex items-center gap-2 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 shrink-0 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-cyan-400" /> Sugerencias:
        </span>
        {SUGGESTED_QUESTIONS.map((sq, i) => (
          <button
            key={i}
            onClick={() => handleSendMessage(sq)}
            className="text-[11px] px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/70 text-slate-300 hover:text-cyan-300 transition-colors shrink-0 whitespace-nowrap"
          >
            {sq}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed space-y-2.5 shadow-lg ${
                msg.sender === 'user'
                  ? 'bg-gradient-to-r from-cyan-600 to-sky-600 text-slate-950 font-semibold rounded-br-none'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-bl-none'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.text}</div>

              {/* Data Grounding & Telemetry Pill for Assistant Messages */}
              {msg.sender === 'assistant' && (
                <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[10px] text-slate-400 font-mono gap-2">
                  <div className="flex items-center gap-2">
                    {msg.period_consulted && (
                      <span className="text-cyan-400/90 font-bold">{msg.period_consulted}</span>
                    )}
                    {msg.is_fallback && (
                      <span className="px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800">
                        Motor Determinista
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {msg.ai_model && (
                      <span className="flex items-center gap-1 text-slate-400">
                        <Cpu className="w-3 h-3 text-cyan-400" /> {msg.ai_model.includes('gemini') ? msg.ai_model : 'gemini:3.5-flash-lite'}
                      </span>
                    )}
                    {msg.latency_ms !== undefined && (
                      <span className="flex items-center gap-1 text-slate-500">
                        <Clock className="w-3 h-3" /> {msg.latency_ms} ms
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
            <span className="text-[10px] text-slate-500 mt-1 px-1 font-mono">{msg.timestamp}</span>
          </div>
        ))}

        {sending && (
          <div className="flex items-center gap-2 text-xs text-cyan-400 font-mono p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 max-w-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Consultando datos analíticos y redactando con Gemini...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800 bg-sismo-darker/60">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage(inputQuestion);
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            placeholder="Pregúntale al asistente sobre sismos, zonas, magnitudes o anomalías..."
            disabled={sending}
            className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 font-mono disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={sending || !inputQuestion.trim()}
            className="p-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-slate-950 font-bold transition-all shadow-glow-cyan"
            title="Enviar mensaje"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
