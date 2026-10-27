export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'viewer';
  is_active: boolean;
  created_at: string;
}

export interface KPIStats {
  total_events_24h: number;
  max_magnitude_24h: number;
  avg_magnitude_24h: number;
  tsunami_alerts_24h: number;
  quality_score: number;
  last_data_update: string | null;
  freshness_delay_minutes: number;
}

export interface SeismicEvent {
  event_id: string;
  magnitude: number;
  mag_type: string | null;
  place: string;
  event_time: string;
  updated_time: string;
  tsunami: boolean;
  sig: number | null;
  status: string | null;
  event_type: string | null;
  longitude: number;
  latitude: number;
  depth_km: number;
  severity_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  url: string | null;
}

export interface TimeSeriesPoint {
  hour: string;
  count: number;
  max_magnitude: number;
}

export interface MagnitudeDistItem {
  severity: string;
  count: number;
}

export interface RegionCountItem {
  region: string;
  count: number;
  max_magnitude: number;
}

export interface DailyReport {
  report_id: string;
  report_date: string;
  executive_summary: string;
  metrics: {
    total_events: number;
    max_magnitude: number;
    avg_magnitude: number;
    tsunami_alerts: number;
    critical_events: number;
    high_events: number;
    moderate_events: number;
    low_events: number;
    top_regions: Array<{ region: string; count: number; max_mag: number }>;
    notable_events: any[];
  };
  ai_model: string;
  generation_status: 'AI_GENERATED' | 'DETERMINISTIC_FALLBACK';
  tokens_used: number;
  latency_ms: number;
  created_at: string;
}

export interface PipelineStatus {
  latest_ingestion_time: string | null;
  latest_ingestion_status: string;
  events_in_bronze: number;
  events_in_silver: number;
  events_in_gold: number;
  quarantined_records_count: number;
  quality_score: number;
  freshness_delay_minutes: number;
  dags_status: Array<{
    dag_id: string;
    schedule: string;
    state: string;
    last_run: string | null;
    status: string;
  }>;
}

export interface QuarantineRecord {
  quarantine_id: number;
  raw_event_id: string | null;
  execution_id: string;
  rejection_reason: string;
  failed_rules: string[];
  raw_payload: any;
  quarantined_at: string;
}

export interface AnomalyAlert {
  alert_id: number;
  alert_type: string;
  region: string;
  period_start: string;
  period_end: string;
  z_score: number;
  event_count: number;
  avg_magnitude: number;
  explanation: string;
  created_at: string;
}

export interface ChatResponse {
  question: string;
  answer: string;
  data_points?: any;
  period_consulted?: string;
  ai_model?: string;
  latency_ms?: number;
  is_fallback?: boolean;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  period_consulted?: string;
  data_points?: any;
  is_fallback?: boolean;
  ai_model?: string;
  latency_ms?: number;
}
