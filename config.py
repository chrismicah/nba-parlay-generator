import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Scraper configuration

USE_SCRAPER = os.getenv("USE_SCRAPER", "true").lower() == "true"

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY") 