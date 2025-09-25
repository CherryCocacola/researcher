# core/config.py
import os

class AppConfig:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        # 모델 분리: 텍스트/비전
        self.openai_text_model_name = os.getenv("OPENAI_TEXT_MODEL", "gpt-5")
        self.openai_vision_model_name = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
        # 하위 호환용(기존 코드 대비): 사용처에서 text/vision 중 택1
        self.openai_model_name = os.getenv("OPENAI_MODEL", self.openai_text_model_name)

        # db connection (provide via environment variables)
        self.db_host = os.getenv("DB_HOST", "")
        self.db_name = os.getenv("DB_NAME", "")
        self.db_user = os.getenv("DB_USER", "")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_schema = os.getenv("DB_SCHEMA", "scholar")
        self.embedding_dim = int(os.getenv("EMBEDDING_DIM", "1024"))
        self.top_k = int(os.getenv("TOP_K", "5"))
        self.max_faiss_distance = float(os.getenv("MAX_FAISS_DISTANCE", "15.0"))
        self.retriever_limit = int(os.getenv("RETRIEVER_LIMIT", "20"))
        self.rag_temperature = float(os.getenv("RAG_TEMPERATURE", "0.4"))
        self.rag_max_tokens = int(os.getenv("RAG_MAX_TOKENS", "500"))
        self.journal_impact_weight = float(os.getenv("JOURNAL_IMPACT_WEIGHT", "0.2"))
        self.keyword_weight = float(os.getenv("KEYWORD_WEIGHT", "0.3"))
        self.keyword_language_priority = os.getenv("KEYWORD_LANGUAGE_PRIORITY", "ko,en")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))
