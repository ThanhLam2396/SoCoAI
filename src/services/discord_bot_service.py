import json
import logging
import discord
import asyncio
from openai import AsyncOpenAI
from src.utils.config_loader import CONFIG

# Configure logger
logger = logging.getLogger("DiscordBotService")
logger.setLevel(logging.ERROR)

# Disable unnecessary logs
logging.getLogger("discord").setLevel(logging.WARNING)

class DiscordBotService:
    def __init__(self):
        """Initialize Discord bot with OpenAI"""
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        # intents.message_content = True  # Required to read messages in the server
        
        self.client = discord.Client(intents=intents)
        self.api_key = CONFIG.get("OPENAI_API_KEY")
        self.discord_token = CONFIG.get("DISCORD_BOT_TOKEN")

        if not self.api_key or not self.discord_token:
            raise ValueError("Missing API Key or Discord Token configuration")

        self.openai_client = AsyncOpenAI(api_key=self.api_key)
        self.prompt_data = self.load_prompt("config/discord_prompt.json")

        # Create list of trigger keywords
        self.trigger_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("trigger_keywords", []))
        self.banned_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("banned_keywords", []))

        # Register event handlers
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

    def load_prompt(self, prompt_file: str) -> dict:
        """Load prompt from JSON file"""
        if hasattr(self, "_cached_prompt"):
            return self._cached_prompt
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                self._cached_prompt = json.load(f)
                # print("[DEBUG] Loaded prompt:", self._cached_prompt)  # Check if prompt is loaded
                return self._cached_prompt
        except FileNotFoundError:
            logger.error(f"Prompt file {prompt_file} not found!")
            return {}

    async def on_ready(self):
        """Event triggered when the bot connects successfully"""
        logger.info(f"[🚀] Discord bot connected to {len(self.client.guilds)} servers!")
        print(f"[✅] Discord bot connected successfully! Bot name: {self.client.user}")

    async def on_message(self, message):
        """Handle messages from users"""
        if message.author == self.client.user:  # Ignore messages from the bot itself
            return

        user_message = message.content.strip()

        # Detect keywords related to staking/Specific mentions
        contains_trigger = any(keyword.lower() in user_message.lower() for keyword in self.trigger_keywords)
        contains_banned = any(keyword.lower() in user_message.lower() for keyword in self.banned_keywords)

        # If user uses banned keywords, respond sassily without mentioning Specific mentions
        if contains_banned:
            await message.channel.send("Oh dear, such unrefined language! I'm a classy bot, let's keep it fun and drama-free, okay? 😤")
            return

        # Generate response from OpenAI
        response = await self.generate_response(user_message, contains_trigger)
        await message.channel.send(response)

    async def generate_response(self, user_message: str, mention_specific: bool) -> str:
        """Generate response from OpenAI based on context"""
        messages = [
            {
                "role": "system",
                "content": f"{self.prompt_data.get('role', 'You are an AI assistant.')}\n\n{self.prompt_data.get('context', '')}"
            }
        ]

        # Add example conversations from prompt
        for example in self.prompt_data.get("example_conversations", []):
            messages.append({"role": "user", "content": example["User:"]})
            messages.append({"role": "assistant", "content": example["Assistant:"]})

        # If user mentions staking/inj/INJ, include specific mention prompt
        if mention_specific:
            strategy = self.prompt_data.get("specific_mention_handling", {}).get("response_strategy", [])
            messages.append({"role": "system", "content": " ".join(strategy)})

        messages.append({"role": "user", "content": user_message})

        # print("[DEBUG] Sending to OpenAI:", messages)  # Debug content sent to API

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            return "Oops, I encountered an error! Please try again. 😢"

    def run_discord_bot(self):
        """Run the Discord bot"""
        try:
            logger.info("[🚀] Discord bot is running...")
            asyncio.run(self.client.start(self.discord_token))  # Run bot with asyncio.run()
        except Exception as e:
            logger.critical(f"[❌] Critical error: {str(e)}", exc_info=True)