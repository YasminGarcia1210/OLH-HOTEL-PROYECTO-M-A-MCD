import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV  = os.getenv("FLASK_ENV", "development")
    DEBUG      = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    PORT       = int(os.getenv("PORT", 5003))

    # Base de datos — cadena de conexión completa (Neon u otro proveedor)
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # Pool de conexiones
    DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", 1))
    DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", 10))

    # ── ABSA ──────────────────────────────────────────────────────────────────
    # Backend: "llm" | "deberta"
    ABSA_MODEL_BACKEND = os.getenv("ABSA_MODEL_BACKEND", "llm")

    # ── LLM — proveedor: "openai" | "gemini" | "ollama" ──────────────────────
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # OpenAI Batch API — polling opcional en el mismo proceso (alternativa: cron → POST /batch/sincronizar)
    OPENAI_BATCH_POLL_ENABLED       = os.getenv("OPENAI_BATCH_POLL_ENABLED", "false").lower() == "true"
    OPENAI_BATCH_POLL_INTERVAL_SEC  = int(os.getenv("OPENAI_BATCH_POLL_INTERVAL_SEC", "120"))

    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.1")

    # ── Backend deberta ───────────────────────────────────────────────────────
    # Modelo de embeddings para BERTopic (dinámicos)
    SENTENCE_MODEL = os.getenv("SENTENCE_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    # Tamaño mínimo de cluster para BERTopic
    BERTOPIC_MIN_TOPIC_SIZE = int(os.getenv("BERTOPIC_MIN_TOPIC_SIZE", "3"))
    # Score mínimo (cosine normalizado) para incluir un tópico dinámico
    BERTOPIC_MIN_DYNAMIC_SCORE = float(os.getenv("BERTOPIC_MIN_DYNAMIC_SCORE", "0.65"))
    # Máximo de tópicos dinámicos por review
    BERTOPIC_MAX_DYNAMIC_PER_REVIEW = int(os.getenv("BERTOPIC_MAX_DYNAMIC_PER_REVIEW", "2"))
    # Máximo de tópicos fijos por review (los de mayor entailment score)
    NLI_MAX_FIXED_PER_REVIEW = int(os.getenv("NLI_MAX_FIXED_PER_REVIEW", "3"))
    # Modelo ATSC: dado (texto, aspecto) → Positive / Negative / Neutral
    DEBERTA_ABSA_MODEL = os.getenv("DEBERTA_ABSA_MODEL", "yangheng/deberta-v3-base-absa-v1.1")
    # Modelo zero-shot NLI para detección de tópicos fijos por entailment
    # Alternativa multilingüe: "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
    NLI_MODEL                = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
    # Umbral de entailment para declarar un tópico mencionado
    NLI_ENTAILMENT_THRESHOLD = float(os.getenv("NLI_ENTAILMENT_THRESHOLD", "0.5"))
