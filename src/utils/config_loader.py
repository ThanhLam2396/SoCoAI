import json
import os

def load_config(file_path):
    """Load cấu hình từ file JSON."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

# Load settings từ file
CONFIG = load_config("config/settings.json")
