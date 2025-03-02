import discord
import os
import asyncio
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("PostToDiscordService")

GENERATED_NEWS_FILE = "data/generated_news.txt"
DAILY_NEWS_FILE = "data/daily_generate_news.txt"  # File for Daily Recap

class PostToDiscordService:
    """Service to post news to Discord without running a persistent bot."""

    def __init__(self):
        self.token = CONFIG["DISCORD_BOT_TOKEN"]
        self.channel_id = int(CONFIG["DISCORD_CHANNEL_ID"])

    def load_news(self, file_path):
        """Load content from news or Daily Recap file and ensure data is returned as a list of strings."""
        if not os.path.exists(file_path):
            logger.warning(f"[⚠️] File {file_path} not found!")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            news_list = [line.strip() for line in f.read().strip().split("\n\n")]

        return news_list  # Return list of strings, no additional nesting

    async def post_news_async(self, file_path, is_daily_recap=False):
        """Send news to Discord."""
        news_list = self.load_news(file_path)
        if not news_list:
            logger.warning(f"[⚠️] No news to post from {file_path}!")
            return

        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        try:
            await client.login(self.token)
            channel = await client.fetch_channel(self.channel_id)

            if channel is None:
                logger.error(f"[❌] Channel with ID {self.channel_id} not found!")
                return

            batch_size = 10  # Each post contains up to 10 news items
            for i in range(0, len(news_list), batch_size):
                batch = news_list[i:i + batch_size]
                message = "\n\n".join(batch)  # Ensure data is a string

                try:
                    logger.info(f"[🚀] Sending {'Daily Recap' if is_daily_recap else 'news'} to Discord: {message[:50]}...")
                    await channel.send(message, suppress_embeds=True)
                    logger.info("[✅] Successfully sent!")
                except Exception as e:
                    logger.error(f"[❌] Error sending news: {e}")

        finally:
            await client.close()  # Close session properly

    def post_news(self):
        """Send regular news from generated_news.txt."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.post_news_async(GENERATED_NEWS_FILE))  # Run asynchronously if loop is active
        except RuntimeError:
            asyncio.run(self.post_news_async(GENERATED_NEWS_FILE))  # If no loop exists, create and run

    def post_daily_recap(self):
        """Send Daily Recap from daily_generate_news.txt."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.post_news_async(DAILY_NEWS_FILE, is_daily_recap=True))  # Run asynchronously if loop is active
        except RuntimeError:
            asyncio.run(self.post_news_async(DAILY_NEWS_FILE, is_daily_recap=True))  # If no loop exists, create and run

# Run script
if __name__ == "__main__":
    service = PostToDiscordService()

    # Post regular news
    service.post_news()

    # Post Daily Recap
    service.post_daily_recap()