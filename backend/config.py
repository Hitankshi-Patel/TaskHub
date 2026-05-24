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
    # Format: postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        # SQLAlchemy requires postgresql:// instead of postgres://
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Replicate API Configuration
    REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
    # Recommended SDXL Inpainting model on Replicate
    REPLICATE_INPAINT_MODEL = os.environ.get(
        "REPLICATE_INPAINT_MODEL", 
        "sepal/sdxl-inpainting:aca001c8b137114d5e594c68f7084ae6d82f364758aab8d997b233e8ef3c4d93"
    )

    # Resend API Key for Email Notifications
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "TaskHub <notifications@taskhub.dev>")

    # Firebase Admin Configuration
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
    # Can point to a local service account credentials JSON file
    FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")
