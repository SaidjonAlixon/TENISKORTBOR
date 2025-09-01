#!/usr/bin/env python3
"""
Botni ishga tushirish uchun skript
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Loyiha ildizini sys.path ga qo'shish
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from database import init_database
from bot import main

def setup_directories():
    """Kerakli papkalarni yaratish"""
    directories = [
        Config.UPLOAD_PATH,
        Config.REPORTS_PATH,
        Config.TICKETS_PATH,
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Papka yaratildi: {directory}")

def setup_logging():
    """Logging sozlash"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(f"logs/{Config.LOG_FILE}"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Aiogram loglarini kamaytirish
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

async def check_database():
    """Ma'lumotlar bazasini tekshirish"""
    try:
        await init_database()
        print("✅ Ma'lumotlar bazasi tayyor")
        return True
    except Exception as e:
        print(f"❌ Ma'lumotlar bazasi xatosi: {e}")
        return False

def print_startup_info():
    """Ishga tushirish ma'lumotlari"""
    print("🎾 Tennis Kort Bron Qilish Boti")
    print("=" * 50)
    print(f"🌐 Til: {Config.DEFAULT_LANGUAGE}")
    print(f"⏰ Vaqt zonasi: {Config.TIMEZONE}")
    print(f"🏟 Ish vaqti: {Config.COURT_OPEN_HOUR}:00 - {Config.COURT_CLOSE_HOUR}:00")
    print(f"🔥 Peak vaqt: {Config.PEAK_START_HOUR}:00 - {Config.PEAK_END_HOUR}:00")
    print(f"💰 Bazaviy narx: {Config.BASE_PRICE_OFFPEAK:,} / {Config.BASE_PRICE_PEAK:,} so'm")
    print(f"📊 Log level: {Config.LOG_LEVEL}")
    
    # VAQTINCHA REJIM haqida ogohlantirish
    if Config.MANUAL_PAYMENT_MODE:
        print("🧪 VAQTINCHA REJIM: To'lov avtomatik tasdiqlash YOQILGAN!")
        print("⚠️  Haqiqiy to'lov API'lari ishlamaydi")
    else:
        print("💳 To'lov tizimlari: HAQIQIY REJIM")
    
    print("=" * 50)

async def run_bot():
    """Botni ishga tushirish"""
    try:
        print_startup_info()
        setup_directories()
        setup_logging()
        
        print("🔍 Ma'lumotlar bazasini tekshirish...")
        if not await check_database():
            sys.exit(1)
        
        print("🚀 Bot ishga tushirilmoqda...")
        await main()
        
    except KeyboardInterrupt:
        print("\n⏹ Bot foydalanuvchi tomonidan to'xtatildi")
    except Exception as e:
        print(f"❌ Kutilmagan xatolik: {e}")
        logging.exception("Kutilmagan xatolik")
        sys.exit(1)

if __name__ == "__main__":
    # Python versiyasini tekshirish
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ talab qilinadi")
        sys.exit(1)
    
    # .env faylini tekshirish
    if not os.path.exists(".env"):
        print("⚠️  .env fayli topilmadi!")
        print("env_example.txt faylini .env ga nusxalab, ma'lumotlarni to'ldiring")
        sys.exit(1)
    
    # Botni ishga tushirish
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Xayr!")
    except Exception as e:
        print(f"❌ Ishga tushirishda xatolik: {e}")
        sys.exit(1)
