import gspread
import os
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from src.utils.config_loader import CONFIG  # Load config from settings.json

# Retrieve information from settings.json
GOOGLE_SHEET_CREDENTIALS = CONFIG.get("GOOGLE_SHEET_CREDENTIALS", "path/to/your/google-credentials.json")  
SPREADSHEET_ID = CONFIG.get("SPREADSHEET_ID", None)  

# File containing generated news
GENERATED_NEWS_FILE = "data/generated_news.txt"

if not SPREADSHEET_ID:
    raise ValueError("[❌] SPREADSHEET_ID not configured in settings.json!")

class PostToGoogleSheetsService:
    """Service to save news to Google Sheets by week."""

    def __init__(self):
        self.client = self.authenticate_google_sheets()

    def authenticate_google_sheets(self):
        """Authenticate and connect to Google Sheets API."""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEET_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client

    def get_current_week_info(self):
        """Calculate week number in the month based on Monday-Sunday."""
        today = datetime.date.today()
        first_day_of_month = today.replace(day=1)
        month = today.strftime("%m")  # Get current month
        year = today.strftime("%Y")  # Get current year

        # Find the first day of the week containing the first day of the month
        first_weekday = first_day_of_month.weekday()  # Monday = 0, Sunday = 6
        first_monday = first_day_of_month if first_weekday == 0 else first_day_of_month + datetime.timedelta(days=(7 - first_weekday))

        # Calculate current week based on the nearest Monday
        week_start = first_monday
        week_of_month = 1

        while week_start + datetime.timedelta(days=6) < today:
            week_start += datetime.timedelta(days=7)
            week_of_month += 1

        week_end = week_start + datetime.timedelta(days=6)

        # Format sheet name: WeekX-MM-YYYY(DD/MM-DD/MM/YYYY)
        sheet_name = f"Week{week_of_month}-{month}-{year}({week_start.strftime('%d/%m')}-{week_end.strftime('%d/%m/%Y')})"
        
        return sheet_name

    def get_or_create_weekly_sheet(self):
        """Create a new sheet if it doesn't exist, or retrieve the current week's sheet."""
        sheet_name = self.get_current_week_info()
        sheet = self.client.open_by_key(SPREADSHEET_ID)

        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="3000", cols="5")

            # Write column headers when creating a new sheet
            worksheet.append_row(["Date", "Author", "Title", "Content", "Link"])

            # Define column widths
            self.set_column_width(worksheet)

        return worksheet

    def set_column_width(self, worksheet):
        """Set column widths in Google Sheets."""
        requests = [
            {"updateDimensionProperties": {
                "range": {"sheetId": worksheet.id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": size},
                "fields": "pixelSize"
            }} for i, size in enumerate([100, 150, 300, 1000, 250])  # Columns: Date, Author, Title, Content, Link
        ]

        body = {"requests": requests}
        worksheet.spreadsheet.batch_update(body)
        print("[✅] Column widths set successfully!")

    def load_news_data(self):
        """Read news content from generated_news.txt."""
        if not os.path.exists(GENERATED_NEWS_FILE):
            print("[⚠️] File generated_news.txt not found!")
            return []

        with open(GENERATED_NEWS_FILE, "r", encoding="utf-8") as f:
            news_list = f.read().strip().split("\n\n")  # Split by news items

        parsed_news = []
        for news in news_list:
            lines = news.split("\n")
            if len(lines) < 3:
                continue  # Skip invalid news items

            title = lines[0].strip()
            author = next((word for word in lines[1].split() if word.startswith("@")), "Unknown")
            content_lines = lines[1:]  # Take all lines after title
            content = " ".join(content_lines).split("📎")[0].strip()  # Remove portion after 📎
            link = lines[-1].split()[-1] if lines[-1].startswith("📎") and lines[-1].split()[-1].startswith("http") else ""

            parsed_news.append((str(datetime.date.today()), author, title, content, link))

        return parsed_news

    def save_news_to_google_sheet(self):
        """Save news to Google Sheet by week."""
        worksheet = self.get_or_create_weekly_sheet()
        news_data = self.load_news_data()

        if not news_data:
            print("[⚠️] No news to save to Google Sheets.")
            return

        for row in news_data:
            worksheet.append_row(row)

        print(f"[✅] Saved {len(news_data)} news items to Google Sheet!")

# Run script
if __name__ == "__main__":
    service = PostToGoogleSheetsService()
    service.save_news_to_google_sheet()