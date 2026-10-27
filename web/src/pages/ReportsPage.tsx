import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { DailyReport } from '../types';
import { useAuth } from '../context/AuthContext';
import { LoadingView, ErrorView, EmptyView } from '../components/StateViews';

export const ReportsPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getReports();
      setReports(data);
      if (data.length > 0 && !selectedReport) {
        setSelectedReport(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Error al consultar reportes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleRegenerate = async () => {
    if (!isAdmin) return;
    setRegenerating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const newReport = await api.regenerateReport();
      setSuccessMsg('Reporte generado exitosamente.');
      await fetchReports();
      setSelectedReport(newReport);
    } catch (err: any) {
      setError(err.message || 'Error al regenerar reporte.');
    } finally {
      setRegenerating(false);
    }
  };

  if (loading && reports.length === 0) {
    return <LoadingView message="Recuperando resúmenes analíticos del observatorio..." />;
  }

  return (
    <div className="flex flex-col w-full text-on-surface bg-surface space-y-space-lg">
      {/* Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-container-low p-space-lg rounded-xl shadow-md border border-outline-variant/20">
        <div className="flex flex-col space-y-space-xs">
          <span className="text-label-sm font-label-sm text-primary uppercase tracking-widest font-mono">
            Módulo de Inteligencia
          </span>
          <h1 className="text-headline-lg font-headline-lg text-on-surface">
            Historial de Reportes Ejecutivos Asistidos por IA
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-space-sm font-label-md">
          <a
            href={api.getExportUrl('csv')}
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-space-xs px-space-md py-2 bg-surface-container-high hover:bg-surface-bright text-on-surface rounded-lg transition-colors border border-outline-variant/30"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            <span>Exportar CSV</span>
          </a>

          {selectedReport && (
            <a
              href={api.getExportUrl('html', selectedReport.report_id)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-space-xs px-space-md py-2 bg-surface-container-high hover:bg-surface-bright text-on-surface rounded-lg transition-colors border border-outline-variant/30"
            >
              <span className="material-symbols-outlined text-[18px]">print</span>
              <span>Ver / Imprimir HTML</span>
            </a>
          )}

          {isAdmin ? (
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex items-center space-x-space-xs px-space-md py-2 bg-primary-container text-on-primary-container hover:bg-primary-fixed rounded-lg transition-all shadow-[0_0_15px_rgba(0,240,255,0.3)] font-bold disabled:opacity-50"
            >
              <span
                className={`material-symbols-outlined text-[18px] ${
                  regenerating ? 'animate-spin' : ''
                }`}
              >
                {regenerating ? 'progress_activity' : 'auto_awesome'}
              </span>
              <span>{regenerating ? 'Generando con IA...' : 'Regenerar Reporte con IA'}</span>
            </button>
          ) : (
            <div className="text-label-sm text-on-surface-variant px-3 py-2 bg-surface-container rounded-lg border border-outline-variant">
              Regeneración: Solo Admin
            </div>
          )}
        </div>
      </div>

      {successMsg && (
        <div className="p-3 rounded-lg bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-body-sm flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">check_circle</span>
          <span>{successMsg}</span>
        </div>
      )}

      {error && <ErrorView message={error} onRetry={fetchReports} />}

      {/* 2-Column Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
        {/* Left Column: Scrollable List (4 cols) */}
        <div className="lg:col-span-4 bg-surface-container-low rounded-xl p-space-md flex flex-col h-[calc(100vh-16rem)] overflow-hidden shadow-xl border border-outline-variant/20">
          <div className="flex items-center justify-between pb-space-md mb-space-sm border-b border-outline-variant/20">
            <span className="text-label-md font-label-md text-on-surface-variant uppercase">
              Reportes Diarios Oficiales
            </span>
            <span className="text-label-sm font-label-sm text-primary font-mono font-bold">
              {reports.length} Disponibles
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-space-sm pr-1">
            {reports.map((rep) => {
              const isSelected = selectedReport?.report_id === rep.report_id;
              return (
                <div
                  key={rep.report_id}
                  onClick={() => setSelectedReport(rep)}
                  className={`cursor-pointer p-space-md rounded-xl transition-all shadow-sm group ${
                    isSelected
                      ? 'bg-surface-container-high border-l-4 border-primary shadow-md'
                      : 'bg-surface-container hover:bg-surface-container-high'
                  }`}
                >
                  <div className="flex items-center justify-between mb-space-xs">
                    <span className="text-label-sm font-label-sm text-primary font-mono font-bold">
                      {rep.report_date}
                    </span>
                    <span className="text-label-sm font-label-sm px-2 py-0.5 rounded bg-surface text-on-surface-variant font-mono">
                      {rep.generation_status === 'AI_GENERATED' ? 'Generado con IA' : 'Fallback determinista'}
                    </span>
                  </div>
                  <div className="text-headline-sm font-headline-sm text-on-surface mb-space-xs">
                    Reporte Sísmico {rep.report_date}
                  </div>
                  <p className="text-body-sm text-on-surface-variant line-clamp-2">
                    {rep.executive_summary}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Detailed Viewer (8 cols) */}
        <div className="lg:col-span-8 bg-surface-container-low rounded-xl p-space-lg flex flex-col space-y-space-lg shadow-xl h-[calc(100vh-16rem)] overflow-y-auto border border-outline-variant/20">
          {selectedReport ? (
            <>
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-md bg-surface-container p-space-md rounded-xl border border-outline-variant/20">
                <div>
                  <div className="flex items-center space-x-space-sm mb-1">
                    <span className="text-headline-md font-headline-md text-primary font-mono font-bold">
                      {selectedReport.report_date}
                    </span>
                    <span className="px-2 py-0.5 bg-primary-container text-on-primary-container text-label-sm font-label-sm rounded font-bold uppercase">
                      Reporte Certificado
                    </span>
                  </div>
                  <div className="text-body-sm text-on-surface-variant font-mono">
                    ID: {selectedReport.report_id} &bull; Analizado en UTC
                  </div>
                </div>

                <div className="flex items-center space-x-space-md bg-surface-container-high px-space-md py-2 rounded-lg border border-outline-variant/30">
                  <div className="text-right">
                    <div className="text-label-sm text-on-surface-variant font-mono">MOTOR IA</div>
                    <div className="text-label-md font-label-md text-secondary font-mono font-bold">
                      {selectedReport.generation_status === 'AI_GENERATED' ? 'SismoWatch AI' : 'Determinista'}
                    </div>
                  </div>
                  <div className="h-8 w-[1px] bg-outline-variant"></div>
                  <div>
                    <div className="text-label-sm text-on-surface-variant font-mono">LATENCIA</div>
                    <div className="text-label-md font-label-md text-emerald-400 font-mono font-bold">
                      {selectedReport.latency_ms.toFixed(0)}ms
                    </div>
                  </div>
                </div>
              </div>

              {/* Certified Metrics Ribbon (4 Cards) */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-space-md">
                <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between border border-outline-variant/20">
                  <span className="text-label-sm font-label-sm text-on-surface-variant font-bold uppercase">
                    Sismos Procesados
                  </span>
                  <span className="text-headline-md font-headline-md text-primary mt-2 font-mono">
                    {selectedReport.metrics.total_events}
                  </span>
                  <span className="text-label-sm text-on-surface-variant mt-1">
                    {new Date(selectedReport.report_date).toLocaleDateString('es-CO')}
                  </span>
                </div>

                <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between border border-outline-variant/20">
                  <span className="text-label-sm font-label-sm text-on-surface-variant font-bold uppercase">
                    Magnitud Máxima
                  </span>
                  <span className="text-headline-md font-headline-md text-error mt-2 font-mono">
                    M {selectedReport.metrics.max_magnitude.toFixed(1)}
                  </span>
                  <span className="text-label-sm text-on-surface-variant mt-1 truncate max-w-[160px]">
                    {selectedReport.metrics.top_regions?.[0]?.region || '—'}
                  </span>
                </div>

                <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between border border-outline-variant/20">
                  <span className="text-label-sm font-label-sm text-on-surface-variant font-bold uppercase">
                    Magnitud Promedio
                  </span>
                  <span className="text-headline-md font-headline-md text-secondary mt-2 font-mono">
                    M {selectedReport.metrics.avg_magnitude.toFixed(1)}
                  </span>
                  <span className="text-label-sm text-on-surface-variant mt-1">
                    Eventos ≥ M4.0: {selectedReport.metrics.high_events + selectedReport.metrics.critical_events}
                  </span>
                </div>

                <div className="bg-surface-container p-space-md rounded-xl flex flex-col justify-between border border-outline-variant/20">
                  <span className="text-label-sm font-label-sm text-on-surface-variant font-bold uppercase">
                    Alertas Tsunami
                  </span>
                  <span
                    className={`text-headline-md font-headline-md mt-2 font-mono ${
                      selectedReport.metrics.tsunami_alerts > 0 ? 'text-error' : 'text-emerald-400'
                    }`}
                  >
                    {selectedReport.metrics.tsunami_alerts}
                  </span>
                  <span className="text-label-sm text-on-surface-variant mt-1">
                    {selectedReport.metrics.tsunami_alerts > 0 ? 'Bandera tsunami activa' : 'Sin bandera tsunami'}
                  </span>
                </div>
              </div>

              {/* Markdown Executive Summary Container */}
              <div className="bg-surface-container p-space-lg rounded-xl flex flex-col space-y-space-md border border-outline-variant/20">
                <div className="flex items-center space-x-space-sm border-b border-outline-variant pb-space-sm">
                  <span className="material-symbols-outlined text-primary">description</span>
                  <h2 className="text-headline-sm font-headline-sm text-on-surface">
                    Resumen Ejecutivo y Análisis Sintético
                  </h2>
                </div>
                <div className="space-y-space-md text-body-md text-on-surface leading-relaxed whitespace-pre-wrap font-sans">
                  {selectedReport.executive_summary}
                </div>
              </div>

              {/* Telemetry Certification Badge */}
              <div className="bg-gradient-to-r from-surface-container via-surface-container-high to-surface-container p-space-md rounded-xl flex items-center justify-between border border-primary/20">
                <div className="flex items-center space-x-space-md">
                  <div className="w-10 h-10 rounded-full bg-emerald-400/10 flex items-center justify-center text-emerald-400 shrink-0">
                    <span className="material-symbols-outlined">verified</span>
                  </div>
                  <div>
                    <div className="text-label-md font-label-md text-on-surface font-bold">
                      Telemetría Oficial USGS Validada
                    </div>
                    <div className="text-body-sm text-on-surface-variant">
                      Consistencia analítica verificada contra las cifras certificadas de la capa Gold con redacción asistida por IA generativa.
                    </div>
                  </div>
                </div>
                <span className="px-3 py-1 bg-emerald-400/10 text-emerald-400 text-label-sm font-label-sm rounded-full font-mono shrink-0">
                  Cifras verificadas &bull; USGS
                </span>
              </div>
            </>
          ) : (
            <EmptyView message="Seleccione un reporte de la lista lateral para visualizar sus detalles." />
          )}
        </div>
      </div>
    </div>
  );
};
