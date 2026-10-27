import {
  KPIStats, SeismicEvent, TimeSeriesPoint, MagnitudeDistItem,
  RegionCountItem, DailyReport, PipelineStatus, QuarantineRecord,
  AnomalyAlert, User, ChatResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('sismowatch_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    localStorage.removeItem('sismowatch_token');
    localStorage.removeItem('sismowatch_user');
    window.location.href = '/login';
    throw new Error('Sesión expirada o no autorizada.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Error en la solicitud (HTTP ${res.status})`);
  }
  return res.json();
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    // A failed login must not be handled as an expired session: keep the backend detail.
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errorData.detail || `Error en la solicitud (HTTP ${res.status})`);
    }
    return res.json();
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // KPIs
  async getKpis(hours = 720): Promise<KPIStats> {
    const res = await fetch(`${API_BASE}/api/kpis?hours=${hours}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // Events
  async getEvents(params: {
    min_magnitude?: number;
    max_magnitude?: number;
    region?: string;
    tsunami_only?: boolean;
    event_category?: 'all' | 'sismo' | 'tsunami';
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ total: number; page: number; page_size: number; events: SeismicEvent[] }> {
    const query = new URLSearchParams();
    if (params.min_magnitude !== undefined) query.set('min_magnitude', params.min_magnitude.toString());
    if (params.max_magnitude !== undefined) query.set('max_magnitude', params.max_magnitude.toString());
    if (params.region) query.set('region', params.region);
    if (params.tsunami_only) query.set('tsunami_only', 'true');
    if (params.event_category && params.event_category !== 'all') {
      query.set('event_category', params.event_category);
    }
    if (params.start_date) query.set('start_date', params.start_date);
    if (params.end_date) query.set('end_date', params.end_date);
    if (params.page) query.set('page', params.page.toString());
    query.set('page_size', (params.page_size || 10).toString());
    if (params.page_size) query.set('page_size', params.page_size.toString());

    const res = await fetch(`${API_BASE}/api/events?${query.toString()}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // Statistics
  async getTimeSeries(hours = 24): Promise<TimeSeriesPoint[]> {
    const res = await fetch(`${API_BASE}/api/stats/timeseries?hours=${hours}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getMagnitudeDistribution(hours = 24): Promise<MagnitudeDistItem[]> {
    const res = await fetch(`${API_BASE}/api/stats/magnitude-distribution?hours=${hours}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getTopRegions(hours = 24, limit = 5): Promise<RegionCountItem[]> {
    const res = await fetch(`${API_BASE}/api/stats/top-regions?hours=${hours}&limit=${limit}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // Reports
  async getReports(search?: string): Promise<DailyReport[]> {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`${API_BASE}/api/reports${query}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getReportById(reportId: string): Promise<DailyReport> {
    const res = await fetch(`${API_BASE}/api/reports/${reportId}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  getExportUrl(format: 'csv' | 'html', reportId?: string): string {
    const token = localStorage.getItem('sismowatch_token') || '';
    const query = new URLSearchParams({ format, token });
    if (reportId) query.set('report_id', reportId);
    return `${API_BASE}/api/reports/export?${query.toString()}`;
  },

  // Pipeline & Quality
  async getPipelineStatus(): Promise<PipelineStatus> {
    const res = await fetch(`${API_BASE}/api/pipeline/status`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  async getQuarantineRecords(page = 1, page_size = 20): Promise<{ total: number; page: number; page_size: number; records: QuarantineRecord[] }> {
    const res = await fetch(`${API_BASE}/api/quality/quarantine?page=${page}&page_size=${page_size}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // Admin Actions
  async triggerBackfill(days = 30, min_magnitude = 2.5): Promise<any> {
    const res = await fetch(`${API_BASE}/api/admin/backfill`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ days, min_magnitude })
    });
    return handleResponse(res);
  },

  async regenerateReport(): Promise<DailyReport> {
    const res = await fetch(`${API_BASE}/api/admin/reports/regenerate`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // Anomalies
  async getAnomalies(limit = 20): Promise<AnomalyAlert[]> {
    const res = await fetch(`${API_BASE}/api/anomalies?limit=${limit}`, {
      headers: getAuthHeaders()
    });
    return handleResponse(res);
  },

  // Chat
  async sendChatMessage(question: string): Promise<ChatResponse> {
    const startTime = performance.now();
    const GEMINI_KEY = (import.meta as any).env?.VITE_GEMINI_API_KEY || "";

    // 1. Fetch current certified Gold KPIs, Timeseries, Regions & top events to ground the prompt
    let goldContext = "";
    try {
      const [kpis, eventsRes, timeseries, topRegions, magnitudeDist] = await Promise.all([
        this.getKPIs('24h').catch(() => null),
        this.getEvents(1, 10, 'all').catch(() => null),
        this.getTimeSeries(168).catch(() => []),
        this.getTopRegions(720, 5).catch(() => []),
        this.getMagnitudeDistribution(24).catch(() => [])
      ]);

      // Extract Yesterday and Today from timeseries
      const todayData = timeseries && timeseries.length > 0 ? timeseries[timeseries.length - 1] : null;
      const yesterdayData = timeseries && timeseries.length > 1 ? timeseries[timeseries.length - 2] : null;

      const topList = eventsRes?.events?.slice(0, 5).map(e => 
        `- M${e.magnitude} en ${e.place} | Profundidad: ${e.depth_km} km | Fecha UTC: ${e.event_time} | Alerta Tsunami: ${e.tsunami ? 'SÍ' : 'NO'}`
      ).join("\n") || "No hay eventos destacados";

      const regionsList = topRegions?.slice(0, 5).map((r, i) =>
        `${i + 1}. ${r.region}: ${r.count} sismos (Magnitud máxima: M${r.max_magnitude})`
      ).join("\n") || "No hay datos de regiones";

      const distList = magnitudeDist?.map(m =>
        `- ${m.severity}: ${m.count} sismos`
      ).join("\n") || "No hay datos de distribución";

      goldContext = `
DATOS CERTIFICADOS (OBSERVATORIO SISMoWATCH):
- COMPARATIVA DIARIA (HISTÓRICO CERTIFICADO):
  * HOY (${todayData?.hour ?? '2026-10-27'}): ${todayData?.count ?? 'N/A'} sismos registrados | Magnitud máxima: M${todayData?.max_magnitude ?? 'N/A'}
  * AYER (${yesterdayData?.hour ?? '2026-10-26'}): ${yesterdayData?.count ?? 'N/A'} sismos registrados | Magnitud máxima: M${yesterdayData?.max_magnitude ?? 'N/A'}
- RESUMEN ÚLTIMAS 24 HORAS:
  * Total sismos en red global: ${kpis?.total_events ?? 'N/A'}
  * Magnitud máxima: ${kpis?.max_magnitude ?? 'N/A'}
  * Magnitud promedio: ${kpis?.avg_magnitude ?? 'N/A'}
  * Alertas de tsunami activas: ${kpis?.tsunami_alerts ?? 0}
- DISTRIBUCIÓN POR SEVERIDAD (24H):
${distList}
- REGIONES CON MAYOR ACTIVIDAD (ÚLTIMOS 30 DÍAS):
${regionsList}
- SISMOS MÁS FUERTES RECIENTES:
${topList}
`;
    } catch {
      // Proceed without full context if API call fails
    }

    const systemPrompt = `Eres SismoWatch AI, el asistente analítico y científico oficial de monitoreo sísmico de SismoWatch.
Tu función es responder consultas informativas, técnicas y estadísticas sobre la actividad sísmica registrada en el observatorio.
Todas las consultas se refieren a fenómenos geológicos naturales (terremotos y sismos).
Responde siempre en español con un tono profesional, claro, riguroso y estructurado.

DIRECTRICES OBLIGATORIAS DE RESPUESTA:
1. RIGOR Y PRECISIÓN: Utiliza estrictamente las cifras certificadas del bloque anterior. No inventes eventos, coordenadas ni magnitudes.
2. COMPARATIVAS (AYER VS HOY / TENDENCIAS):
   - Si el usuario solicita comparar ayer con hoy o analizar tendencias, genera OBLIGATORIAMENTE una Tabla Markdown comparando:
     * Fecha
     * Cantidad de sismos registrados
     * Magnitud máxima
     * Variación absoluta y porcentual (+/-)
   - Agrega un análisis conciso de la tendencia geológica observada.
3. DIAGRAMAS Y GRÁFICOS VISUALES:
   - Si el usuario solicita un "diagrama", "gráfico", "ranking" o "barras", incluye SIEMPRE una representación visual en bloque de código ASCII (\`\`\`text ... \`\`\`) con barras proporcionales usando el carácter '█'.
4. TABLAS FORMATO MARKDOWN:
   - Presenta listas de eventos o datos comparativos en tablas Markdown limpias con cabeceras claras (| Métrica | Ayer | Hoy | Variación |).
5. ALERTAS DE TSUNAMI: Menciona siempre el estado de alertas de tsunami cuando sea relevante.`;

    const fullPrompt = `PREGUNTA DEL USUARIO: "${question}"
${goldContext}

Instrucción: Responde a la pregunta del usuario utilizando los datos certificados anteriores de forma precisa, clara y estructurada, incluyendo tablas y diagramas si corresponden.`;

    // 2. Query Google Gemini AI Studio
    const candidateModels = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview"];
    for (const model of candidateModels) {
      try {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_KEY}`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            systemInstruction: { parts: [{ text: systemPrompt }] },
            contents: [{ parts: [{ text: fullPrompt }] }],
            generationConfig: { temperature: 0.2, maxOutputTokens: 2048 }
          })
        });

        if (res.ok) {
          const data = await res.json();
          const answer = data?.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
          if (answer) {
            const latency = Math.round(performance.now() - startTime);
            return {
              question,
              answer,
              data_points: { source: "curated.events", model: `gemini:${model}` },
              period_consulted: "Últimas 24 horas",
              ai_model: `gemini:${model}`,
              latency_ms: latency,
              is_fallback: false
            };
          }
        }
      } catch (err) {
        console.warn(`Gemini model ${model} request failed:`, err);
      }
    }

    // Fallback to backend API if Gemini call fails
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ question })
    });
    return handleResponse(res);
  },

  async askChat(question: string): Promise<ChatResponse> {
    return this.sendChatMessage(question);
  }
};
