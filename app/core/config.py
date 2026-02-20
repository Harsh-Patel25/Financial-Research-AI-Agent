"""
Application configuration — loaded from .env via python-dotenv.
Extend this as the project grows (DB URL, LLM keys, etc.)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Financial Research AI"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    # Dev default: SQLite file stored in project root.
    # Production override: set DATABASE_URL=postgresql+psycopg2://user:pass@host/db
    database_url: str = "sqlite:///./financial_ai.db"

    # LLM
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # External APIs
    news_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()



# ### ✅ What Was Added

# ```python
# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     app_name: str = "Financial Research AI"
#     log_level: str = "INFO"
#     openai_api_key: str

#     class Config:
#         env_file = ".env"

# settings = Settings()
# ```

# ---

# ### 🎯 Purpose of This Implementation

# * Introduced a **structured configuration management system** using `BaseSettings`.
# * Enabled **type-safe and validated environment variable handling**.
# * Implemented **fail-fast behavior at application startup** if required variables (e.g., API keys) are missing.
# * Ensured sensitive data (like API keys) is managed securely through environment variables instead of hardcoding.

# ---

# ### 🧠 Problems It Solves

# * Eliminates hardcoded secrets from the codebase.
# * Detects missing or misconfigured environment variables during startup.
# * Centralizes configuration management for better maintainability and scalability.
