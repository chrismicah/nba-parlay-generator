from tools.tweet_scraper import scrape_tweets

scrape_tweets(
    keywords=["injury report", "lineup news"],
    usernames=["ShamsCharania", "wojespn", "underdog_nba"],
    since="2024-10-01",
    max_tweets=150,
    output_name="nba_injury_news"
)