import json
import logging
import os
import openai
import requests
from datetime import datetime
from src.utils.config_loader import CONFIG

# Logger setup
logger = logging.getLogger("MarketNewsService")
logger.setLevel(logging.INFO)

# Configurable paths & token settings
DATA_DIR = "data"
CONFIG_DIR = "config"
TOKEN_ID = CONFIG.get("TOKEN_ID", "injective-protocol")

MARKET_DATA_FILE = os.path.join(DATA_DIR, f"{TOKEN_ID}_market_data.json")
GENERATED_NEWS_FILE = os.path.join(DATA_DIR, "generated_market_news.txt")
MARKET_NEWS_PROMPT_FILE = os.path.join(CONFIG_DIR, "market_news_prompt.json")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)


class MarketNewsService:
    def __init__(self):
        """Initialize the service with API keys"""
        self.coingecko_api_key = CONFIG.get("COINGECKO_API_KEY")
        self.openai_api_key = CONFIG.get("OPENAI_API_KEY")
        self.base_url = "https://pro-api.coingecko.com/api/v3"

        if not self.coingecko_api_key:
            raise ValueError("❌ Missing Coingecko API Key!")

        if not self.openai_api_key:
            raise ValueError("❌ Missing OpenAI API Key!")

        openai.api_key = self.openai_api_key

    def fetch_token_market_data(self):
        """Fetch token market data from Coingecko API and save to JSON file"""
        params = {
            "vs_currency": "usd",
            "ids": TOKEN_ID,
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
            "price_change_percentage": "1h,24h,7d,30d,90d,1y"
        }

        market_data = self._make_request("/coins/markets", params)

        if not market_data or len(market_data) == 0:
            logger.warning(f"⚠️ No market data found for token {TOKEN_ID}")
            return None

        token = market_data[0]

        data = {
            "Token Name": token.get("name"),
            "Symbol": token.get("symbol").upper(),
            "Current Price (USD)": token.get("current_price"),
            "Market Capitalization (USD)": token.get("market_cap"),
            "Market Cap Rank": token.get("market_cap_rank"),
            "24h Trading Volume (USD)": token.get("total_volume"),
            "24h Price Change (%)": token.get("price_change_percentage_24h"),
            "7d Price Change (%)": token.get("price_change_percentage_7d_in_currency"),
            "30d Price Change (%)": token.get("price_change_percentage_30d_in_currency"),
            "90d Price Change (%)": token.get("price_change_percentage_90d_in_currency"),
            "All-Time High (USD)": token.get("ath"),
            "ATH Change (%)": token.get("ath_change_percentage"),
            "ATH Date": token.get("ath_date", "N/A"),  # Handle missing ATH Date
            "All-Time Low (USD)": token.get("atl"),
            "ATL Change (%)": token.get("atl_change_percentage"),
            "ATL Date": token.get("atl_date", "N/A"),  # Handle missing ATL Date
            "Last Updated": token.get("last_updated"),
        }

        self._save_json_file(MARKET_DATA_FILE, data)
        logger.info(f"✅ Market data saved to `{MARKET_DATA_FILE}`")
        return data

    def generate_market_news(self):
        """Generate market news using OpenAI"""
        market_data = self._load_json_file(MARKET_DATA_FILE)
        prompt_template = self._load_market_news_prompt()

        if not market_data:
            logger.warning(f"⚠️ No market data found to generate news for {TOKEN_ID}")
            return None

        if not prompt_template:
            logger.warning("⚠️ No market news prompt found!")
            return None

        formatted_prompt = self._format_prompt(prompt_template, market_data)

        try:
            logger.info("[🔍] Sending request to OpenAI for market news...")
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": formatted_prompt}],
                max_tokens=1000,
                temperature=0.7
            )

            logger.info(f"🔄 OpenAI Response: {response}")  # Check if OpenAI returns data

            if not response.choices or not response.choices[0].message.content:
                logger.error("[❌] OpenAI API returned an empty response!")
                return None

            news_content = response.choices[0].message.content.strip()
            self._save_text_file(GENERATED_NEWS_FILE, news_content)

            logger.info(f"[✅] Market news generated and saved to `{GENERATED_NEWS_FILE}`")
            return news_content

        except openai.OpenAIError as e:
            logger.error(f"[❌] OpenAI API Error: {e}")
            return None
        except Exception as e:
            logger.error(f"[❌] Unexpected error generating market news: {e}")
            return None

    def _format_prompt(self, prompt_template, market_data):
        """Replace placeholders in prompt template with actual market data"""
        today_date = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

        formatted_prompt = (
            f"{prompt_template['role']}\n\n"
            f"### Goals:\n"
            f"{' '.join(prompt_template['goals'])}\n\n"
            f"### Formatting Requirements:\n"
            f"{' '.join(prompt_template['formatting_requirements'])}\n\n"
            f"### Market Data:\n"
            f"Date: {today_date}\n"
            f"Token: {market_data['Token Name']} ({market_data['Symbol']})\n"
            f"Current Price: ${market_data['Current Price (USD)']}\n"
            f"24h Change: {market_data['24h Price Change (%)']}%\n"
            f"7d Change: {market_data['7d Price Change (%)']}%\n"
            f"All-Time High: ${market_data['All-Time High (USD)']} on {market_data['ATH Date']}\n"
            f"All-Time Low: ${market_data['All-Time Low (USD)']} on {market_data['ATL Date']}\n\n"
            f"### Example Output:\n"
            f"{prompt_template['example_output'][0]}\n\n"
            f"Now, generate a new market update based on the latest market data."
        )

        return formatted_prompt

    def _make_request(self, endpoint: str, params: dict = None):
        headers = {"Accept": "application/json"}
        params["x_cg_pro_api_key"] = self.coingecko_api_key
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[❌] Coingecko API Error: {e}")
            return None

    def _save_json_file(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _save_text_file(self, file_path, content):
        """Save text content to a file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content + "\n")

            logger.info(f"✅ Market news saved successfully to `{file_path}`")

            # Debug: Check immediately after writing file
            with open(file_path, "r", encoding="utf-8") as f:
                saved_content = f.read().strip()
                if not saved_content:
                    logger.error(f"[❌] Market news file `{file_path}` is empty after writing!")
                else:
                    logger.info(f"📄 Saved content in `{file_path}`")

        except Exception as e:
            logger.error(f"[❌] Error writing to `{file_path}`: {e}")

    def _load_json_file(self, file_path):
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ File not found: {file_path}")
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_market_news_prompt(self):
        if not os.path.exists(MARKET_NEWS_PROMPT_FILE):
            logger.warning(f"⚠️ Market news prompt file not found: {MARKET_NEWS_PROMPT_FILE}")
            return None
        with open(MARKET_NEWS_PROMPT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


# Test class
if __name__ == "__main__":
    service = MarketNewsService()
    service.fetch_token_market_data()
    service.generate_market_news()