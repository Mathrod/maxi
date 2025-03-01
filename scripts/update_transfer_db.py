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

    
    yesterday = datetime.today() - timedelta(days=1)
    input_file = (base_dir / "data" / "open_transfers" / f"{yesterday.strftime('%Y%m%d')}_open_transfers.csv")
    df_yesterday = pd.read_csv(input_file)

    df_yesterday["AtleetId"] = df_yesterday["AtleetID"].astype(int)

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
                lengte, gewicht, vorm, ervaring, humeur, fav, deadline = fysiek_data
                
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
    df_diff = df_yesterday[~df_yesterday["AtleetID"].isin(df_atleet_data["AtleetID"])]
    df_transfer_database = pd.read_csv(base_dir / "data"/ "transfer_database.csv")

    logger.info(f"Total records transfer_database.csv before updating {len(df_transfer_database)}")

    for x, row in df_diff.iterrows():
        atleet_id = row["AtleetID"]
        deadline = row["Deadline"]
        datum, waarde = get_transfer_details(atleet_id, session)
        atleet = df_yesterday[df_yesterday["AtleetID"] == atleet_id].copy()
        
        if type(deadline) == str:
            deadline = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        if type(datum) == str:
            datum = datetime.strptime(datum, "%Y-%m-%d")
        
        if abs(datum - deadline).days <= 2:
            atleet["Waarde"] = waarde
        else:
            atleet["Waarde"] = 0

        df_transfer_database = pd.concat([df_transfer_database, atleet], ignore_index=True)

    df_transfers_database_uniek = df_transfer_database.drop_duplicates(keep=False)
    
    df_transfers_database_uniek.to_csv(base_dir / "data" / "transfer_database.csv", index=False)
    output_path = (base_dir / "data" /"open_transfers"/ f"{datetime.today().strftime('%Y%m%d')}_open_transfers.csv")
    
    df_atleet_data.to_csv(output_path, index=False)
    logger.info(f"Total records transfer_database.csv after updating {len(df_transfer_database)}")

    session.get(logout_url)  # Dit beëindigt de sessie
    session.close()

if __name__ == "__main__":
    run()