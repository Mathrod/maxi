import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir))

import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime
from utils.logger import logger


def get_latest_test_results(soup, week):
    resultaten = []
    new_week = week

    for row in soup.find_all("tr"):
        img = row.find("img", {"title": True})  # Zoek afbeelding met title attribuut (discipline naam)
        if img:
            discipline = img["title"]  # Discipline naam
            prestaties = row.find_all("td", align="center", class_="vtip")  # Alle prestatie cellen
    
            if prestaties:
                if prestaties[-1].get_text(strip=True) == "":
                    laatste_prestatie = prestaties[-2].get_text(strip=True) # Laatste prestatie (op één na laatste <td>)
                    laatste_title = prestaties[-2]["title"]  # Laatste prestatie's title attribuut
                    if new_week == week:
                        new_week -= 1
                else:
                    laatste_prestatie = prestaties[-1].get_text(strip=True) # Laatste prestatie (op één na laatste <td>)
                    laatste_title = prestaties[-1]["title"]  # Laatste prestatie's title attribuut
                
                if laatste_prestatie:
                    resultaten.append((discipline, laatste_prestatie, laatste_title, new_week))
                    
    return resultaten

def fetch_page(url, session, params=None, method="get", data=None):
    for _ in range(3):  # Retry mechanism
        try:
            if method == "post":
                response = session.post(url, data=data, timeout=10)
            else:
                response = session.get(url, params=params, timeout=10)
            
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            time.sleep(1)
    return None


def parse_athlete_row(row):
    cols = row.find_all("td")
    if len(cols) > 1:
        naam_tag = cols[1].find("a")
        naam = naam_tag.text.strip() if naam_tag else ""                
        atleet_id = naam_tag["href"].split("aid=")[-1].split("&")[0] if naam_tag else "" 
        
        kleur_tag = cols[1].find("font")
        geslacht = "Man" if kleur_tag and kleur_tag["color"] == "#32A9AF" else "Vrouw"
        
        land = cols[0].find("img")["title"].strip() if cols[0].find("img") else ""
        leeftijd = cols[2].text.strip()
        maxid = cols[3].text.strip()
        specialiteit = cols[4].text.strip()
        skills = [int(col.text.strip()) for col in cols[5:]]
        
        return naam, atleet_id, geslacht, land, leeftijd, maxid, specialiteit, skills
    return None


def fetch_athlete_data(atleet_id, session):
    atleet_data = fetch_page(f"https://www.maxithlon.com/user/atleta_one.php?aid={atleet_id}&tipo=aid", session)
    if not atleet_data:
        return None
    
    soup = BeautifulSoup(atleet_data.text, "html.parser")

    # Fysiek (lengte en gewicht)
    lengte, gewicht = [int(x.split(" ")[0]) for x in soup.find_all("div", class_="col02")[1].find("strong").text.split(" - ")]
    
    # Vorm
    vorm_element = soup.find("div", class_="box")
    vorm = vorm_element.find("strong").text.strip() if vorm_element else "Onbekend"

    # Ervaring
    ervaring_element = soup.find("div", class_="box box_right").find("span", string="Ervaring:")
    ervaring = ervaring_element.find_next("strong").text.strip() if ervaring_element else "Onbekend"

    # Humeur
    humeur_element = soup.find_all("div", class_="row gray")[1].find("span", string="Humeur:")
    humeur = humeur_element.find_next("strong").text.strip() if humeur_element else "Onbekend"

    # club
    club = bool(soup.find_all("div", class_="col01")[0].find("strong").text)

    # Favoriete onderdeel
    try:
        fav_element = soup.find("h4", class_="heading").find("strong", class_="right")
        fav = fav_element.get_text(strip=True) if fav_element else "Onbekend"
    except AttributeError:
        fav = "Onbekend"

    return lengte, gewicht, vorm, ervaring, humeur, fav, club


def get_transfer_details(atleet_id, session):
    transfer_data = fetch_page(f"https://www.maxithlon.com/user/trasf_one.php?aid={atleet_id}", session)
    
    # HTML parser
    soup = BeautifulSoup(transfer_data.text, "html.parser")

    if "Over deze atleet is nooit onderhandeld." in soup.get_text():
        return datetime(1,1,1), 0

    # Zoek de tabel
    table = soup.find("table", class_="results")

    # Controleer of er rijen in de tabel zijn behalve de header
    rows = table.find_all("tr")[1:] if table else []

    row = rows[1]
    cells = row.find_all("td")
    if len(cells) >= 4:
        datum_str = cells[0].text.strip()
        waarde_text = cells[3].text.strip()

        # Converteer waarde van "€ 1.000" naar integer 1000
        datum = datetime.strptime(datum_str, "%d-%m-%Y")
        waarde = int(waarde_text.replace("€", "").replace(".", "").strip())

        return datum, waarde

    return datetime(1,1,1), 0