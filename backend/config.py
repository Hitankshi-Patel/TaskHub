import os
from dotenv import load_dotenv

# Load .env file from the current directory
load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "taskhub-secret-key-change-in-prod")
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")

    # Supabase (PostgreSQL) Database connection URI
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        # SQLAlchemy requires postgresql:// instead of postgres://
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Serverless-friendly SQLAlchemy engine options.
    # NullPool disables connection pooling entirely — each request opens a fresh
    # connection and closes it when done. This is required for Vercel serverless
    # functions, which are stateless and cannot safely share connection pools
    # across invocations.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,       # Test connection before use to discard stale sockets
        "pool_recycle": 280,         # Recycle connections before Supabase's 300s idle timeout
        "connect_args": {
            "connect_timeout": 10,   # Fail fast on connection attempts (seconds)
            "options": "-c statement_timeout=30000"  # 30s max per statement
        }
    }

    # Replicate API Configuration
    REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
    REPLICATE_INPAINT_MODEL = os.environ.get(
        "REPLICATE_INPAINT_MODEL",
        "sepal/sdxl-inpainting:aca001c8b137114d5e594c68f7084ae6d82f364758aab8d997b233e8ef3c4d93"
    )

    # Resend API Key for Email Notifications
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "TaskHub <notifications@taskhub.dev>")

    # Firebase Admin Configuration
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
    FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")

    # Gemini API Key for Image Generation
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

    # Firebase Service Account JSON (as a raw string) for production/Vercel
    FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
