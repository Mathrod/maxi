@echo off
call micromamba activate maxithlon-env || exit /b
cd /d C:\Users\mathi\Documents\programmeren\maxithlon
python scripts/update_athlete_database.py
python scripts/update_transfer_db.py
python scripts/backup_database.py
exit
