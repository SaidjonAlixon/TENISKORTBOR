import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    
    # Database - PostgreSQL (Railway)
    DATABASE_URL = os.getenv("DATABASE_URL")
    DB_HOST = os.getenv("PGHOST", "localhost")
    DB_PORT = os.getenv("PGPORT", "5432")
    DB_NAME = os.getenv("PGDATABASE", "tennis_bot_db")
    DB_USER = os.getenv("PGUSER", "postgres")
    DB_PASSWORD = os.getenv("PGPASSWORD")
    
    # Railway uchun DATABASE_URL yaratish
    @classmethod
    def get_database_url(cls):
        """Database URL ni olish"""
        if cls.DATABASE_URL:
            # Railway dan kelgan URL ni asyncpg uchun o'zgartirish
            if cls.DATABASE_URL.startswith('postgresql://'):
                # postgres.railway.internal ni localhost ga o'zgartirish
                url = cls.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
                url = url.replace('postgres.railway.internal', 'localhost')
                return url
            return cls.DATABASE_URL
        
        # Railway yoki boshqa PostgreSQL uchun URL yaratish
        if cls.DB_PASSWORD:
            return f"postgresql+asyncpg://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        else:
            # Local development uchun
            return f"postgresql+asyncpg://{cls.DB_USER}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    # To'lov tizimlari
    # Payme
    PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID")
    PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY")
    PAYME_TEST_MODE = os.getenv("PAYME_TEST_MODE", "True").lower() == "true"
    
    # Click
    CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID")
    CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID")
    CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY")
    CLICK_TEST_MODE = os.getenv("CLICK_TEST_MODE", "True").lower() == "true"
    
    # Uzum Pay
    UZUM_MERCHANT_ID = os.getenv("UZUM_MERCHANT_ID")
    UZUM_SECRET_KEY = os.getenv("UZUM_SECRET_KEY")
    UZUM_TEST_MODE = os.getenv("UZUM_TEST_MODE", "True").lower() == "true"
    
    # Xavfsizlik
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-change-this")
    
    # Admin
    ADMIN_CHAT_IDS = [int(x) for x in os.getenv("ADMIN_CHAT_IDS", "").split(",") if x.strip()]
    SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
    
    # Bot sozlamalari
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "uz")
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
    BOOKING_HOLD_MINUTES = int(os.getenv("BOOKING_HOLD_MINUTES", "5"))
    CANCELLATION_HOURS = int(os.getenv("CANCELLATION_HOURS", "6"))
    
    # VAQTINCHA REJIM - To'lovni qo'lda tasdiqlash
    MANUAL_PAYMENT_MODE = os.getenv("MANUAL_PAYMENT_MODE", "True").lower() == "true"
    
    # Narxlar (so'mda)
    BASE_PRICE_PEAK = float(os.getenv("BASE_PRICE_PEAK", "50000"))
    BASE_PRICE_OFFPEAK = float(os.getenv("BASE_PRICE_OFFPEAK", "30000"))
    WEEKEND_COEFFICIENT = float(os.getenv("WEEKEND_COEFFICIENT", "1.2"))
    VIP_DISCOUNT = float(os.getenv("VIP_DISCOUNT", "0.15"))
    SERVICE_FEE = float(os.getenv("SERVICE_FEE", "0.03"))
    
    # Vaqt sozlamalari
    PEAK_START_HOUR = int(os.getenv("PEAK_START_HOUR", "18"))
    PEAK_END_HOUR = int(os.getenv("PEAK_END_HOUR", "22"))
    COURT_OPEN_HOUR = int(os.getenv("COURT_OPEN_HOUR", "6"))
    COURT_CLOSE_HOUR = int(os.getenv("COURT_CLOSE_HOUR", "23"))
    
    # Fayl yo'llari
    UPLOAD_PATH = os.getenv("UPLOAD_PATH", "./uploads")
    REPORTS_PATH = os.getenv("REPORTS_PATH", "./reports")
    TICKETS_PATH = os.getenv("TICKETS_PATH", "./tickets")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "bot.log")
    
    @classmethod
    def get_timezone(cls):
        """Vaqt zonasini olish"""
        return pytz.timezone(cls.TIMEZONE)
    
    @classmethod
    def get_current_time(cls):
        """Joriy vaqtni olish"""
        return datetime.now(cls.get_timezone())
    
    @classmethod
    def is_peak_time(cls, hour: int) -> bool:
        """Peak vaqtni tekshirish"""
        return cls.PEAK_START_HOUR <= hour < cls.PEAK_END_HOUR
    
    @classmethod
    def is_weekend(cls, weekday: int) -> bool:
        """Dam olish kunini tekshirish (0=Dushanba, 6=Yakshanba)"""
        return weekday in [5, 6]  # Shanba va Yakshanba
    
    @classmethod
    def validate_config(cls):
        """Konfiguratsiyani tekshirish"""
        required_vars = [
            "BOT_TOKEN",
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Quyidagi environment variable'lar yo'q: {', '.join(missing_vars)}")
        
        return True

# Konfiguratsiyani tekshirish
try:
    Config.validate_config()
except ValueError as e:
    print(f"Konfiguratsiya xatosi: {e}")
    exit(1)
