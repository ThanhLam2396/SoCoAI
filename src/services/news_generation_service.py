import json
import os
import openai
import datetime
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("NewsGenerationService")

TRANSFORMED_TWEETS_FILE = "data/transformed_tweets.txt"
GENERATED_NEWS_FILE = "data/generated_news.txt"
DAILY_NEWS_FILE = "data/daily_news_summary.txt"
WEEKLY_NEWS_FILE = "data/weekly_news_summary.txt"
DAILY_GENERATED_NEWS_FILE = "data/daily_generate_news.txt"
NEWS_PROMPT_FILE = "config/news_generation_prompt.json"
DAILY_RECAP_PROMPT_FILE = "config/daily_news_generation_prompt.json"

class NewsGenerationService:
    def __init__(self):
        self.api_key = CONFIG.get("OPENAI_API_KEY")
        openai.api_key = self.api_key
        self.news_prompt = self.load_prompt(NEWS_PROMPT_FILE)
        self.daily_recap_prompt = self.load_prompt(DAILY_RECAP_PROMPT_FILE)
        self.current_date = self.get_date_from_file()

    def load_prompt(self, prompt_file):
        if not os.path.exists(prompt_file):
            logger.error(f"[❌] Prompt file {prompt_file} not found!")
            return {}
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[❌] Error reading prompt file {prompt_file}: {e}")
            return {}

    def get_date_from_file(self):
        if not os.path.exists(DAILY_NEWS_FILE):
            return datetime.date.today().strftime("%d/%m/%y")
        with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        if first_line.startswith("DATE:"):
            date_str = first_line.replace("DATE:", "").strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%y"):
                try:
                    return datetime.datetime.strptime(date_str, fmt).strftime("%d/%m/%y")
                except ValueError:
                    continue
            logger.error(f"[❌] Invalid date format: {date_str}. Using today's date.")
        return datetime.date.today().strftime("%d/%m/%y")

    def load_transformed_tweets(self):
        if not os.path.exists(TRANSFORMED_TWEETS_FILE):
            logger.warning("[⚠️] File transformed_tweets.txt not found!")
            return ""
        with open(TRANSFORMED_TWEETS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logger.warning("[⚠️] transformed_tweets.txt is empty!")
            return content

    def load_daily_news(self):
        if not os.path.exists(DAILY_NEWS_FILE):
            logger.warning("[⚠️] File daily_news_summary.txt not found!")
            return ""
        with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[1:]).strip()

    def build_prompt(self, news_data, is_daily_recap=False):
        prompt_data = self.daily_recap_prompt if is_daily_recap else self.news_prompt
        if not prompt_data:
            logger.error("[❌] Invalid prompt data!")
            return ""
        role = prompt_data.get("role", "")
        goals = "\n".join(["- " + goal for goal in prompt_data.get("goals", [])])
        formatting = "\n".join(["- " + req for req in prompt_data.get("formatting_requirements", [])])
        examples = "\n\n".join(prompt_data.get("example_output", []))
        title = f"📅 Injective Daily Wrap-Up: Top Highlights on Date [{self.current_date}]!"
        full_prompt = f"""{role}

### 🎯 Goals:
{goals}

### 📝 Formatting Requirements:
{formatting}

### 🏆 Example Output:
{examples}

### 🚀 Input Data:
{title}

{news_data}
"""
        return full_prompt.strip()

    def append_to_news_files(self, news_content):
        self.current_date = datetime.date.today().strftime("%d/%m/%y")
        news_hash = hash(news_content)

        try:
            existing_hashes = set()
            if os.path.exists(DAILY_NEWS_FILE):
                with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.startswith(f"DATE: {self.current_date}"):
                        news_items = content.split("\n\n")[1:]
                        existing_hashes = {hash(item.strip()) for item in news_items if item.strip()}
                    else:
                        os.remove(DAILY_NEWS_FILE)
                        logger.info(f"[🔄] Daily date mismatch! Deleted old file {DAILY_NEWS_FILE}")

            if news_hash in existing_hashes:
                logger.info("[INFO] Skipping duplicate news for daily file.")
                return

            with open(DAILY_NEWS_FILE, "a" if os.path.exists(DAILY_NEWS_FILE) else "w", encoding="utf-8") as f:
                if os.stat(DAILY_NEWS_FILE).st_size == 0:
                    f.write(f"DATE: {self.current_date}\n\n")
                f.write(news_content + "\n\n")
        except Exception as e:
            logger.error(f"[❌] Error appending to {DAILY_NEWS_FILE}: {e}")

        try:
            existing_hashes = set()
            if os.path.exists(WEEKLY_NEWS_FILE):
                with open(WEEKLY_NEWS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                news_items = [item for item in content.split("\n\n") if item.strip()]
                existing_hashes = {hash(item) for item in news_items}
                if len(news_items) >= 50:
                    os.remove(WEEKLY_NEWS_FILE)
                    logger.info(f"[🔄] Weekly news exceeded 50 items! Deleted old file {WEEKLY_NEWS_FILE}")

            if news_hash in existing_hashes:
                logger.info("[INFO] Skipping duplicate news for weekly file.")
                return

            with open(WEEKLY_NEWS_FILE, "a", encoding="utf-8") as f:
                f.write(news_content + "\n\n")
        except Exception as e:
            logger.error(f"[❌] Error appending to {WEEKLY_NEWS_FILE}: {e}")

    def generate_news(self):
        transformed_tweets = self.load_transformed_tweets()
        if not transformed_tweets:
            logger.warning("[⚠️] No new tweet data to generate news! Clearing generated_news.txt.")
            with open(GENERATED_NEWS_FILE, "w", encoding="utf-8") as f:
                f.write("")  
            return
        
        full_prompt = self.build_prompt(transformed_tweets)
        try:
            logger.info("[🔍] Sending request to OpenAI to generate news...")
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": full_prompt}],
                max_tokens=3000,
                temperature=0.7
            )
            news_content = response.choices[0].message.content.strip()
            with open(GENERATED_NEWS_FILE, "w", encoding="utf-8") as f:
                f.write(news_content)
            self.append_to_news_files(news_content)
            logger.info(f"[✅] News generated and saved to {GENERATED_NEWS_FILE}, {DAILY_NEWS_FILE}, and {WEEKLY_NEWS_FILE}")
        except Exception as e:
            logger.error(f"[❌] Error generating news: {e}")

    def generate_daily_recap(self):
        daily_news_content = self.load_daily_news()
        if not daily_news_content:
            logger.warning("[⚠️] No news for the day to summarize!")
            return
        full_prompt = self.build_prompt(daily_news_content, is_daily_recap=True)
        try:
            logger.info("[🔍] Sending request to OpenAI to generate Daily Recap...")
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "system", "content": full_prompt}],
                max_tokens=3000,
                temperature=0.7
            )
            daily_recap_content = response.choices[0].message.content.strip()
            with open(DAILY_GENERATED_NEWS_FILE, "w", encoding="utf-8") as f:
                f.write(daily_recap_content)
            logger.info(f"[✅] Daily Recap generated and saved to {DAILY_GENERATED_NEWS_FILE}")
        except Exception as e:
            logger.error(f"[❌] Error generating Daily Recap: {e}")

    def run(self):
        self.current_date = datetime.date.today().strftime("%d/%m/%y")
        logger.info("[🚀] Starting news generation...")
        self.generate_news()

    def run_daily_recap(self):
        logger.info("[🚀] Starting Daily Recap generation...")
        self.generate_daily_recap()

if __name__ == "__main__":
    service = NewsGenerationService()
    service.run()