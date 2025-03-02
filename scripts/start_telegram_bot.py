import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.telegram_bot_service import TelegramBotService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    logging.info("🤖 Starting Telegram Bot Service...")
    bot_service = TelegramBotService()
    bot_service.run()
