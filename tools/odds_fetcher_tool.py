from tools.api_fetcher import ApiFetcher
from config import THE_ODDS_API_KEY

class OddsFetcherTool:
    def __init__(self):
        self.api_fetcher = ApiFetcher(api_key=THE_ODDS_API_KEY)

    def get_game_odds(self, sport_key, regions, markets):
        """
        Fetch game odds from The Odds API
        
        Args:
            sport_key (str): The sport key (e.g., 'basketball_nba')
            regions (str): The regions to fetch odds for (e.g., 'us')
            markets (str): The markets to fetch odds for (e.g., 'h2h,spreads')
        """
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        params = {
            "regions": regions,
            "markets": markets,
            "apiKey": self.api_fetcher.api_key
        }
        return self.api_fetcher.fetch(url, params=params)