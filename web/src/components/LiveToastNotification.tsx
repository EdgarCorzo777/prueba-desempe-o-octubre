import React, { useState, useEffect, useRef } from 'react';
import { sseService } from '../services/sse';
import { SeismicEvent } from '../types';

interface ToastItem {
  id: string;
  event: SeismicEvent;
  createdAt: number;
}

export const LiveToastNotification: React.FC = () => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const sessionStartTime = useRef(Date.now());

  useEffect(() => {
    const unsubscribe = sseService.subscribe((event: SeismicEvent) => {
      const eventTimestamp = new Date(event.updated_time || event.event_time).getTime();
      // Only show live incoming events during the current session
      if (eventTimestamp < sessionStartTime.current - 10000) {
        return;
      }

      const newToast: ToastItem = {
        id: `${event.event_id}_${Date.now()}`,
        event,
        createdAt: Date.now(),
      };

      setToasts((prev) => [newToast, ...prev.slice(0, 2)]);

      setTimeout(() => {
        setToasts((current) => current.filter((t) => t.id !== newToast.id));
      }, 6000);
    });

    return () => unsubscribe();
  }, []);

  const removeToast = (id: string) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-20 right-margin z-50 flex flex-col space-y-space-sm w-80 pointer-events-none">
      {toasts.map((t) => {
        const isTsunami = t.event.tsunami;
        const isSevere = t.event.magnitude >= 6.0;

        return (
          <div
            key={t.id}
            className={`pointer-events-auto p-space-md rounded-xl backdrop-blur-md shadow-2xl flex items-start space-x-space-sm border transition-all duration-300 animate-in fade-in slide-in-from-right ${
              isTsunami
                ? 'bg-error-container/95 border-error text-on-error-container shadow-[0_0_25px_rgba(147,0,10,0.5)]'
                : isSevere
                ? 'bg-surface-container-high/95 border-orange-400 text-on-surface shadow-[0_0_20px_rgba(249,115,22,0.3)]'
                : 'bg-surface-container-low/95 border-primary text-on-surface shadow-[0_0_20px_rgba(0,240,255,0.2)]'
            }`}
          >
            <span
              className={`material-symbols-outlined text-[22px] shrink-0 ${
                isTsunami
                  ? 'text-error animate-pulse'
                  : isSevere
                  ? 'text-orange-400'
                  : 'text-primary'
              }`}
            >
              {isTsunami ? 'tsunami' : isSevere ? 'warning' : 'pulse_alert'}
            </span>

            <div className="flex-1 min-w-0">
              <div className="text-label-md font-bold tracking-wider uppercase flex items-center justify-between">
                <span>{isTsunami ? 'ALERTA DE TSUNAMI' : 'NUEVO SISMO'}</span>
                <span className="font-mono text-primary font-bold">
                  M {t.event.magnitude.toFixed(1)}
                </span>
              </div>
              <div className="text-body-sm truncate mt-0.5 leading-snug font-medium">
                {t.event.place}
              </div>
              <div className="text-label-sm opacity-80 mt-1 font-mono">
                Prof: {t.event.depth_km.toFixed(1)} km &bull;{' '}
                {new Date(t.event.event_time).toLocaleTimeString()}
              </div>
            </div>

            <button
              onClick={() => removeToast(t.id)}
              className="opacity-70 hover:opacity-100 transition-opacity p-0.5"
              title="Cerrar notificación"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        );
      })}
    </div>
  );
};
