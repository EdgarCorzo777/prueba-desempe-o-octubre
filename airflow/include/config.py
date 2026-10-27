import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PostgreSQL Configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sismowatch_db")
    
    # Credentials by Role
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "sismowatch_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "sismowatch_db_pass_2026")
    
    INGESTION_USER: str = os.getenv("INGESTION_USER", "ingest_user")
    INGESTION_PASSWORD: str = os.getenv("INGESTION_PASSWORD", "ingest_secret_2026")
    
    TRANSFORM_USER: str = os.getenv("TRANSFORM_USER", "transform_user")
    TRANSFORM_PASSWORD: str = os.getenv("TRANSFORM_PASSWORD", "transform_secret_2026")
    
    API_USER: str = os.getenv("API_USER", "api_user")
    API_PASSWORD: str = os.getenv("API_PASSWORD", "api_secret_2026")
    
    # USGS Feeds
    USGS_REALTIME_FEED_URL: str = os.getenv(
        "USGS_REALTIME_FEED_URL",
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    )
    USGS_HISTORICAL_QUERY_URL: str = os.getenv(
        "USGS_HISTORICAL_QUERY_URL",
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
    )
    
    # Google Gemini AI Studio (Primary LLM Engine)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Local fallback engine
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11438")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemini:3.5-flash-lite")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))
    
    # Data Quality Thresholds
    DATA_FRESHNESS_THRESHOLD_MINUTES: float = float(os.getenv("DATA_FRESHNESS_THRESHOLD_MINUTES", "60.0"))
    MIN_EVENTS_PER_BATCH_WARNING: int = int(os.getenv("MIN_EVENTS_PER_BATCH_WARNING", "0"))
    MAX_EVENTS_PER_BATCH_WARNING: int = int(os.getenv("MAX_EVENTS_PER_BATCH_WARNING", "5000"))
    ALERT_WEBHOOK_URL: str = os.getenv("ALERT_WEBHOOK_URL", "")

settings = Settings()
