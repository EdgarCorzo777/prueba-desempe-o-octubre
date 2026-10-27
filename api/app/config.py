import os
from pydantic_settings import BaseSettings

class APISettings(BaseSettings):
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sismowatch_db")
    
    API_USER: str = os.getenv("API_USER", "api_user")
    API_PASSWORD: str = os.getenv("API_PASSWORD", "api_secret_2026")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "sismowatch_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "sismowatch_db_pass_2026")
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "sismowatch_jwt_secret_token_secure_key_hash_2026_xyz")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001")
    
    # Google Gemini AI Studio
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11438")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemini-3.5-flash-lite")
    OLLAMA_TIMEOUT_SECONDS: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))

    # Seed Admin & Viewer Credentials
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@sismowatch.internal")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "AdminSecure2026!*")
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "Administrador SismoWatch")
    
    VIEWER_EMAIL: str = os.getenv("VIEWER_EMAIL", "viewer@sismowatch.internal")
    VIEWER_PASSWORD: str = os.getenv("VIEWER_PASSWORD", "ViewerSecure2026!*")
    VIEWER_NAME: str = os.getenv("VIEWER_NAME", "Operador Viewer")

settings = APISettings()
