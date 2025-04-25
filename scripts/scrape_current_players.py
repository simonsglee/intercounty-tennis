# scripts/scrape_current_players.py

from scripts.scraper_utils import scrape_all_teams

if __name__ == "__main__":
    year = input("📅 Enter the current season year (e.g. 2024): ").strip()
    base_url = input("🔗 Paste the base URL for the current season standings page: ").strip()

    all_players = scrape_all_teams(base_url, year=year)
    print(f"\n🎉 Done scraping. Total players scraped: {len(all_players)}")
