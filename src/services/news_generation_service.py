import json
import os
import openai
import datetime
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("NewsGenerationService")

# Define storage files
TRANSFORMED_TWEETS_FILE = "data/transformed_tweets.txt"
GENERATED_NEWS_FILE = "data/generated_news.txt"
DAILY_NEWS_FILE = "data/daily_news_summary.txt"  # File for daily news summary
DAILY_GENERATED_NEWS_FILE = "data/daily_generate_news.txt"  # File for generated Daily Recap
NEWS_PROMPT_FILE = "config/news_generation_prompt.json"  # Prompt for regular news
DAILY_RECAP_PROMPT_FILE = "config/daily_news_generation_prompt.json"  # Prompt for Daily Recap

class NewsGenerationService:
    """Service to generate news from transformed tweets and create Daily Recap."""

    def __init__(self):
        self.api_key = CONFIG.get("OPENAI_API_KEY")  
        openai.api_key = self.api_key
        self.news_prompt = self.load_prompt(NEWS_PROMPT_FILE)  # Load news prompt
        self.daily_recap_prompt = self.load_prompt(DAILY_RECAP_PROMPT_FILE)  # Load Daily Recap prompt
        self.current_date = self.get_date_from_file()  # Get date from daily_news_summary.txt

    def load_prompt(self, prompt_file):
        """Load prompt from JSON file."""
        if not os.path.exists(prompt_file):
            logger.error(f"[❌] Prompt file {prompt_file} not found!")
            return {}

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                return json.load(f)  # Load prompt as dictionary
        except Exception as e:
            logger.error(f"[❌] Error reading prompt file {prompt_file}: {e}")
            return {}

    def get_date_from_file(self):
        """Get date from the first line of daily_news_summary.txt (supports formats: DATE: DD/MM/YY and DATE: YYYY-MM-DD)."""
        if not os.path.exists(DAILY_NEWS_FILE):
            return datetime.date.today().strftime("%d/%m/%y")  # Format: DD/MM/YY if file doesn't exist

        with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        if first_line.startswith("DATE:"):
            date_str = first_line.replace("DATE:", "").strip()
            
            # Try parsing with format YYYY-MM-DD or DD/MM/YY
            for fmt in ("%Y-%m-%d", "%d/%m/%y"):
                try:
                    return datetime.datetime.strptime(date_str, fmt).strftime("%d/%m/%y")
                except ValueError:
                    continue

            logger.error(f"[❌] Invalid date format: {date_str}. Using today's date.")
        
        return datetime.date.today().strftime("%d/%m/%y")

    def load_transformed_tweets(self):
        """Load content from transformed_tweets.txt."""
        if not os.path.exists(TRANSFORMED_TWEETS_FILE):
            logger.warning("[⚠️] File transformed_tweets.txt not found!")
            return ""

        with open(TRANSFORMED_TWEETS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()

    def load_daily_news(self):
        """Load content from daily_news_summary.txt (skip DATE line)."""
        if not os.path.exists(DAILY_NEWS_FILE):
            logger.warning("[⚠️] File daily_news_summary.txt not found!")
            return ""

        with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return "".join(lines[1:]).strip()  # Skip the first line (DATE)

    def build_prompt(self, news_data, is_daily_recap=False):
        """Build complete prompt from JSON template."""
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

    def append_to_daily_news(self, news_content):
        """Append news to daily_news_summary.txt. If it's a new day, delete the old file."""
        if os.path.exists(DAILY_NEWS_FILE):
            with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()

            # If it's a new day, delete the old file
            if first_line.startswith("DATE:") and first_line != f"DATE: {self.current_date}":
                os.remove(DAILY_NEWS_FILE)
                logger.info(f"[🔄] New day! Deleted old file {DAILY_NEWS_FILE}")

        # Write news to daily_news_summary.txt
        with open(DAILY_NEWS_FILE, "a", encoding="utf-8") as f:
            if os.stat(DAILY_NEWS_FILE).st_size == 0:
                f.write(f"DATE: {self.current_date}\n\n")  # Add date if file is empty
            f.write(news_content + "\n\n")

    def generate_news(self):
        """Send request to OpenAI to generate news from transformed tweets."""
        transformed_tweets = self.load_transformed_tweets()
        if not transformed_tweets:
            logger.warning("[⚠️] No tweet data to generate news!")
            return

        full_prompt = self.build_prompt(transformed_tweets)  # Build prompt

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

            self.append_to_daily_news(news_content)

            logger.info(f"[✅] News generated and saved to {GENERATED_NEWS_FILE} and {DAILY_NEWS_FILE}")

        except Exception as e:
            logger.error(f"[❌] Error generating news: {e}")

    def generate_daily_recap(self):
        """Generate Daily Recap summary from the day's news."""
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
        """Run the news generation process."""
        logger.info("[🚀] Starting news generation from transformed tweets...")
        self.generate_news()

    def run_daily_recap(self):
        """Run the Daily Recap generation process."""
        logger.info("[🚀] Starting Daily Recap generation from the day's news...")
        self.generate_daily_recap()