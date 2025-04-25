# scripts/scraper.py

# REMOVE: import argparse
from scripts.scraper_utils import scrape_season_divisions

if __name__ == "__main__":
    entry_url = input("🔗 Paste the Intercounty division URL you want to scrape: ").strip()
    scrape_season_divisions(entry_url=entry_url)
