import sys
from pathlib import Path

# Voeg het project-hoofdpad toe aan sys.path
base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir))  # Nu kan Python 'utils' vinden

import datetime as dt
import pandas as pd
from utils.logger import logger

vandaag = dt.datetime.today()

# Bepaal de paden
csv_path1 = base_dir / "data" / "database.csv"
csv_path2 = base_dir / "data" / "transfer_database.csv"
output_path1 = (base_dir / "data" / "backup" /
f"backup_database_week_{vandaag.isocalendar().week}.csv")
output_path2 = (base_dir / "data" / "backup" /
f"backup_transfer_database_week_{vandaag.isocalendar().week}.csv")

def run():
    if vandaag.weekday() == 3:
        df1 = pd.read_csv(csv_path1)
        df1.to_csv(output_path1, index=False)
        df2 = pd.read_csv(csv_path2)
        df2.to_csv(output_path2, index=False)
        logger.info(f"Database backup gemaakt op {vandaag.date()}")




if __name__ == "__main__":
    run()