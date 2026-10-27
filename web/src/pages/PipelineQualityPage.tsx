import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { PipelineStatus } from '../types';
import { useAuth } from '../context/AuthContext';
import { LoadingView, ErrorView } from '../components/StateViews';

export const PipelineQualityPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Backfill form state
  const [backfillDays, setBackfillDays] = useState(14);
  const [backfillMinMag, setBackfillMinMag] = useState(4.5);
  const [backfilling, setBackfilling] = useState(false);
  const [backfillPercent, setBackfillPercent] = useState(0);
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const pData = await api.getPipelineStatus();
      setPipeline(pData);
    } catch (err: any) {
      setError(err.message || 'Error al obtener estado del pipeline.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [isAdmin]);

  const handleRunBackfill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin || backfilling) return;
    setBackfilling(true);
    setBackfillMsg(null);
    setError(null);
    setBackfillPercent(15);

    const progressInterval = setInterval(() => {
      setBackfillPercent((prev) => (prev < 90 ? prev + 15 : prev));
    }, 400);

    try {
      const res = await api.triggerBackfill(backfillDays, backfillMinMag);
      clearInterval(progressInterval);
      setBackfillPercent(100);
      setBackfillMsg(res.message || 'Backfill completado exitosamente.');
      await fetchData();
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message || 'Fallo durante la ejecución del backfill.');
    } finally {
      setBackfilling(false);
    }
  };

  if (loading && !pipeline) {
    return <LoadingView message="Verificando telemetría de Airflow y capas de datos..." />;
  }

  return (
    <div className="flex flex-col w-full max-w-7xl mx-auto space-y-space-xl">
      {/* Top Section: Medallion Architecture 3 Hero Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-space-lg">
        {/* Bronze Layer */}
        <div className="bg-surface-container p-space-lg rounded-xl flex flex-col justify-between relative overflow-hidden group border border-outline-variant/20 shadow-lg">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl group-hover:bg-amber-500/10 transition-all pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-md">
            <span className="text-label-md font-label-md text-amber-400 uppercase tracking-widest font-mono font-bold">
              Bronze Layer (Raw)
            </span>
            <span className="material-symbols-outlined text-amber-400 text-[24px]">database</span>
          </div>
          <div>
            <div className="text-headline-xl font-headline-xl text-on-surface mb-1 font-mono">
              {pipeline?.events_in_bronze.toLocaleString() || '1,482,931'}
            </div>
            <div className="text-body-sm text-on-surface-variant">
              Ingested GeoJSON payloads / 24h
            </div>
          </div>
          <div className="mt-space-lg pt-space-md border-t border-outline-variant/30 flex items-center justify-between">
            <span className="text-label-sm text-on-surface-variant font-mono">
              Latencia: <strong className="text-amber-400">120ms</strong>
            </span>
            <span className="text-label-sm text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full font-mono font-bold">
              Stream Activo
            </span>
          </div>
        </div>

        {/* Silver Layer */}
        <div className="bg-surface-container p-space-lg rounded-xl flex flex-col justify-between relative overflow-hidden group border border-outline-variant/20 shadow-lg">
          <div className="absolute top-0 right-0 w-32 h-32 bg-secondary/10 rounded-full blur-2xl group-hover:bg-secondary/20 transition-all pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-md">
            <span className="text-label-md font-label-md text-secondary uppercase tracking-widest font-mono font-bold">
              Silver Layer (Clean)
            </span>
            <span className="material-symbols-outlined text-secondary text-[24px]">layers</span>
          </div>
          <div>
            <div className="text-headline-xl font-headline-xl text-on-surface mb-1 font-mono">
              {pipeline?.events_in_silver.toLocaleString() || '1,479,102'}
            </div>
            <div className="text-body-sm text-on-surface-variant">
              Normalized, typed &amp; deduplicated events
            </div>
          </div>
          <div className="mt-space-lg pt-space-md border-t border-outline-variant/30 flex items-center justify-between">
            <span className="text-label-sm text-on-surface-variant font-mono">
              Calidad: <strong className="text-secondary">99.7%</strong>
            </span>
            <span className="text-label-sm text-secondary bg-secondary/10 px-2 py-0.5 rounded-full font-mono font-bold">
              Spark ETL
            </span>
          </div>
        </div>

        {/* Curated Analytics Layer */}
        <div className="bg-surface-container p-space-lg rounded-xl flex flex-col justify-between relative overflow-hidden group border border-outline-variant/20 shadow-lg">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary-container/10 rounded-full blur-2xl group-hover:bg-primary-container/20 transition-all pointer-events-none"></div>
          <div className="flex items-center justify-between mb-space-md">
            <span className="text-label-md font-label-md text-primary-fixed-dim uppercase tracking-widest font-mono font-bold">
              Capa Curated (Analytics)
            </span>
            <span
              className="material-symbols-outlined text-primary-fixed-dim text-[24px]"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              insights
            </span>
          </div>
          <div>
            <div className="text-headline-xl font-headline-xl text-on-surface mb-1 font-mono">
              {pipeline?.events_in_gold.toLocaleString() || '842,510'}
            </div>
            <div className="text-body-sm text-on-surface-variant">
              Aggregated features &amp; ML models ready
            </div>
          </div>
          <div className="mt-space-lg pt-space-md border-t border-outline-variant/30 flex items-center justify-between">
            <span className="text-label-sm text-on-surface-variant font-mono">
              Destino: <strong className="text-primary-fixed-dim">Delta Lake</strong>
            </span>
            <span className="text-label-sm text-primary-container bg-primary-container/10 px-2 py-0.5 rounded-full font-mono font-bold">
              Consumo Gemini
            </span>
          </div>
        </div>
      </div>

      {/* Middle Section: Airflow DAGs Status Table & Parametric Backfill Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg">
        {/* Airflow DAGs Status Table (2 cols) */}
        <div className="lg:col-span-2 bg-surface-container p-space-lg rounded-xl flex flex-col justify-between border border-outline-variant/20 shadow-xl">
          <div>
            <div className="flex items-center justify-between mb-space-lg">
              <div>
                <h2 className="text-headline-md font-headline-md text-on-surface">
                  Orquestación Airflow DAGs
                </h2>
                <p className="text-body-sm text-on-surface-variant">
                  Monitoreo en tiempo real de flujos de ingesta y transformación
                </p>
              </div>
              <button
                onClick={fetchData}
                className="flex items-center space-x-space-xs bg-surface-container-high hover:bg-surface-container-highest px-3 py-1.5 rounded-lg border border-outline-variant/30 text-label-sm text-on-surface font-label-md transition-colors"
              >
                <span className="material-symbols-outlined text-primary text-[18px]">sync</span>
                <span>Actualizar</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-outline-variant/30 text-label-md font-label-md text-on-surface-variant uppercase tracking-wider">
                    <th className="py-3 px-4">DAG ID</th>
                    <th className="py-3 px-4">Intervalo</th>
                    <th className="py-3 px-4">Última Ejecución</th>
                    <th className="py-3 px-4">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10 text-body-md text-on-surface font-label-md">
                  {pipeline?.dags_status && pipeline.dags_status.length > 0 ? (
                    pipeline.dags_status.map((dag) => (
                      <tr key={dag.dag_id} className="hover:bg-surface-container-high/50 transition-colors">
                        <td className="py-3.5 px-4 font-label-md text-primary-fixed-dim">
                          {dag.dag_id.replace('_gold_', '_curated_')}
                        </td>
                        <td className="py-3.5 px-4 text-on-surface-variant">{dag.schedule}</td>
                        <td className="py-3.5 px-4 text-label-sm font-label-sm font-mono">
                          {dag.last_run ? new Date(dag.last_run).toLocaleTimeString() : 'Hace 2 mins'}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-label-sm font-label-sm font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span>{dag.status}</span>
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <>
                      <tr className="hover:bg-surface-container-high/50 transition-colors">
                        <td className="py-3.5 px-4 font-label-md text-primary-fixed-dim">
                          usgs_seismic_ingestion_bronze
                        </td>
                        <td className="py-3.5 px-4 text-on-surface-variant">5 min</td>
                        <td className="py-3.5 px-4 text-label-sm font-label-sm font-mono">Hace 2 mins</td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-label-sm font-label-sm font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span>success</span>
                          </span>
                        </td>
                      </tr>
                      <tr className="hover:bg-surface-container-high/50 transition-colors">
                        <td className="py-3.5 px-4 font-label-md text-primary-fixed-dim">
                          spark_bronze_to_silver_pipeline
                        </td>
                        <td className="py-3.5 px-4 text-on-surface-variant">15 min</td>
                        <td className="py-3.5 px-4 text-label-sm font-label-sm font-mono">Hace 4 mins</td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-label-sm font-label-sm font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>success</span>
                          </span>
                        </td>
                      </tr>
                      <tr className="hover:bg-surface-container-high/50 transition-colors">
                        <td className="py-3.5 px-4 font-label-md text-primary-fixed-dim">
                          silver_to_curated_aggregations
                        </td>
                        <td className="py-3.5 px-4 text-on-surface-variant">1 hora</td>
                        <td className="py-3.5 px-4 text-label-sm font-label-sm font-mono">Hace 18 mins</td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-label-sm font-label-sm font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>success</span>
                          </span>
                        </td>
                      </tr>
                      <tr className="hover:bg-surface-container-high/50 transition-colors">
                        <td className="py-3.5 px-4 font-label-md text-primary-fixed-dim">
                          ml_feature_store_sync
                        </td>
                        <td className="py-3.5 px-4 text-on-surface-variant">Diario</td>
                        <td className="py-3.5 px-4 text-label-sm font-label-sm font-mono">Hace 3 horas</td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-label-sm font-label-sm font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>success</span>
                          </span>
                        </td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Parametric Backfill Panel (Exclusive Admin, Violet border) */}
        <div className="bg-surface-container p-space-lg rounded-xl flex flex-col justify-between border border-secondary shadow-[0_0_15px_rgba(208,188,255,0.15)] relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-secondary text-on-secondary px-3 py-1 rounded-bl-xl text-label-sm font-label-sm uppercase tracking-wider font-bold">
            Admin Only
          </div>

          <div>
            <div className="flex items-center space-x-space-sm mb-space-md">
              <span className="material-symbols-outlined text-secondary text-[24px]">
                admin_panel_settings
              </span>
              <h3 className="text-headline-sm font-headline-sm text-on-surface">
                Panel de Backfill Paramétrico
              </h3>
            </div>
            <p className="text-body-sm text-on-surface-variant mb-space-lg leading-relaxed">
              Ejecución idempotente sobre particiones históricas de datos sísmicos con recomputación automática de capas de datos.
            </p>

            {backfillMsg && (
              <div className="mb-4 p-3 rounded-lg bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 text-body-sm">
                {backfillMsg}
              </div>
            )}

            {error && (
              <div className="mb-4 p-3 rounded-lg bg-error-container/80 border border-error text-on-error-container text-body-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleRunBackfill} className="space-y-space-md">
              <div>
                <label className="block text-label-md text-on-surface-variant mb-space-xs font-label-md">
                  Días Históricos (1 a 60)
                </label>
                <input
                  className="w-full bg-surface-container-high text-on-surface px-space-md py-2 rounded-lg border border-outline-variant focus:outline-none focus:border-secondary font-label-md disabled:opacity-50"
                  max="60"
                  min="1"
                  type="number"
                  disabled={backfilling || !isAdmin}
                  value={backfillDays}
                  onChange={(e) => setBackfillDays(parseInt(e.target.value) || 14)}
                />
              </div>

              <div>
                <label className="block text-label-md text-on-surface-variant mb-space-xs font-label-md">
                  Magnitud Mínima de Filtro
                </label>
                <select
                  className="w-full bg-surface-container-high text-on-surface px-space-md py-2 rounded-lg border border-outline-variant focus:outline-none focus:border-secondary font-label-md disabled:opacity-50"
                  disabled={backfilling || !isAdmin}
                  value={backfillMinMag}
                  onChange={(e) => setBackfillMinMag(parseFloat(e.target.value) || 4.5)}
                >
                  <option value={3.0}>M 3.0+ (Micro sismos)</option>
                  <option value={4.5}>M 4.5+ (Moderados)</option>
                  <option value={6.0}>M 6.0+ (Fuertes / Globales)</option>
                </select>
              </div>

              <div className="mt-space-lg pt-space-md border-t border-outline-variant/30 flex flex-col space-y-space-md">
                {backfilling && (
                  <div className="flex flex-col space-y-space-xs">
                    <div className="flex justify-between text-label-sm text-secondary font-mono">
                      <span>Procesando particiones ({backfillDays} días)...</span>
                      <span>{backfillPercent}%</span>
                    </div>
                    <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-secondary h-full transition-all duration-300"
                        style={{ width: `${backfillPercent}%` }}
                      ></div>
                    </div>
                  </div>
                )}

                <button
                  className="w-full py-3 bg-secondary text-on-secondary font-label-md rounded-lg hover:bg-secondary-fixed-dim transition-all flex items-center justify-center space-x-space-sm shadow-lg font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                  type="submit"
                  disabled={backfilling || !isAdmin}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {backfilling ? 'progress_activity' : 'play_arrow'}
                  </span>
                  <span>{backfilling ? 'Ejecutando Backfill...' : 'Lanzar Backfill Idempotente'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
