import sys
from pathlib import Path

# Voeg het project-hoofdpad toe aan sys.path
base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir)) 

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.logger import logger
from utils.helpers import fetch_page, parse_athlete_row, fetch_athlete_data, get_transfer_details


def run():
    logger.info("Start updating transfer database...")
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

    login_response = fetch_page(login_url, session, method="post", data=payload)

    if login_response and login_response.status_code in (200, 302):
        logger.info("Login successful!")
    else:
        logger.error("Login failed")
        return
    
    search_data = {
        "min_forza": "0",
        "new_scadenza": "144",
        "youth": "0",
        "mercato": "1",
        "libero": "0",
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
                lengte, gewicht, vorm, ervaring, humeur, fav, _, deadline = fysiek_data
                
                all_athletes.append([fav, naam, int(atleet_id), int(leeftijd), land, geslacht, int(maxid), specialiteit, int(humeur), int(ervaring), int(vorm), lengte, gewicht, deadline] + skills)

        if not next_page:
            break
        logger.info(f"Scraped page {page_number}")
        page_number += 1

    columns = [
        "Favoriete onderdeel", "Naam", "AtleetID", "Leeftijd", "Land", "Geslacht", "MaxID", 
        "Specialiteit", "Humeur", "Ervaring", "Vorm", "Lengte", "Gewicht", "Deadline", "Zorg", "Kracht", 
        "Uithouding", "Snelheid", "Lenigheid", "Springen", "Werpen", "SP1", "SP2"]

    df_atleet_data = pd.DataFrame(all_athletes, columns=columns)
    output_path = (base_dir / "data" / f"{datetime.today().strftime('%Y%m%d')}_open_transfers.csv")
    df_atleet_data.to_csv(output_path, index=False)

    logger.info(f"{len(df_atleet_data)} records saved to {output_path}")
    session.get(logout_url)  # Dit beëindigt de sessie
    session.close()


if __name__ == "__main__":
    file = (base_dir / "data" / f"{datetime.today().strftime('%Y%m%d')}_open_transfers.csv")
    if os.path.exists(file):
        logger.info("File already exists, no need to update.")
    else:
        run()