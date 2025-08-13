import subprocess

accounts = [
    "ShamsCharania",
    # "wojespn",  # excluded
    "ChrisBHaynes",
    "Marc_DAmico",
    "Rotoworld_BK",
    "danbesbris",
    "Underdog__NBA",
    "SteveJonesJr",
    # Additional relevant NBA accounts
    "NBACentral",
    "BleacherReport",
    "statmuse",
    "TheSteinLine",
    "wojespnESPNU",  # placeholder alt; safe to skip if not found
]

for acct in accounts:
    subprocess.run(
        ["python", "tools/twitter_scraper.py", "--account", acct, "--scrolls", "45"],
        check=False,
    )


