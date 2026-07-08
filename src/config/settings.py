from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str
    postgres_user: str = "deepl_user"
    postgres_password: str = "deepl_password"
    postgres_db: str = "deepl_fp"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # OpenRouter / LLM
    openrouter_api_key: str
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"

    # OpenRouter Rerank (untuk Retrieval Agent)
    openrouter_rerank_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2:free"
    openrouter_rerank_url: str = "https://openrouter.ai/api/v1/rerank"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Anomaly — threshold kalibrasi test set (BERT 20-epoch, AUC 0.96): is_anomaly True jika score >= 0.069
    anomaly_threshold: float = 0.069

    # RAGAS judge (evaluasi RAG) — model berbeda dari generator (hindari self-bias)
    openrouter_judge_model: str = "openai/gpt-4o-mini"

    # Embedding — 384 dimensi untuk all-MiniLM-L6-v2
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True

    # RAG
    rag_top_k: int = 3
    rag_similarity_threshold: float = 0.5


settings = Settings()
