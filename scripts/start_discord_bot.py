import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.discord_bot_service import DiscordBotService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    logging.info("🤖 Starting Discord Bot Service...")
    bot_service = DiscordBotService()
    bot_service.run_discord_bot()
