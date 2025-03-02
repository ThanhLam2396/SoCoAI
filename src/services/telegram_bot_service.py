import json
import os
import re
import logging
from openai import AsyncOpenAI
from telegram import Update, MessageEntity, Chat
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from src.utils.config_loader import CONFIG

# Configure logger
logger = logging.getLogger("TelegramBotService")
logger.setLevel(logging.ERROR)

# Disable unnecessary logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class TelegramBotService:
    def __init__(self):
        """Initialize Telegram bot with OpenAI"""
        self.api_key = CONFIG.get("OPENAI_API_KEY")
        self.telegram_token = CONFIG.get("TELEGRAM_BOT_TOKEN")
        self.bot_username = CONFIG.get("BOT_USERNAME", "socoai_bot").lower()

        if not all([self.api_key, self.telegram_token]):
            raise ValueError("Missing API Key or Telegram Token configuration")

        self.openai_client = AsyncOpenAI(api_key=self.api_key)
        self.application = Application.builder().token(self.telegram_token).build()
        self.prompt_data = self.load_prompt("config/telegram_prompt.json")

        # Create list of trigger keywords
        self.trigger_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("trigger_keywords", []))
        self.banned_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("banned_keywords", []))

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & self._mention_filter(),
                self.handle_message
            )
        )

    def _mention_filter(self):
        """Create a filter to check for mentions"""
        return (
            filters.ChatType.PRIVATE
            | (
                filters.Entity(MessageEntity.MENTION)
                & filters.Regex(rf"@{self.bot_username}(\s+|$)")
            )
        )

    def load_prompt(self, prompt_file: str) -> dict:
        """Load prompt from JSON file"""
        if hasattr(self, "_cached_prompt"):  # If already cached, reuse it
            return self._cached_prompt
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                self._cached_prompt = json.load(f)  # Cache the data
                return self._cached_prompt
        except FileNotFoundError:
            logger.error(f"Prompt file {prompt_file} not found!")
            return {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        await update.message.reply_text("Hello! Tag me with @socoai_bot to chat!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages from users"""
        try:
            user_message = update.message.text.strip()

            # Clean mentions in group chats
            if update.message.chat.type != Chat.PRIVATE:
                user_message = re.sub(
                    rf"@{self.bot_username}\s*",
                    "",
                    user_message,
                    flags=re.IGNORECASE
                ).strip()

            # Detect keywords related to staking/Specific mentions
            contains_trigger = any(keyword.lower() in user_message.lower() for keyword in self.trigger_keywords)
            contains_banned = any(keyword.lower() in user_message.lower() for keyword in self.banned_keywords)

            # If user uses banned keywords, respond sassily without mentioning Specific mentions
            if contains_banned:
                await update.message.reply_text("Oh dear, such unrefined language! I'm a classy bot, let's keep it fun and drama-free. 😤")
                return

            # Generate response from OpenAI
            response = await self.generate_response(user_message, contains_trigger)
            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            await update.message.reply_text("Oops! I encountered an error, try again later. 😢")

    async def generate_response(self, user_message: str, mention_specific: bool) -> str:
        """Generate response from OpenAI based on context"""
        messages = [
            {
                "role": "system",
                "content": f"{self.prompt_data.get('role', '')}\n\n{self.prompt_data.get('context', '')}"
            }
        ]

        # Add example conversations from prompt
        for example in self.prompt_data.get("example_conversations", []):
            messages.append({"role": "user", "content": example["User:"]})
            messages.append({"role": "assistant", "content": example["Assistant:"]})

        # If user mentions staking/inj/INJ, add specific mention prompt
        if mention_specific:
            strategy = self.prompt_data.get("specific_mention_handling", {}).get("response_strategy", [])
            messages.append({"role": "system", "content": " ".join(strategy)})

        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=300,
                temperature=0.9  # Increase creativity
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            return "Got a little lag, try asking again! 😏"

    def run(self):
        """Run the Telegram bot"""
        try:
            logger.info("[🚀] Telegram bot is running...")
            self.application.run_polling(
                poll_interval=0.1,
                timeout=10,
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
        except Exception as e:
            logger.critical(f"[❌] Critical error: {str(e)}", exc_info=True)