
import requests
import time
import logging

logging.basicConfig(level=logging.INFO)

class ApiFetcher:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def fetch(self, url: str, headers: dict = None, params: dict = None, max_retries: int = 3, backoff_factor: float = 2.0):
        retries = 0
        delay = 1
        while retries < max_retries:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                if response.status_code == 401:
                    logging.error(f"401 Unauthorized: {url}")
                    raise Exception("Unauthorized: Check your API key and permissions.")
                if response.status_code == 404:
                    logging.error(f"404 Not Found: {url}")
                    raise Exception("Not Found: The requested resource does not exist.")
                if response.status_code == 429:
                    logging.warning(f"429 Rate Limit: {url}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries += 1
                    delay *= backoff_factor
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                logging.error(f"Timeout occurred for {url}. Retrying in {delay} seconds...")
                time.sleep(delay)
                retries += 1
                delay *= backoff_factor
            except requests.exceptions.ConnectionError:
                logging.error(f"Connection error for {url}. Retrying in {delay} seconds...")
                time.sleep(delay)
                retries += 1
                delay *= backoff_factor
            except Exception as e:
                logging.error(f"Unexpected error for {url}: {e}")
                raise Exception(str(e))
        raise Exception(f"Failed after {max_retries} retries: {url}")
