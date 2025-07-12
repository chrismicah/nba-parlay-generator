import requests
from config import THE_ODDS_API_KEY

class OddsFetcherTool:
    def get_game_odds(self, sport_key, regions, markets):
        """
        Fetch game odds from The Odds API
        
        Args:
            sport_key (str): The sport key (e.g., 'basketball_nba')
            regions (str): Comma-separated regions (e.g., 'us')
            markets (str): Comma-separated markets (e.g., 'h2h,spreads,totals')
            
        Returns:
            dict: JSON response from The Odds API
        """
        if not THE_ODDS_API_KEY:
            raise ValueError("THE_ODDS_API_KEY not found in environment variables")
        
        # Construct the API URL
        base_url = "https://api.the-odds-api.com/v4/sports"
        url = f"{base_url}/{sport_key}/odds"
        
        # Set up query parameters
        params = {
            'apiKey': THE_ODDS_API_KEY,
            'regions': regions,
            'markets': markets
        }
        
        try:
            # Make the API request
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch odds from The Odds API: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid JSON response from The Odds API: {str(e)}") 
        
