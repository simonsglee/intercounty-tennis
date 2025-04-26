# scripts/scraper.py
"""
INSTRUCTIONS FOR SCRAPING:

1. Go to: https://icmixed.tenniscores.com/
2. Select the desired Season (e.g., 2024).
3. Select the Division Group (e.g., Majors, A Division, B Division, C Division, etc.)
4. Select any specific Division inside that Group (e.g., Majors West, East Central 1, etc.)
   (✅ You do NOT have to select the first/top division — any division inside the group works.)
5. Click on the "Matches" tab to load the matches page.
6. Copy the full URL from your browser — this will be your entry URL.
7. Use that URL when calling `scrape_season_divisions(entry_url)`.

Note:
- The scraper will automatically detect and loop through ALL divisions inside the selected Division Group.
- The selected Season and Division Group must match what you want to scrape.
"""


from scripts.scraper_utils import scrape_season_divisions

if __name__ == "__main__":
    print("🔔 Reminder: Before pasting the URL, make sure you have:")
    print("   1. Selected the correct Season (e.g., 2024)")
    print("   2. Selected the correct Division Group (Majors, A, B, C, etc.)")
    print("   3. Entered any Division inside that group")
    print("   4. Clicked on the 'Matches' tab")
    print()
    entry_url = input("🔗 Paste the Intercounty Matches URL you want to scrape: ").strip()
    scrape_season_divisions(entry_url=entry_url)
