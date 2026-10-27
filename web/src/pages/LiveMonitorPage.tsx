import React, { useState, useEffect, useRef } from 'react';
import { SeismicEvent } from '../types';
import { sseService, SSEStatus } from '../services/sse';
import { api } from '../services/api';
import { Radio, AlertOctagon, Waves, MapPin, Clock, Volume2, VolumeX, ShieldAlert } from 'lucide-react';

export const LiveMonitorPage: React.FC = () => {
  const [liveEvents, setLiveEvents] = useState<SeismicEvent[]>([]);
  const [sseStatus, setSseStatus] = useState<SSEStatus>('CONNECTING');
  const [lastEventTime, setLastEventTime] = useState<Date | null>(null);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(true);
  const soundEnabledRef = useRef<boolean>(soundEnabled);
  soundEnabledRef.current = soundEnabled;

  useEffect(() => {
    // Initial fetch to populate immediately
    api.getEvents({ page_size: 30 })
      .then((res) => {
        if (res && res.events) {
          const sorted = [...res.events].sort(
            (a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime()
          );
          setLiveEvents(sorted);
          if (sorted.length > 0) {
            setLastEventTime(new Date(sorted[0].event_time));
          }
        }
      })
      .catch((err) => console.warn('Could not fetch initial events:', err));

    const unsubscribe = sseService.subscribe(
      (newEvent: SeismicEvent) => {
        setLiveEvents((prev) => {
          const map = new Map<string, SeismicEvent>();
          map.set(newEvent.event_id, newEvent);
          prev.forEach((e) => {
            if (!map.has(e.event_id)) map.set(e.event_id, e);
          });
          const sorted = Array.from(map.values()).sort(
            (a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime()
          );
          return sorted.slice(0, 50);
        });

        setLastEventTime(new Date());

        // Play brief beep for significant events if sound enabled
        if (soundEnabledRef.current && (newEvent.magnitude >= 5.5 || newEvent.tsunami)) {
          try {
            const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = newEvent.tsunami ? 880 : 550;
            gain.gain.setValueAtTime(0.1, ctx.currentTime);
            osc.start();
            osc.stop(ctx.currentTime + 0.3);
          } catch (e) {
            // Audio not allowed yet
          }
        }
      },
      (status: SSEStatus) => {
        setSseStatus(status);
      }
    );

    return () => {
      unsubscribe();
    };
  }, []);

  const getStatusBadge = () => {
    switch (sseStatus) {
      case 'CONNECTED':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/50 border border-emerald-700/60 text-emerald-400 text-xs font-mono font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            CANAL SSE ACTIVO
          </div>
        );
      case 'RECONNECTING':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-950/50 border border-amber-700/60 text-amber-400 text-xs font-mono font-bold">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
            RECONECTANDO AL FLUJO...
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-red-950/50 border border-red-700/60 text-red-400 text-xs font-mono font-bold">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            DESCONECTADO
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Monitor Bar */}
      <div className="p-5 rounded-2xl bg-sismo-surface/90 border border-slate-800 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-glow-cyan">
            <Radio className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h2 className="text-base font-extrabold tracking-wider text-slate-100 uppercase">
              Centro de Recepción en Tiempo Real
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Eventos transmitidos vía Server-Sent Events (SSE) sin recarga de pantalla
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-lg border text-xs flex items-center gap-1.5 transition-colors ${
              soundEnabled
                ? 'bg-cyan-950/40 border-cyan-700/50 text-cyan-300'
                : 'bg-slate-900 border-slate-700 text-slate-500'
            }`}
            title="Activar / Desactivar alerta sonora de eventos críticos"
          >
            {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            <span className="hidden sm:inline">{soundEnabled ? 'Sonido Activado' : 'Silenciado'}</span>
          </button>

          {getStatusBadge()}
        </div>
      </div>

      {/* Connection Notice / Reconnect Banner */}
      {sseStatus === 'RECONNECTING' && (
        <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Conexión interrumpida con el servidor. Reconectando automáticamente mediante SSE...</span>
        </div>
      )}

      {/* Stream Feed Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span className="font-bold uppercase tracking-wider">Flujo de Eventos Recientes</span>
            <span className="font-mono">{liveEvents.length} eventos en memoria de sesión</span>
          </div>

          {liveEvents.length === 0 ? (
            <div className="p-12 rounded-2xl bg-sismo-surface/50 border border-dashed border-slate-800 text-center text-slate-500 flex flex-col items-center justify-center">
              <Waves className="w-12 h-12 text-slate-600 mb-3 animate-pulse" />
              <h4 className="font-bold text-slate-300 text-sm">Esperando nuevos sismos...</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                El canal SSE se encuentra escuchando activamente las publicaciones en tiempo real. Los sismos detectados aparecerán aquí instantáneamente.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {liveEvents.map((ev, idx) => (
                <div
                  key={`${ev.event_id}-${idx}`}
                  className={`p-4 rounded-xl border transition-all duration-300 ${
                    ev.tsunami
                      ? 'bg-pink-950/30 border-pink-700/80 shadow-[0_0_15px_-3px_rgba(236,72,153,0.3)] animate-pulse'
                      : ev.magnitude >= 6.0
                      ? 'bg-red-950/20 border-red-700/60 shadow-[0_0_15px_-3px_rgba(239,68,68,0.2)]'
                      : 'bg-sismo-surface/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className={`text-xl font-extrabold font-mono px-3 py-1.5 rounded-lg border ${
                        ev.magnitude >= 7.0 ? 'bg-red-950 text-red-400 border-red-800' :
                        ev.magnitude >= 6.0 ? 'bg-orange-950 text-orange-400 border-orange-800' :
                        ev.magnitude >= 4.0 ? 'bg-cyan-950 text-cyan-400 border-cyan-800' :
                        'bg-emerald-950 text-emerald-400 border-emerald-800'
                      }`}>
                        M {ev.magnitude.toFixed(1)}
                      </div>
                      <div>
                        <div className="font-bold text-sm text-slate-100 flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          {ev.place}
                        </div>
                        <div className="text-xs text-slate-400 font-mono mt-0.5">
                          Profundidad: {ev.depth_km.toFixed(1)} km &bull; Coord: [{ev.latitude.toFixed(2)}, {ev.longitude.toFixed(2)}]
                        </div>
                      </div>
                    </div>

                    <div className="text-right flex flex-col items-end gap-1">
                      {ev.tsunami && (
                        <span className="px-2 py-0.5 rounded bg-red-600 text-white font-bold text-[10px] tracking-wider animate-bounce">
                          TSUNAMI
                        </span>
                      )}
                      <span className="text-[11px] text-slate-400 font-mono flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {new Date(ev.event_time).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Telemetry & Protocol Panel */}
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-sismo-surface/80 border border-slate-800">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-cyan-400" /> Protocolo de Severidad
            </h4>
            <div className="space-y-2.5 text-xs">
              <div className="p-2.5 rounded-lg bg-red-950/30 border border-red-800/40 text-red-300">
                <div className="font-bold">M ≥ 7.0 — Crítico</div>
                <p className="text-[11px] text-red-400/80 mt-0.5">Alerta inmediata a equipos de riesgo y operaciones.</p>
              </div>
              <div className="p-2.5 rounded-lg bg-orange-950/30 border border-orange-800/40 text-orange-300">
                <div className="font-bold">M 6.0 - 6.9 — Fuerte</div>
                <p className="text-[11px] text-orange-400/80 mt-0.5">Verificación de infraestructura regional y líneas de vida.</p>
              </div>
              <div className="p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-cyan-300">
                <div className="font-bold">M 4.0 - 5.9 — Moderado</div>
                <p className="text-[11px] text-cyan-400/80 mt-0.5">Registro en historial analítico y monitoreo preventivo.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
