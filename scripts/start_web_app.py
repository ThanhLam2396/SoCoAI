import os
import logging
import json
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string, send_from_directory, abort, request
from flask_cors import CORS
from functools import wraps

# Import CONFIG từ utils.config_loader
from utils.config_loader import CONFIG

# Configure logger
logger = logging.getLogger("FlaskBotService")
logger.setLevel(logging.ERROR)

# Disable unnecessary logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Lấy OPENAI_API_KEY và TOKEN_ACCESS từ CONFIG
OPENAI_API_KEY = CONFIG.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in config/setting.json!")

TOKEN_ACCESS = CONFIG.get("TOKEN_ACCESS")
if not TOKEN_ACCESS:
    raise ValueError("TOKEN_ACCESS not found in config/setting.json!")

# Initialize Flask app
app = Flask(__name__, template_folder=".")
CORS(app, resources={r"/*": {"origins": "*"}})

# Define prompt file path explicitly
PROMPT_FILE = "config/web_app_prompt.json"  # Default prompt file
CONFIG_DIR = "config"  # Thư mục chứa các file prompt

class FlaskBotService:
    def __init__(self):
        """Initialize Flask bot with OpenAI"""
        self.api_key = OPENAI_API_KEY
        self.prompt_data = self.load_prompt(PROMPT_FILE)

        # Create list of trigger keywords
        self.trigger_keywords = set(self.prompt_data.get("special_handling", {}).get("trigger_keywords", []))
        self.banned_keywords = set(self.prompt_data.get("special_handling", {}).get("banned_keywords", []))

    def load_prompt(self, prompt_file: str) -> dict:
        """Load prompt from JSON file"""
        if hasattr(self, "_cached_prompt"):  # If already cached, reuse it
            return self._cached_prompt
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                self._cached_prompt = json.load(f)  # Cache the data
                logger.info(f"Successfully loaded prompt from {prompt_file}")
                return self._cached_prompt
        except FileNotFoundError:
            logger.error(f"Prompt file {prompt_file} not found!")
            return {}

    def generate_response(self, user_message: str, mention_special: bool) -> str:
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

        # If user mentions staking/BGT/BERA, add specific prompt
        if mention_special:
            strategy = self.prompt_data.get("special_handling", {}).get("response_strategy", [])
            messages.append({"role": "system", "content": " ".join(strategy)})

        messages.append({"role": "user", "content": user_message})

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4",
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.9  # Increase creativity
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response_data = response.json()

            if "error" in response_data:
                logger.error(f"OpenAI API error: {response_data['error']}")
                return "Got a little lag, try asking again! 😏"

            return response_data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            return "Got a little lag, try asking again! 😏"

bot_service = FlaskBotService()

# Middleware để yêu cầu token xác thực
def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or token != f"Bearer {TOKEN_ACCESS}":
            return jsonify({"error": "Invalid or missing token"}), 401
        return f(*args, **kwargs)
    return decorated

# API để liệt kê các file _prompt.json
@app.route("/api/prompts", methods=["GET"])
@require_token
def list_prompt_files():
    try:
        prompt_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith("_prompt.json")]
        return jsonify({"prompt_files": prompt_files}), 200
    except Exception as e:
        logger.error(f"Error listing prompt files: {str(e)}")
        return jsonify({"error": "Failed to list prompt files"}), 500

# API để xem nội dung file _prompt.json
@app.route("/api/prompt/<filename>", methods=["GET"])
@require_token
def get_prompt_file(filename):
    if not filename.endswith("_prompt.json"):
        return jsonify({"error": "Only files ending with _prompt.json are allowed"}), 403

    file_path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"File {filename} not found"}), 404

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        return jsonify({"filename": filename, "content": content}), 200
    except Exception as e:
        logger.error(f"Error reading prompt file {filename}: {str(e)}")
        return jsonify({"error": f"Failed to read {filename}"}), 500

# API để lưu nội dung file _prompt.json
@app.route("/api/prompt/<filename>", methods=["POST"])
@require_token
def save_prompt_file(filename):
    if not filename.endswith("_prompt.json"):
        return jsonify({"error": "Only files ending with _prompt.json are allowed"}), 403

    file_path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"File {filename} not found"}), 404

    try:
        new_content = request.get_json()
        if not new_content:
            return jsonify({"error": "No content provided"}), 400

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_content, f, indent=4)
        
        logger.info(f"Prompt file {filename} updated successfully")
        return jsonify({"message": f"File {filename} saved successfully"}), 200
    except Exception as e:
        logger.error(f"Error saving prompt file {filename}: {str(e)}")
        return jsonify({"error": f"Failed to save {filename}"}), 500

# API đăng nhập để xác thực ACCESS_KEY
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    access_key = data.get("password", "")  # Popup gửi ACCESS_KEY qua trường password

    if not access_key or access_key != TOKEN_ACCESS:
        return jsonify({"error": "Invalid ACCESS_KEY"}), 401
    
    # Nếu đúng, trả về token (ở đây dùng chính TOKEN_ACCESS làm token cho đơn giản)
    return jsonify({"token": TOKEN_ACCESS}), 200

# Route để phục vụ cms.html
@app.route("/cms")
def serve_cms():
    """Render cms.html from the frontend directory"""
    file_path = os.path.join(os.getcwd(), "frontend", "cms.html")
    if not os.path.exists(file_path):
        return "cms.html not found", 404

    with open(file_path, "r", encoding="utf-8") as f:
        return render_template_string(f.read())

# Các route hiện có của bạn
@app.route("/")
def home():
    """Render index.html from the root directory"""
    file_path = os.path.join(os.getcwd(), "index.html")
    if not os.path.exists(file_path):
        return "index.html not found", 404

    with open(file_path, "r", encoding="utf-8") as f:
        return render_template_string(f.read())

@app.route("/data/<path:filename>")
def serve_data_files(filename):
    """Serve files from the data/ directory"""
    data_dir = os.path.join(os.getcwd(), "data")
    file_path = os.path.join(data_dir, filename)

    if not os.path.exists(file_path):
        abort(404, description=f"File {filename} not found in /data/")

    try:
        return send_from_directory(data_dir, filename)
    except Exception as e:
        logging.error(f"[ERROR] Could not serve file {filename}: {e}")
        abort(500, description="Internal Server Error")

@app.route("/assets/<path:filename>")
def serve_assets_files(filename):
    """Serve files from the assets/ directory"""
    data_dir = os.path.join(os.getcwd(), "assets")
    file_path = os.path.join(data_dir, filename)

    if not os.path.exists(file_path):
        abort(404, description=f"File {filename} not found in /assets/")

    try:
        return send_from_directory(data_dir, filename)
    except Exception as e:
        logging.error(f"[ERROR] Could not serve file {filename}: {e}")
        abort(500, description="Internal Server Error")

@app.route("/status", methods=["GET"])
def status():
    """API to check system status"""
    return jsonify({
        "status": "running",
        "uptime": f"{datetime.now()}",
    })

@app.route("/chat", methods=["POST"])
def chat():
    """API Proxy to call OpenAI ChatGPT with custom prompt"""
    if not OPENAI_API_KEY:
        return jsonify({"error": "API Key not found"}), 500

    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        contains_trigger = any(keyword.lower() in user_message.lower() for keyword in bot_service.trigger_keywords)
        contains_banned = any(keyword.lower() in user_message.lower() for keyword in bot_service.banned_keywords)

        if contains_banned:
            return jsonify({"response": "Oh dear, such unrefined language! I'm a classy bot, let's keep it fun and drama-free. 😤"})

        response = bot_service.generate_response(user_message, contains_trigger)
        return jsonify({"response": response})

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return jsonify({"response": "Oops! I encountered an error, try again later. 😢"}), 500

# Run Flask API with Gunicorn
if __name__ == "__main__":
    logging.info("🚀 Starting Flask API with Gunicorn in production mode...")
    os.system("gunicorn --workers=4 --bind 0.0.0.0:5555 scripts.start_web_app:app")