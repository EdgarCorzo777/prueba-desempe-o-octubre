from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class KPIResponse(BaseModel):
    total_events_24h: int
    max_magnitude_24h: float
    # Contexto del evento de magnitud máxima en la ventana consultada
    max_magnitude_place: Optional[str] = None
    max_magnitude_event_time: Optional[datetime] = None
    avg_magnitude_24h: float
    tsunami_alerts_24h: int
    quality_score: float
    last_data_update: Optional[datetime]
    freshness_delay_minutes: float

class EventItem(BaseModel):
    event_id: str
    magnitude: float
    mag_type: Optional[str]
    place: str
    event_time: datetime
    updated_time: datetime
    tsunami: bool
    sig: Optional[int]
    status: Optional[str]
    event_type: Optional[str]
    longitude: float
    latitude: float
    depth_km: float
    severity_level: str
    url: Optional[str]

class PaginatedEventsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    events: List[EventItem]

class TimeSeriesPoint(BaseModel):
    hour: str
    count: int
    max_magnitude: float

class MagnitudeDistItem(BaseModel):
    severity: str
    count: int

class RegionCountItem(BaseModel):
    region: str
    count: int
    max_magnitude: float

class ReportItem(BaseModel):
    report_id: str
    report_date: date
    executive_summary: str
    metrics: Dict[str, Any]
    ai_model: str
    generation_status: str
    tokens_used: int
    latency_ms: float
    created_at: datetime

class PipelineStatusResponse(BaseModel):
    latest_ingestion_time: Optional[datetime]
    latest_ingestion_status: str
    events_in_bronze: int
    events_in_silver: int
    events_in_gold: int
    quarantined_records_count: int
    quality_score: float
    freshness_delay_minutes: float
    dags_status: List[Dict[str, Any]]

class QuarantineItem(BaseModel):
    quarantine_id: int
    raw_event_id: Optional[str]
    execution_id: str
    rejection_reason: str
    failed_rules: List[str]
    raw_payload: Dict[str, Any]
    quarantined_at: datetime

class PaginatedQuarantineResponse(BaseModel):
    total: int
    page: int
    page_size: int
    records: List[QuarantineItem]

class BackfillRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=60)
    min_magnitude: float = Field(default=2.5, ge=0.0, le=10.0)

class BackfillResponse(BaseModel):
    message: str
    execution_id: str
    period: str
    raw_events_fetched: int
    valid_promoted_to_gold: int
    quarantined: int
    quality_score: float

class ChatRequest(BaseModel):
    question: str
    context_window_hours: Optional[int] = 24

class ChatResponse(BaseModel):
    question: str
    answer: str
    data_points: Dict[str, Any]
    period_consulted: str
    ai_model: str
    latency_ms: float
    is_fallback: bool

class AnomalyAlertItem(BaseModel):
    alert_id: int
    alert_type: str
    region: str
    period_start: datetime
    period_end: datetime
    z_score: float
    event_count: int
    avg_magnitude: float
    explanation: str
    created_at: datetime
