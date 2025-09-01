"""
Asosiy ishga tushirish fayli
"""

import asyncio
import logging
from bot import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
    except Exception as e:
        print(f"Xatolik: {e}")
