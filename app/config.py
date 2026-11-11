import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-secret-key-replace-at-least-32-characters!")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-jwt-secret-key-replace-with-at-least-32-characters!")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # MongoDB Config (mongoengine)
    MONGODB_SETTINGS = {
        'host': os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/trip_planner_db"),
        'connect': False,
    }
    
    # Email SMTP Settings
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1")
    MAIL_USERNAME = (os.getenv("MAIL_USERNAME") or os.getenv("MAIL_USER") or "").strip()
    MAIL_PASSWORD = (os.getenv("MAIL_PASSWORD") or os.getenv("MAIL_PASS") or "").replace(" ", "").strip()
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER") or MAIL_USERNAME or "welcome@tripplanner.com"
