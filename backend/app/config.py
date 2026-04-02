from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # JWT
    secret_key: str = "change-me-to-random-32-char-string"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/rag_platform.db"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "gpt-oss:latest"
    ollama_vision_model: str = "llava:latest"

    # Embedding (via Ollama)
    ollama_embedding_model: str = "bge-m3"
    embedding_dim: int = 1024

    # RAG storage paths
    rag_working_dir: str = "./rag_storage"
    upload_dir: str = "./uploads"
    rag_skip_entity_extraction: bool = True

    # Conversation settings
    conversation_max_history_turns: int = 20
    conversation_compact_threshold: int = 15
    conversation_compact_target: int = 6


settings = Settings()
