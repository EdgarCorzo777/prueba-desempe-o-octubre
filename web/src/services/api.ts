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

  // Chat — siempre vía backend (grounding Gold + sanitización de prompt injection en el servidor)
  async sendChatMessage(question: string): Promise<ChatResponse> {
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
