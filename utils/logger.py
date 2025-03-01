import logging
from pathlib import Path

# Zorg ervoor dat de logs-map bestaat
log_dir = Path(__file__).resolve().parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Logbestand pad
log_file = log_dir / "app.log"

# Maak een custom logfilter
class ExcludeScrapeFilter(logging.Filter):
    """Filtert logberichten die 'Scraped page' bevatten uit het logbestand."""
    def filter(self, record):
        return "Scraped page" not in record.getMessage()

# Maak de logger aan
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Alle niveaus beschikbaar

# 🔹 FileHandler → Slaat logs op (maar zonder 'Scraped page')
file_handler = logging.FileHandler(log_file, mode="a")
file_handler.setLevel(logging.INFO)
file_handler.addFilter(ExcludeScrapeFilter())  # 👈 Filter toevoegen

# 🔹 ConsoleHandler → Toont ALLES (incl. 'Scraped page')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Laat alles in de CMD zien

# Formatter instellen
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Voeg handlers toe aan de logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
