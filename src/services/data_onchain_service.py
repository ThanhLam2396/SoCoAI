import requests
import subprocess
import json
import os
import openai
import logging
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Ensure src is loaded correctly regardless of execution location
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from utils.config_loader import CONFIG  # Retrieve API key from CONFIG

# Paths to files
DATA_DIR = "data"
CONFIG_DIR = "config"

ONCHAIN_DATA_FILE = os.path.join(DATA_DIR, "onchain_data.json")
ONCHAIN_NEWS_PROMPT_FILE = os.path.join(CONFIG_DIR, "onchain_news_prompt.json")
GENERATED_NEWS_FILE = os.path.join(DATA_DIR, "generated_onchain_news.txt")

# Ensure directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve OpenAI API Key from CONFIG
OPENAI_API_KEY = CONFIG.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("❌ Error: OpenAI API Key not set in CONFIG!")
    exit(1)  # Stop the program if API key is missing

class OnchainDataService:
    def __init__(self):
        """Initialize Onchain Data Service"""
        self.api_url = "https://s.directory/injective"
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        # Configure Selenium WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        self.driver = webdriver.Chrome(options=options)

    def fetch_injective_data(self):
        """Fetch Injective network information from API"""
        try:
            response = requests.get(self.api_url)
            response.raise_for_status()
            data = response.json()

            chain = data.get("chain", {})
            params = chain.get("params", {})
            prices = chain.get("prices", {}).get("coingecko", {}).get("INJ", {}).get("usd", "N/A")

            return {
                "Pretty Name": chain.get("pretty_name", "Injective"),
                "Chain ID": chain.get("chain_id", "injective-1"),
                "Status": chain.get("status", "Live"),
                "Symbol": chain.get("symbol", "INJ"),
                "Base Inflation": f"{params.get('base_inflation', 0) * 100:.3f}%" if "base_inflation" in params else "N/A",
                "Inflation Max": f"{float(params.get('mint', {}).get('inflation_max', 0)) * 100:.3f}%" if "mint" in params else "N/A",
                "Community Tax": f"{float(params.get('community_tax', 0)) * 100:.1f}%" if "community_tax" in params else "N/A",
                "Prices": f"${prices}",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error calling API: {e}")
            return {}

    def fetch_gov_params(self):
        """Fetch governance parameters from Injective using gRPC"""
        try:
            result = subprocess.run(
                ["grpcurl", "-plaintext", "-d", "{}", "injective-grpc.polkachu.com:14390", "cosmos.gov.v1.Query/Params"],
                capture_output=True, text=True, check=True
            )
            params = json.loads(result.stdout).get("params", {})

            return {
                "Min Deposit": f"{float(params.get('minDeposit', [{}])[0].get('amount', 0)) / 1e18:.2f} INJ",
                "Voting Period": f"{int(params.get('votingPeriod', '0s').replace('s', '')) // 3600} hours",
                "Quorum": f"{float(params.get('quorum', 0)) * 100:.2f}%",
                "Threshold": f"{float(params.get('threshold', 0)) * 100:.2f}%",
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error calling gRPC: {e}")
            return {}

    def fetch_supply_and_staking(self):
        """Fetch total INJ supply and staking amounts"""
        try:
            supply_data = json.loads(subprocess.run(
                ["grpcurl", "-plaintext", "-d", '{"denom": "inj"}', "injective-grpc.polkachu.com:14390", "cosmos.bank.v1beta1.Query/SupplyOf"],
                capture_output=True, text=True, check=True
            ).stdout)

            staking_data = json.loads(subprocess.run(
                ["grpcurl", "-plaintext", "-d", "{}", "injective-grpc.polkachu.com:14390", "cosmos.staking.v1beta1.Query/Pool"],
                capture_output=True, text=True, check=True
            ).stdout)

            return {
                "Supply Data": f"{float(supply_data['amount']['amount']) / 1e18:,.2f} INJ",
                "BondedTokens": f"{float(staking_data['pool']['bondedTokens']) / 1e18:,.2f} INJ",
                "NotBondedTokens": f"{float(staking_data['pool']['notBondedTokens']) / 1e18:,.2f} INJ"
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error calling gRPC: {e}")
            return {}

    def fetch_web_data(self):
        """Fetch data from injscan.com using Selenium"""
        def get_value(xpath, timeout=15):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                return element.text.strip().replace("\n", " ")
            except:
                return "Not found"

        web_data = {}
        
        # 1. Homepage
        self.driver.get("https://injscan.com/")
        time.sleep(5)
        web_data.update({
            "Circulating Supply": get_value("//span[contains(text(), ',') and ancestor::div[contains(@class, 'inline-flex')]]"),
            "Market Cap": get_value("//div[contains(text(), 'Market Cap')]/following-sibling::div"),
            "Number of Assets": get_value("//div[contains(text(), 'Number of Assets')]/following-sibling::div"),
            "Number of Wallets": get_value("//div[contains(text(), 'Number of Wallets')]/following-sibling::div"),
            "Total Staked": get_value("//div[contains(text(), 'Total Staked')]/following-sibling::div"),
            "Staking APR": get_value("//div[contains(text(), 'Staking APR')]/following-sibling::div"),
            "INJ Burned": get_value("//div[contains(text(), 'INJ Burned')]/following-sibling::div"),
        })

        # 2. Transactions page
        self.driver.get("https://injscan.com/transactions/")
        time.sleep(7)
        web_data.update({
            "Total Transactions": get_value("//div[@class='text-2xl font-medium text-uiPrimary-100 leading-8']"),
            "Transactions (Last 24h)": get_value("//div[contains(., 'Transactions (Last 24h)')]/following-sibling::div//span"),
            "Transactions (30d)": get_value("//div[contains(., 'Transactions (30d)')]/following-sibling::div//div[@class='flex items-end gap-1 text-uiGray-200']"),
            "TPS (Last 100 Blocks)": get_value("//div[contains(., 'TPS (Last 100 Blocks)')]/following-sibling::div//span"),
        })

        # 3. Blocks page
        self.driver.get("https://injscan.com/blocks/")
        time.sleep(7)
        web_data.update({
            "Block Height": get_value("//div[contains(., 'Block Height')]/following-sibling::div"),
            "Block Count (Last 24h)": get_value("//div[contains(., 'Block Count (Last 24h)')]/following-sibling::div"),
            "Block Time": get_value("//div[contains(., 'Block Time')]/following-sibling::div"),
        })

        # 4. Assets page
        self.driver.get("https://injscan.com/assets/")
        time.sleep(7)
        web_data.update({
            "Total Asset Value": f"${get_value('//*[@id=\"__nuxt\"]/main/div[2]/div/main/div/div[1]/div[1]/div/div[2]/div/div/span/span')}",
            "Staked Asset Value (INJ)": f"${get_value('//*[@id=\"__nuxt\"]/main/div[2]/div/main/div/div[1]/div[2]/div/div[2]/span/div/span/span')}",
            "Total On-Chain Assets": get_value('//*[@id=\"__nuxt\"]/main/div[2]/div/main/div/div[1]/div[3]/div/div[2]/span'),
            "Smart Contracts": get_value('//*[@id=\"__nuxt\"]/main/div[2]/div/main/div/div[1]/div[4]/div/div[2]/span'),
        })

        return web_data

    def save_onchain_data(self, data):
        """Save on-chain data to JSON file"""
        try:
            with open(ONCHAIN_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Data saved to {ONCHAIN_DATA_FILE}")
        except Exception as e:
            logger.error(f"❌ Error saving on-chain data: {e}")

    def generate_news(self, onchain_data):
        """Generate news from on-chain data using OpenAI GPT"""
        if not os.path.exists(ONCHAIN_NEWS_PROMPT_FILE):
            logger.warning("⚠️ Prompt file not found!")
            return None

        try:
            with open(ONCHAIN_NEWS_PROMPT_FILE, "r", encoding="utf-8") as f:
                prompt_template = json.load(f)
        except json.JSONDecodeError:
            logger.error("❌ Error reading prompt file!")
            return None

        formatted_prompt = json.dumps({
            "role": prompt_template["role"],
            "goals": " ".join(prompt_template["goals"]),
            "formatting_requirements": " ".join(prompt_template["formatting_requirements"]),
            "example_output": prompt_template["example_output"][0],
            "onchain_data": onchain_data
        })

        try:
            logger.info("[🔍] Sending request to OpenAI to generate news...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": formatted_prompt}],
                max_tokens=1000,
                temperature=0.7
            )

            news_content = response.choices[0].message.content.strip()
            with open(GENERATED_NEWS_FILE, "w", encoding="utf-8") as f:
                f.write(news_content)

            logger.info(f"✅ News saved to {GENERATED_NEWS_FILE}")
            return news_content
        except Exception as e:
            logger.error(f"❌ Error generating news: {e}")
            return None

    def __del__(self):
        """Close the browser when the object is destroyed"""
        self.driver.quit()

if __name__ == "__main__":
    service = OnchainDataService()
    # Fetch data from various sources
    onchain_data = {
        **service.fetch_injective_data(),
        **service.fetch_gov_params(),
        **service.fetch_supply_and_staking(),
        **service.fetch_web_data()
    }
    
    # Save on-chain data to file
    service.save_onchain_data(onchain_data)
    
    # Generate news from fetched data
    service.generate_news(onchain_data)