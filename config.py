import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Scraper configuration

USE_SCRAPER = os.getenv("USE_SCRAPER", "true").lower() == "true"

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY", "ef4a1082cfd017155a366da6f03e538b") 