import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { sseService } from '../services/sse';
import { KPIStats, SeismicEvent, TimeSeriesPoint, MagnitudeDistItem, RegionCountItem } from '../types';
import { EarthquakeMap } from '../components/EarthquakeMap';
import { LoadingView, ErrorView } from '../components/StateViews';

const PAGE_SIZE = 10;

export const DashboardPage: React.FC = () => {
  const [kpis, setKpis] = useState<KPIStats | null>(null);
  const [events, setEvents] = useState<SeismicEvent[]>([]);
  const [timeseries, setTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [magDist, setMagDist] = useState<MagnitudeDistItem[]>([]);
  const [topRegions, setTopRegions] = useState<RegionCountItem[]>([]);
  // Timeframe: 24 (24 Horas), 168 (7 Días), 720 (30 Días)
  const [timeframeHours, setTimeframeHours] = useState<number>(720);

  const [selectedEvent, setSelectedEvent] = useState<SeismicEvent | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalEventsCount, setTotalEventsCount] = useState<number>(0);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpiRes, eventsRes, tsRes, distRes, regRes] = await Promise.all([
        api.getKpis(timeframeHours),
        api.getEvents({
          page,
          page_size: PAGE_SIZE,
        }),
        api.getTimeSeries(timeframeHours),
        api.getMagnitudeDistribution(timeframeHours),
        api.getTopRegions(timeframeHours, 5),
      ]);

      setKpis(kpiRes);
      setEvents(eventsRes.events);
      setTotalEventsCount(eventsRes.total);
      setTotalPages(Math.ceil(eventsRes.total / PAGE_SIZE) || 1);
      setTimeseries(tsRes);
      setMagDist(distRes);
      setTopRegions(regRes);
    } catch (err: any) {
      setError(err.message || 'Error cargando datos del dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeframeHours, page]);

  // Cambiar la ventana temporal reinicia la paginación.
  // NOTA: separado del efecto anterior — el reset dentro del efecto que depende
  // de `page` hacía que "Anterior/Siguiente" volvieran inmediatamente a la página 1.
  useEffect(() => {
    setPage(1);
  }, [timeframeHours]);

  // Refresco silencioso ante eventos en vivo (SSE): actualiza KPIs y gráficas
  // sin recargar la pantalla ni disparar el estado de loading.
  const quietTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    const quietRefresh = async () => {
      try {
        const [kpiRes, tsRes, distRes, regRes] = await Promise.all([
          api.getKpis(timeframeHours),
          api.getTimeSeries(timeframeHours),
          api.getMagnitudeDistribution(timeframeHours),
          api.getTopRegions(timeframeHours, 5),
        ]);
        setKpis(kpiRes);
        setTimeseries(tsRes);
        setMagDist(distRes);
        setTopRegions(regRes);
      } catch {
        // Silencioso: ante fallo puntual se conservan los datos vigentes.
      }
    };

    const unsubscribe = sseService.subscribe((newEvent) => {
      setTotalEventsCount((c) => c + 1);
      // Solo la página 1 recibe el evento en vivo al tope de la tabla;
      // en otras páginas no corresponde mezclar el recién llegado.
      if (page === 1) {
        setEvents((prev) => [newEvent, ...prev.slice(0, PAGE_SIZE - 1)]);
      }
      // Debounce ~1.5 s: agrupa ráfagas de eventos y refresca estadísticas una sola vez.
      if (quietTimer.current) {
        clearTimeout(quietTimer.current);
      }
      quietTimer.current = setTimeout(quietRefresh, 1500);
    });
    return () => {
      unsubscribe();
      if (quietTimer.current) {
        clearTimeout(quietTimer.current);
      }
    };
  }, [timeframeHours, page]);

  if (loading && !kpis) {
    return <LoadingView message="Cargando telemetría del Observatorio Global SismoWatch..." />;
  }

  if (error && !kpis) {
    return <ErrorView message={error} onRetry={fetchData} />;
  }

  // Distribution calculations using severity enum: LOW (<4), MODERATE (4-5), HIGH/CRITICAL (5+)
  const microCount = magDist.filter((d) => d.severity === 'LOW').reduce((a, b) => a + b.count, 0);
  const minorCount = magDist.filter((d) => d.severity === 'MODERATE').reduce((a, b) => a + b.count, 0);
  const majorCount = magDist.filter((d) => d.severity === 'HIGH' || d.severity === 'CRITICAL').reduce((a, b) => a + b.count, 0);
  const distTotal = Math.max(1, microCount + minorCount + majorCount);

  // Serie temporal: el backend agrega por día si la ventana supera 48 h, por hora en caso contrario.
  const isDailySeries = timeframeHours > 48;
  const tsSlice = timeseries.slice(-10);
  const tsMax = Math.max(1, ...timeseries.map((t) => t.count));
  const fmtAxisLabel = (hourStr: string) => {
    if (!hourStr) return '—';
    if (isDailySeries) {
      const d = new Date(`${hourStr}T12:00:00`);
      return isNaN(d.getTime())
        ? hourStr.slice(5)
        : d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }); // "29 oct."
    }
    // Punto horario "YYYY-MM-DD HH:00" -> "HH:00"
    const parts = hourStr.split(' ');
    return parts.length > 1 ? parts[1].trim() : hourStr.slice(-5);
  };

  return (
    <div className="flex flex-col w-full max-w-7xl mx-auto px-margin py-space-lg space-y-space-xl">
      {/* Top Control Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-low p-space-md rounded-xl shadow-md border border-outline-variant/20">
        {/* Time Windows */}
        <div className="flex items-center space-x-space-xs bg-surface-container p-1 rounded-lg">
          <button
            onClick={() => { setTimeframeHours(24); setPage(1); }}
            className={`px-space-md py-1.5 rounded-md text-label-md transition-all ${
              timeframeHours === 24
                ? 'bg-primary-container text-on-primary-container font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
            }`}
          >
            24 Horas
          </button>
          <button
            onClick={() => { setTimeframeHours(168); setPage(1); }}
            className={`px-space-md py-1.5 rounded-md text-label-md transition-all ${
              timeframeHours === 168
                ? 'bg-primary-container text-on-primary-container font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
            }`}
          >
            7 Días
          </button>
          <button
            onClick={() => { setTimeframeHours(720); setPage(1); }}
            className={`px-space-md py-1.5 rounded-md text-label-md transition-all ${
              timeframeHours === 720
                ? 'bg-primary-container text-on-primary-container font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
            }`}
          >
            30 Días
          </button>
        </div>

        {/* Live Indicator */}
        <div className="flex items-center space-x-space-sm text-label-md text-on-surface-variant font-mono">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span>En vivo · registro completo de la Red Global</span>
        </div>
      </div>

      {/* KPI Stat Cards (6) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
        {/* Stat 1: Total Eventos */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-lg relative overflow-hidden group hover:translate-y-[-2px] transition-transform border border-outline-variant/20">
          <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-bl-full pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-sm">
            <span className="text-label-md text-on-surface-variant uppercase tracking-widest font-label-md">
              Total Eventos
            </span>
            <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center text-primary shadow-sm">
              <span className="material-symbols-outlined text-[18px]">drive_file_rename_outline</span>
            </div>
          </div>
          <div className="flex items-baseline space-x-space-sm">
            <span className="text-headline-lg font-headline-lg text-primary">
              {kpis?.total_events_24h.toLocaleString() || '0'}
            </span>
          </div>
          <div className="text-label-sm text-on-surface-variant mt-1">
            Frescura: {kpis?.freshness_delay_minutes !== undefined ? kpis.freshness_delay_minutes.toFixed(1) : '—'} min
          </div>
        </div>

        {/* Stat 2: Magnitud Máxima */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-lg relative overflow-hidden group hover:translate-y-[-2px] transition-transform border border-outline-variant/20">
          <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/5 rounded-bl-full pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-sm">
            <span className="text-label-md text-on-surface-variant uppercase tracking-widest font-label-md">
              Magnitud Máxima
            </span>
            <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center text-orange-400 shadow-sm">
              <span
                className="material-symbols-outlined text-[18px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                local_fire_department
              </span>
            </div>
          </div>
          <div className="flex items-baseline space-x-space-sm">
            <span className="text-headline-lg font-headline-lg text-orange-400">
              M {kpis?.max_magnitude_24h !== undefined ? kpis.max_magnitude_24h.toFixed(1) : '0.0'}
            </span>
            <span className="text-label-sm text-on-surface-variant font-label-sm truncate max-w-[120px]">
              {kpis?.max_magnitude_place || '—'}
            </span>
          </div>
        </div>

        {/* Stat 3: Magnitud Promedio */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-lg relative overflow-hidden group hover:translate-y-[-2px] transition-transform border border-outline-variant/20">
          <div className="absolute top-0 right-0 w-24 h-24 bg-secondary/5 rounded-bl-full pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-sm">
            <span className="text-label-md text-on-surface-variant uppercase tracking-widest font-label-md">
              Magnitud Promedio
            </span>
            <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center text-secondary shadow-sm">
              <span className="material-symbols-outlined text-[18px]">bar_chart</span>
            </div>
          </div>
          <div className="flex items-baseline space-x-space-sm">
            <span className="text-headline-lg font-headline-lg text-secondary">
              M {kpis?.avg_magnitude_24h !== undefined ? kpis.avg_magnitude_24h.toFixed(1) : '0.0'}
            </span>
          </div>
          <div className="text-label-sm text-on-surface-variant mt-1">
            Ventana: últimas {timeframeHours} h
          </div>
        </div>

        {/* Stat 4: Alertas Tsunami */}
        <div
          className={`bg-surface-container-low p-space-lg rounded-xl shadow-lg relative overflow-hidden group hover:translate-y-[-2px] transition-transform border ${
            kpis && kpis.tsunami_alerts_24h > 0 ? 'border-error/60 bg-error-container/20' : 'border-outline-variant/20'
          }`}
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-error/10 rounded-bl-full pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-sm">
            <span className="text-label-md text-on-surface-variant uppercase tracking-widest font-label-md">
              Alertas Tsunami
            </span>
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-sm ${
                kpis && kpis.tsunami_alerts_24h > 0
                  ? 'bg-error-container text-error animate-pulse'
                  : 'bg-surface-container text-on-surface-variant'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">tsunami</span>
            </div>
          </div>
          <div className="flex items-baseline space-x-space-sm">
            <span
              className={`text-headline-lg font-headline-lg ${
                kpis && kpis.tsunami_alerts_24h > 0 ? 'text-error' : 'text-on-surface'
              }`}
            >
              {kpis?.tsunami_alerts_24h || 0} {kpis?.tsunami_alerts_24h === 1 ? 'Alerta' : 'Alertas'}
            </span>
            <span
              className={`text-label-sm font-label-sm ${
                kpis && kpis.tsunami_alerts_24h > 0 ? 'text-error animate-pulse' : 'text-emerald-400'
              }`}
            >
              {kpis && kpis.tsunami_alerts_24h > 0 ? 'Activa' : 'Seguro'}
            </span>
          </div>
        </div>

        {/* Stat 5: Puntaje de Calidad */}
        <div
          className={`bg-surface-container-low p-space-lg rounded-xl shadow-lg relative overflow-hidden group hover:translate-y-[-2px] transition-transform border ${
            kpis && kpis.quality_score >= 90 ? 'border-emerald-500/40' : kpis ? 'border-amber-500/40' : 'border-outline-variant/20'
          }`}
        >
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-bl-full pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-sm">
            <span className="text-label-md text-on-surface-variant uppercase tracking-widest font-label-md">
              Puntaje Calidad
            </span>
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-sm ${
                kpis && kpis.quality_score >= 90
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'bg-surface-container text-amber-400'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">verified</span>
            </div>
          </div>
          <div className="flex items-baseline space-x-space-sm">
            <span
              className={`text-headline-lg font-headline-lg ${
                kpis && kpis.quality_score >= 90 ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {kpis?.quality_score !== undefined ? `${kpis.quality_score.toFixed(1)}%` : '—'}
            </span>
          </div>
          <div className="text-label-sm text-on-surface-variant mt-1">
            Registros validados vs cuarentena
          </div>
        </div>

        {/* Stat 6: Última Actualización */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-lg relative overflow-hidden group hover:translate-y-[-2px] transition-transform border border-outline-variant/20">
          <div className="absolute top-0 right-0 w-24 h-24 bg-secondary/5 rounded-bl-full pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-sm">
            <span className="text-label-md text-on-surface-variant uppercase tracking-widest font-label-md">
              Última Actualización
            </span>
            <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center text-secondary shadow-sm">
              <span className="material-symbols-outlined text-[18px]">schedule</span>
            </div>
          </div>
          <div className="flex items-baseline space-x-space-sm">
            <span className="text-headline-lg font-headline-lg text-secondary font-mono text-[1.75rem]">
              {kpis?.last_data_update
                ? new Date(kpis.last_data_update).toLocaleTimeString('es-CO', { hour12: false })
              : '—'}
            </span>
          </div>
          <div className="text-label-sm text-on-surface-variant mt-1 truncate">
            {kpis?.last_data_update
              ? `${new Date(kpis.last_data_update).toLocaleDateString('es-CO')} · hora local`
              : 'Sin cargas registradas'}
          </div>
        </div>
      </div>

      {/* Central Geospatial Seismological Map Block */}
      <div className="bg-surface-container-low rounded-xl shadow-xl overflow-hidden relative flex flex-col h-[520px] border border-outline-variant/30">
        <div className="absolute top-4 left-4 z-10 bg-surface/90 backdrop-blur-md px-space-md py-2 rounded-lg border border-outline-variant flex items-center space-x-space-sm shadow-lg pointer-events-none">
          <span className="material-symbols-outlined text-primary text-[20px]">globe_asia</span>
          <div>
            <div className="text-label-md font-bold text-on-surface">Mapa Epicentral Global</div>
            <div className="text-label-sm text-on-surface-variant">CartoDB Dark Matter Layer</div>
          </div>
        </div>

        {/* Legend overlay */}
        <div className="absolute bottom-4 left-4 z-10 bg-surface/90 backdrop-blur-md px-space-md py-2 rounded-lg border border-outline-variant flex items-center space-x-space-md shadow-lg pointer-events-none">
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            <span className="text-label-sm text-on-surface-variant">&lt;4.0</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-primary-container"></span>
            <span className="text-label-sm text-on-surface-variant">4.0-4.9</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-400"></span>
            <span className="text-label-sm text-on-surface-variant">5.0-6.4</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-error"></span>
            <span className="text-label-sm text-on-surface-variant">&gt;=6.5</span>
          </div>
        </div>

        {/* Map Container */}
        <div className="w-full h-full relative flex-1">
          <EarthquakeMap
            events={events}
            selectedEvent={selectedEvent}
            onSelectEvent={(ev) => setSelectedEvent(ev)}
          />
        </div>
      </div>

      {/* Row of Analytical Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-md">
        {/* Chart 1: Hourly Activity */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-xl flex flex-col justify-between border border-outline-variant/20">
          <div className="flex items-center justify-between mb-space-md">
            <div className="text-headline-sm font-headline-sm text-on-surface">
            {isDailySeries ? 'Actividad por Día' : 'Actividad por Hora'}
          </div>
            <span className="material-symbols-outlined text-primary">show_chart</span>
          </div>
          <div className="h-48 flex items-end justify-between gap-1 pt-4 px-2">
            {tsSlice.length > 0
              ? tsSlice.map((pt, i) => {
                  const heightPercent = Math.max(15, Math.min(100, Math.round((pt.count / tsMax) * 100)));
                  return (
                    <div
                      key={i}
                      className="w-full bg-surface-container rounded-t flex flex-col justify-end h-full group relative"
                      title={`${pt.hour}: ${pt.count} sismos`}
                    >
                      <div
                        className="w-full bg-primary/40 rounded-t group-hover:bg-primary-container transition-colors"
                        style={{ height: `${heightPercent}%` }}
                      ></div>
                    </div>
                  );
                })
              : (
                  <div className="w-full h-full flex items-center justify-center">
                    <p className="text-label-md text-on-surface-variant text-center">
                      Sin actividad registrada en la ventana seleccionada
                    </p>
                  </div>
                )}
          </div>
          <div className="flex justify-between text-label-sm text-on-surface-variant mt-2 pt-2 border-t border-outline-variant">
            {tsSlice.length > 0 ? (
              <>
                <span>{fmtAxisLabel(tsSlice[0].hour)}</span>
                {tsSlice.length >= 3 && (
                  <span>{fmtAxisLabel(tsSlice[Math.floor((tsSlice.length - 1) / 2)].hour)}</span>
                )}
                <span>{fmtAxisLabel(tsSlice[tsSlice.length - 1].hour)}</span>
              </>
            ) : (
              <>
                <span>—</span>
                <span>—</span>
                <span>—</span>
              </>
            )}
          </div>
        </div>

        {/* Chart 2: Magnitude Distribution */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-xl flex flex-col justify-between border border-outline-variant/20">
          <div className="flex items-center justify-between mb-space-md">
            <div className="text-headline-sm font-headline-sm text-on-surface">Distribución por Magnitud</div>
            <span className="material-symbols-outlined text-secondary">donut_large</span>
          </div>
          <div className="space-y-space-md my-auto">
            <div>
              <div className="flex justify-between text-label-md mb-1">
                <span className="text-on-surface-variant">Micro (&lt;3.0)</span>
                <span className="text-on-surface font-bold">{microCount} eventos</span>
              </div>
              <div className="w-full h-2 bg-surface-container rounded-full overflow-hidden">
                <div
                  className="bg-emerald-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.round((microCount / distTotal) * 100)}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-label-md mb-1">
                <span className="text-on-surface-variant">Menor (3.0 - 4.9)</span>
                <span className="text-on-surface font-bold">{minorCount} eventos</span>
              </div>
              <div className="w-full h-2 bg-surface-container rounded-full overflow-hidden">
                <div
                  className="bg-primary-container h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.round((minorCount / distTotal) * 100)}%` }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-label-md mb-1">
                <span className="text-on-surface-variant">Moderado/Fuerte (&gt;=5.0)</span>
                <span className="text-on-surface font-bold">{majorCount} eventos</span>
              </div>
              <div className="w-full h-2 bg-surface-container rounded-full overflow-hidden">
                <div
                  className="bg-orange-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.round((majorCount / distTotal) * 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
          <div className="text-label-sm text-on-surface-variant pt-2 border-t border-outline-variant mt-4">
            Basado en los registros acumulados de la Red Global
          </div>
        </div>

        {/* Chart 3: Top Active Regions Leaderboard */}
        <div className="bg-surface-container-low p-space-lg rounded-xl shadow-xl flex flex-col justify-between border border-outline-variant/20">
          <div className="flex items-center justify-between mb-space-md">
            <div className="text-headline-sm font-headline-sm text-on-surface">Regiones Más Activas</div>
            <span className="material-symbols-outlined text-orange-400">leaderboard</span>
          </div>
          <div className="space-y-3 my-auto">
            {topRegions.length > 0 ? (
              topRegions.slice(0, 3).map((r, idx) => {
                const maxReg = Math.max(1, ...topRegions.map((t) => t.count));
                const widthPct = Math.round((r.count / maxReg) * 100);
                const col = idx === 0 ? 'bg-primary' : idx === 1 ? 'bg-secondary' : 'bg-orange-400';
                return (
                  <div key={idx}>
                    <div className="flex justify-between text-body-md mb-1">
                      <span className="text-on-surface font-medium truncate max-w-[200px]">
                        {idx + 1}. {r.region}
                      </span>
                      <span className="text-primary font-bold">{r.count}</span>
                    </div>
                    <div className="w-full h-1.5 bg-surface-container rounded-full overflow-hidden">
                      <div className={`${col} h-full rounded-full`} style={{ width: `${widthPct}%` }}></div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="flex items-center justify-center py-6">
                <p className="text-label-md text-on-surface-variant text-center">
                  Sin regiones activas en la ventana seleccionada
                </p>
              </div>
            )}
          </div>
          <div className="text-label-sm text-on-surface-variant pt-2 border-t border-outline-variant mt-4">
            Índice de impacto sísmico acumulado
          </div>
        </div>
      </div>

      {/* Paginated Seismic Events Table */}
      <div className="bg-surface-container-low rounded-xl shadow-xl overflow-hidden flex flex-col border border-outline-variant/30">
        <div className="p-space-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm border-b border-outline-variant">
          <div>
            <div className="text-headline-sm font-headline-sm text-on-surface">Registro Detallado de Sismos</div>
            <div className="text-body-sm text-on-surface-variant">Mostrando eventos en tiempo real con validación USGS</div>
          </div>
          <div className="flex items-center space-x-space-sm">
            <span className="text-label-sm text-on-surface-variant">
              Total Registros: <strong className="text-primary font-bold">{totalEventsCount.toLocaleString()}</strong>
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container text-label-md text-on-surface-variant uppercase tracking-wider">
                <th className="p-space-md">Magnitud</th>
                <th className="p-space-md">Epicentro / Región</th>
                <th className="p-space-md">Profundidad</th>
                <th className="p-space-md">Tsunami</th>
                <th className="p-space-md">Timestamp (UTC)</th>
                <th className="p-space-md text-right">USGS Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50 text-body-md text-on-surface font-label-md">
              {events.map((ev) => {
                const isCrit = ev.magnitude >= 6.5;
                const isMod = ev.magnitude >= 5.0 && ev.magnitude < 6.5;
                const isLow = ev.magnitude < 4.0;

                const magBadgeClass = isCrit
                  ? 'bg-error-container text-error'
                  : isMod
                  ? 'bg-orange-500/20 text-orange-400'
                  : isLow
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-primary-container/20 text-primary-fixed';

                return (
                  <tr
                    key={ev.event_id}
                    onClick={() => setSelectedEvent(ev)}
                    className="hover:bg-surface-container transition-colors cursor-pointer"
                  >
                    <td className="p-space-md">
                      <span className={`px-2.5 py-1 rounded font-bold text-label-md ${magBadgeClass}`}>
                        M {ev.magnitude.toFixed(1)}
                      </span>
                    </td>
                    <td className="p-space-md font-body-md text-on-surface font-semibold max-w-[280px] truncate">
                      {ev.place}
                    </td>
                    <td className="p-space-md text-on-surface-variant font-mono">
                      {ev.depth_km.toFixed(1)} km
                    </td>
                    <td className="p-space-md">
                      {ev.tsunami ? (
                        <span className="px-2 py-0.5 rounded bg-error/20 text-error text-label-sm font-bold animate-pulse">
                          Sí (Activa)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant text-label-sm">
                          No
                        </span>
                      )}
                    </td>
                    <td className="p-space-md text-on-surface-variant font-mono text-body-sm">
                      {new Date(ev.event_time).toISOString().replace('T', ' ').slice(0, 19)}
                    </td>
                    <td className="p-space-md text-right" onClick={(e) => e.stopPropagation()}>
                      {ev.url ? (
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary hover:underline inline-flex items-center space-x-1"
                        >
                          <span>USGS</span>
                          <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                        </a>
                      ) : (
                        <span className="text-on-surface-variant opacity-40">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-space-md bg-surface-container-low flex items-center justify-between border-t border-outline-variant">
          <div className="text-label-sm text-on-surface-variant font-mono">
            Página {page} de {totalPages}
          </div>
          <div className="flex items-center space-x-space-xs font-label-md">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 bg-surface-container rounded-lg text-label-md text-on-surface-variant hover:text-on-surface disabled:opacity-40 transition-colors"
            >
              ← Anterior
            </button>
            <span className="px-3 py-1 bg-primary text-on-primary rounded-lg text-label-md font-bold">
              {page}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 bg-surface-container rounded-lg text-label-md text-on-surface hover:text-primary disabled:opacity-40 transition-colors"
            >
              Siguiente →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
