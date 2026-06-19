import os
import django
import sys
import pandas as pd
from datetime import datetime

# Setup Django
sys.path.append('/home/edgar/ANAM/EjeCentral/eje_central_back')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eje_central_back.settings')
django.setup()

from plantilla.models import CuadroVacancia

def parse_date(date_str):
    if not isinstance(date_str, str):
        return None
    
    date_str = date_str.lower().strip()
    
    months = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
        'dic': 12
    }
    
    # Check if it has a day
    # formats: "01 abril, 2026", "19 mayo, 2026"
    import re
    match_day = re.match(r'(\d{1,2})\s+([a-z]+)[,\s]+(\d{4})', date_str)
    if match_day:
        day = int(match_day.group(1))
        month = months.get(match_day.group(2))
        year = int(match_day.group(3))
        if month:
            return datetime(year, month, day).date()

    # Check if it's just month and year
    # formats: "enero, 2025", "dic, 2025"
    match_month = re.match(r'([a-z]+)[,\s]+(\d{4})', date_str)
    if match_month:
        month = months.get(match_month.group(1))
        year = int(match_month.group(2))
        if month:
            # default to 1st of the month
            return datetime(year, month, 1).date()
            
    return None

def run():
    df = pd.read_excel('/home/edgar/Descargas/12 06 2026 Movimientos 1135 V.2.xlsx', sheet_name='Cuadros Vacancia', header=None)
    data = df.iloc[2:24, 0:11].to_dict('records')
    
    inserted = 0
    for row in data:
        qna_str = row[1]
        
        # Skip header rows or textual rows
        if pd.isna(row[2]) or row[2] == 'Permanente' or row[2] == 'Ocupadas':
            continue
            
        parsed_date = parse_date(qna_str)
        if not parsed_date:
            continue
            
        try:
            CuadroVacancia.objects.update_or_create(
                fecha=parsed_date,
                defaults={
                    'ocupadas_permanente': int(row[2]) if not pd.isna(row[2]) else 0,
                    'ocupadas_eventual': int(row[3]) if not pd.isna(row[3]) else 0,
                    'ocupadas_total': int(row[4]) if not pd.isna(row[4]) else 0,
                    'vacantes_permanente': int(row[5]) if not pd.isna(row[5]) else 0,
                    'vacantes_eventual': int(row[6]) if not pd.isna(row[6]) else 0,
                    'vacantes_total': int(row[7]) if not pd.isna(row[7]) else 0,
                    'total_permanente': int(row[8]) if not pd.isna(row[8]) else 0,
                    'total_eventual': int(row[9]) if not pd.isna(row[9]) else 0,
                    'total': int(row[10]) if not pd.isna(row[10]) else 0,
                }
            )
            inserted += 1
            print(f"Imported date: {parsed_date}")
        except Exception as e:
            print(f"Error importing row {row}: {e}")
            
    print(f"Total inserted: {inserted}")

if __name__ == '__main__':
    run()
