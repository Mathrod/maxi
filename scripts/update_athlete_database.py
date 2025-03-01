import sys
from pathlib import Path

# Voeg het project-hoofdpad toe aan sys.path
base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir))  # Nu kan Python 'utils' vinden

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import ast
from utils.logger import logger
from utils.helpers import get_latest_test_results, fetch_page, parse_athlete_row, fetch_athlete_data

def run():
    logger.info("Start updating athlete database...")
    load_dotenv()
    login_url = "https://www.maxithlon.com/accesscontrol.php"
    target_url = "https://www.maxithlon.com/varie/mercato.php"
    logout_url = "https://www.maxithlon.com/logout.php"

    payload = {
        "user": os.getenv("MAXITHLON_USER"),
        "password": os.getenv("MAXITHLON_PASS"),
        "id_gioco": "1",
        "user_control": "Login",
    }

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Referer": "https://www.maxithlon.com/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.maxithlon.com",
    }

    login_response = fetch_page(login_url, session, method="post", data=payload)

    if login_response and login_response.status_code in (200, 302):
        logger.info("Login successful!")
    else:
        logger.error(f"Login failed, login_response: \n{login_response}")
        return
    
    search_data = {
        "min_forza": "0",
        "new_scadenza": "0",
        "youth": "0",
        "mercato": "1",
        "libero": "1",
        "new_sesso": "2",
        "ric_1": "Zoek",
    }

    response = fetch_page(target_url, session, method="post", data=search_data)

    if not response:
        logger.error("Failed to fetch athlete market data.")
        return
    
    logger.info("Athlete market data fetched successfully!")


    all_athletes = []
    page_number = 1

    while True:
        if page_number > 1:
            response = fetch_page(f"{target_url}?p={page_number}&bm=", session)
            if not response:
                break

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="results")

        if table is None:
            logger.error(f"Error: Could not find the expected results table on page {page_number}. Possible session expiration or page structure change.")
            logger.error("Response preview: %s", response.text[:500])
            return

        next_page = soup.find("a", href=f"{target_url}?p={page_number+1}&bm=")

        for row in table.find_all("tr")[1:]:
            athlete_data = parse_athlete_row(row)
            if athlete_data:
                naam, atleet_id, geslacht, land, leeftijd, maxid, specialiteit, skills = athlete_data
                fysiek_data = fetch_athlete_data(atleet_id, session)
                if fysiek_data:
                    lengte, gewicht, vorm, ervaring, humeur, fav, club = fysiek_data
                    weekly_test = session.get(f"https://www.maxithlon.com/user/test_settimanali.php?aid={atleet_id}")
                    soup = BeautifulSoup(weekly_test.text, "html.parser")
                    table = soup.find("table")
                    week = int(table.find_all("tr")[1].find_all("th")[-1].text.strip())
                    test_results = get_latest_test_results(table, week)
                    all_athletes.append([fav, naam, atleet_id, int(leeftijd), land, geslacht, int(maxid), specialiteit, int(humeur), int(ervaring), int(vorm), lengte, gewicht, test_results, club] + skills)

        if not next_page:
            break
        logger.info(f"Scraped page {page_number}")
        page_number += 1

    columns = [
        "Favoriete onderdeel", "Naam", "AtleetID", "Leeftijd", "Land", "Geslacht", "MaxID", 
        "Specialiteit", "Humeur", "Ervaring", "Vorm", "Lengte", "Gewicht", "Resultaten test", "Club",
        "Zorg", "Kracht", "Uithouding", "Snelheid", "Lenigheid", "Springen", "Werpen", "SP1", "SP2"]

    df = pd.DataFrame(all_athletes, columns=columns)
    output_path = (base_dir / "data" / "atleten_data" / f"atleten_data_{datetime.today().strftime('%Y%m%d')}.csv")
    df.to_csv(output_path, index=False)
    logger.info(f"{len(df)} athlete records saved to {output_path.name}")

    # Integrate merge_data.py functionality
    atleten_file = output_path
    database_file = (base_dir / "data" / "database.csv")

    # CSV-bestanden inlezen
    df_atleten = pd.read_csv(atleten_file)
    df_database = pd.read_csv(database_file)

    logger.info(f"Total records database.csv before updating {len(df_database)}")

    # Nieuwe DataFrame voor de opgesplitste data
    expanded_rows = []

    # Itereer over elke rij in df_atleten
    for _, row in df_atleten.iterrows():
        atleet_data = row.drop(["Resultaten test"]).to_dict()  # Bewaar alle andere kolommen behalve "Resultaten test"
        
        # Probeer de "Resultaten test" kolom te evalueren (omzetten van string naar lijst van tuples)
        try:
            resultaten = ast.literal_eval(row["Resultaten test"])  # Converteer de string-lijst naar echte lijst
        except:
            resultaten = []  # Als conversie faalt, gebruik een lege lijst
        
        # Itereer over de resultaten en maak een nieuwe rij voor elk resultaat
        for resultaat in resultaten:
            if len(resultaat) >= 4:  # Zorg ervoor dat de structuur correct is
                nieuwe_rij = atleet_data.copy()  # Kopieer de originele rij zonder "Resultaten test"
                nieuwe_rij["Discipline"] = resultaat[0]
                nieuwe_rij["Resultaat"] = resultaat[1]
                nieuwe_rij["Punten Resultaat"] = resultaat[2]
                nieuwe_rij["Week"] = resultaat[3]
                expanded_rows.append(nieuwe_rij)

    # Maak een DataFrame van de opgesplitste rijen
    df_expanded = pd.DataFrame(expanded_rows)

    # Controleer of database niet leeg is en filter op unieke (AthleetID, Week) combinaties
    if not df_database.empty:
        df_merged = pd.concat([df_database, df_expanded], ignore_index=True)
        df_merged = df_merged.drop_duplicates(subset=["AtleetID", "Week", "Discipline"], keep="first")
    else:
        df_merged = df_expanded  # Als database leeg is, gebruik direct de nieuwe data

    # Opslaan naar database.csv
    df_merged.to_csv(database_file, index=False)

    logger.info(f"Total records database.csv after updating {len(df_merged)}")

    session.get(logout_url)  # Dit beëindigt de sessie
    session.close()

if __name__ == "__main__":
    run()