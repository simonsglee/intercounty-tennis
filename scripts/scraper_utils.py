# scripts/scraper_utils.py

import time
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin, urlparse, parse_qs
import base64

def clean_filename(s):
    return re.sub(r"[^\w\-]", "-", s).strip("-").replace("--", "-")

def decode_player_id(href):
    query = urlparse(href).query
    p_encoded = parse_qs(query).get("p")
    if p_encoded:
        try:
            return base64.b64decode(p_encoded[0]).decode("utf-8")
        except Exception:
            return p_encoded[0]
    return "N/A"

def count_games(score_str):
    score_str = re.sub(r"\[.*?\]", "", score_str)
    sets = score_str.split(",")
    home_games = 0
    away_games = 0
    for s in sets:
        s = s.strip()
        if "-" in s:
            try:
                home, away = map(int, s.split("-"))
                home_games += home
                away_games += away
            except ValueError:
                pass
    return home_games, away_games

def extract_all_matches(html, season, division):
    soup = BeautifulSoup(html, "html.parser")
    fixtures = soup.select("div.match_results_table")
    all_matches = []

    for i, fixture in enumerate(fixtures):
        date_tag = fixture.select_one("div.match_rest")
        date = date_tag.text.strip() if date_tag else "N/A"

        home_team_tag = fixture.select_one("div.team_name a")
        home_team = home_team_tag.text.strip() if home_team_tag else "N/A"

        away_team_tag = fixture.select_one("div.team_name2 a")
        away_team = away_team_tag.text.strip() if away_team_tag else "N/A"

        match_blocks = fixture.select("div.match_results_content")[1:]
        line_number = 1

        for block in match_blocks:
            try:
                home_tags = block.select("div.team_name a")
                away_tags = block.select("div.team_name2 a")

                home_names = [a.text.strip() for a in home_tags]
                home_ids = [decode_player_id(a['href']) for a in home_tags]

                away_names = [a.text.strip() for a in away_tags]
                away_ids = [decode_player_id(a['href']) for a in away_tags]

                score_tag = block.select_one("div.match_rest")
                score = score_tag.text.strip() if score_tag else "N/A"

                if score == "N/A" and len(home_names) == 0 and len(away_names) == 0:
                    continue

                home_text = block.select_one("div.team_name").text if block.select_one("div.team_name") else ""
                away_text = block.select_one("div.team_name2").text if block.select_one("div.team_name2") else ""

                home_defaulted = "By Default" in home_text or "By Forfeit" in home_text
                away_defaulted = "By Default" in away_text or "By Forfeit" in away_text
                is_default = home_defaulted or away_defaulted

                match_record = {
                    "Season": season,
                    "Division": division,
                    "Date": date,
                    "Home Team": home_team,
                    "Away Team": away_team,
                    "Line": line_number,
                    "Score": score,
                    "Defaulted": is_default
                }

                if is_default:
                    if len(home_names) == 2:
                        match_record.update({
                            "Home Player 1": home_names[0],
                            "Home ID 1": home_ids[0],
                            "Home Player 2": home_names[1],
                            "Home ID 2": home_ids[1],
                        })
                    if len(away_names) == 2:
                        match_record.update({
                            "Away Player 1": away_names[0],
                            "Away ID 1": away_ids[0],
                            "Away Player 2": away_names[1],
                            "Away ID 2": away_ids[1],
                        })
                else:
                    if len(home_names) == 2 and len(away_names) == 2:
                        home_games, away_games = count_games(score)
                        match_record.update({
                            "Home Player 1": home_names[0],
                            "Home ID 1": home_ids[0],
                            "Home Player 2": home_names[1],
                            "Home ID 2": home_ids[1],
                            "Away Player 1": away_names[0],
                            "Away ID 1": away_ids[0],
                            "Away Player 2": away_names[1],
                            "Away ID 2": away_ids[1],
                            "Home Games Won": home_games,
                            "Away Games Won": away_games,
                        })

                all_matches.append(match_record)
                line_number += 1

            except Exception as e:
                print(f"❌ Error in fixture {i+1}, match {line_number}: {e}")

    return all_matches

def scrape_season_divisions(entry_url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("🌐 Loading provided URL...")
    driver.get(entry_url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "arch_season_list")))
        season_dropdown = Select(driver.find_element(By.ID, "arch_season_list"))
        season = season_dropdown.first_selected_option.text.strip()
    except Exception as e:
        print("❌ Could not determine season from the dropdown.")
        driver.quit()
        return

    os.makedirs("data/processed", exist_ok=True)

    group_dropdown = Select(driver.find_element(By.ID, "divgs_list"))
    group_dropdown.select_by_index(1)
    time.sleep(2)

    division_select = Select(driver.find_element(By.ID, "divgs_div_list"))
    division_options = [o.text.strip() for o in division_select.options if "Select" not in o.text]

    print(f"📋 Found {len(division_options)} divisions to scrape for {season}")

    for division in division_options:
        print(f"🔄 Scraping division: {division}")
        try:
            Select(driver.find_element(By.ID, "divgs_div_list")).select_by_visible_text(division)
            time.sleep(2)

            driver.find_element(By.LINK_TEXT, "Matches").click()
            time.sleep(3)

            html = driver.page_source
            matches = extract_all_matches(html, season, division)

            if matches:
                df = pd.DataFrame(matches)
                filename = f"data/processed/ic_mixed_matches_{clean_filename(season)}_{clean_filename(division)}.csv"
                df.to_csv(filename, index=False)
                print(f"   ✅ Saved {len(df)} matches → {filename}")
            else:
                print(f"   ⚠️ No matches found for {division}")

        except Exception as e:
            print(f"   ❌ Failed to scrape division: {division}. Error: {e}")
            continue

    driver.quit()
    print(f"\n🎉 Done scraping all divisions for season {season}")

def scrape_roster_page(driver, team_url, team_name, team_id):
    driver.get(team_url)
    time.sleep(3)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # 🌟 Extract division name
    division_header = soup.find("div", class_="shader team_nav team_nav2")
    division = None
    if division_header:
        div_text = division_header.find("div")
        if div_text:
            raw_division = div_text.text.strip()
            division = raw_division.split("Standings")[0].strip()

    table = soup.find("table", class_="team_roster_table")
    if not table:
        print(f"⚠️ No roster table found for {team_name}")
        return []

    rows = table.find_all("tr")
    section = None
    players = []

    for row in rows:
        th = row.find("th", class_="player_col")
        if th:
            if "Captains" in th.text:
                section = "Captain"
            elif "Players" in th.text:
                section = "Player"
            continue

        a_tag = row.find("a", href=True)
        if not a_tag:
            continue

        name = a_tag.text.strip()
        full_text = row.get_text(separator=" ", strip=True)
        suffix = full_text.replace(name, "").strip()
        player_id = decode_player_id(a_tag["href"])

        players.append({
            "Division": division,
            "Team": team_name,
            "Team ID": team_id,
            "Name": name,
            "Suffix": suffix,
            "ID": player_id,
            "Role": section
        })

    return players

def get_team_links(driver, base_url):
    from urllib.parse import urljoin, urlparse, parse_qs

    driver.get(base_url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    team_links = []

    current_division = None
    ul = soup.find("ul", class_="team-selector")
    for li in ul.find_all("li"):
        # Check if it's a division header
        if "division" in li.get("class", []):
            current_division = li.text.strip()
            continue

        if "divteamer" not in li.get("class", []):
            continue

        a = li.find("a", href=True)
        if not a:
            continue

        team_url = urljoin(base_url, a["href"])
        team_name_div = a.find("div")
        team_name = team_name_div.text.strip() if team_name_div else "Unknown"

        parsed = urlparse(team_url)
        team_id = parse_qs(parsed.query).get("team", ["N/A"])[0]

        team_links.append({
            "team_name": team_name,
            "team_url": team_url,
            "team_id": team_id,
            "division": current_division
        })

    return team_links

def scrape_all_teams(base_url, year="2024"):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    print("🌐 Loading division page...")
    team_links = get_team_links(driver, base_url)
    print(f"📋 Found {len(team_links)} teams.")

    all_players = []

    for team in team_links:
        team_name = team["team_name"]
        team_url = team["team_url"]
        team_id = team["team_id"]
        division = team["division"]

        print(f"🔄 Scraping {team_name}...")
        players = scrape_roster_page(driver, team_url, team_name, team_id)
        all_players.extend(players)

        df = pd.DataFrame(players)
        if not df.empty:
            safe_team_name = team_name.lower().replace(" ", "-")
            os.makedirs("data/processed", exist_ok=True)
            filename = f"data/processed/ic_mixed_roster_{year}_{safe_team_name}.csv"
            df.to_csv(filename, index=False)
            print(f"   ✅ Saved {len(df)} players → {filename}")
        else:
            print(f"   ⚠️ No data found for {team_name}")

    driver.quit()
    return all_players

