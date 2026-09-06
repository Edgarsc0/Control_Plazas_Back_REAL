import os
import sys
import django
import urllib.request
import urllib.parse
import json
import time
from django.db import connection

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eje_central_back.settings")
django.setup()

from plantilla.models import EmpleadosCompletosSig

def clean_address(addr):
    if not addr:
        return ""
    addr = addr.strip()

    # Check for "Torre Caballito"
    if "Torre Caballito" in addr or "Caballito Reforma 10" in addr:
        return "Paseo de la Reforma 10, Tabacalera, Cuauhtémoc, Ciudad de México, 06030, México"

    # Check for "Lucas Alamán"
    if "L.  Alamán" in addr or "L. Alamán" in addr or "Lucas Alaman" in addr:
        return "Calle Lucas Alamán 111, Obrera, Cuauhtémoc, Ciudad de México, 06800, México"

    # Check for "Laboratorio Central"
    if "Laboratorio Central" in addr:
        return "San Lorenzo 252, Miguel Hidalgo, Ciudad de México"

    # Check for "Chichimequillas"
    if "Chichimequilla" in addr:
        return "Chichimequillas, El Marqués, Querétaro, México"

    # Check for Tlalpan
    if "Tlalpan" in addr:
        return "Tlalpan, Ciudad de México, México"

    return addr

def geocode_external(address):
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': address,
        'format': 'json',
        'limit': 1
    })
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'ANAMEjeCentralGeocoding/1.0 (edgar@anam.gob.mx)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Error calling Nominatim for '{address}': {e}")
    return None, None

def run(dry_run=False):
    print("Step 1: Building database coordinate mapping cache...")
    # Fetch all records in EMPLEADOS_COMPLETOS_SIG with coordinates to use as cache
    populated_records = EmpleadosCompletosSig.objects.exclude(
        latitud__isnull=True
    ).exclude(
        latitud=''
    ).exclude(
        longitud__isnull=True
    ).exclude(
        longitud=''
    )

    known_coords = {}
    for r in populated_records:
        desc = r.descripcion_ubicacion
        if desc:
            desc_clean = clean_address(desc)
            if desc_clean not in known_coords:
                known_coords[desc_clean] = (r.latitud, r.longitud)

    print(f"Loaded {len(known_coords)} unique location mappings from the database.")

    print("\nStep 2: Fetching the dataset to process...")
    query = """
    SELECT e.*
    FROM EMPLEADOS_COMPLETOS_SIG e
    INNER JOIN (
        SELECT m.`Nº Pos Actual`
        FROM MOV_POS m
        INNER JOIN (
            SELECT `Nº Pos Actual`, MAX(id) AS max_id
            FROM MOV_POS
            GROUP BY `Nº Pos Actual`
        ) latest ON m.id = latest.max_id
        WHERE m.`Estado Psn` = 'A'
    ) p ON e.`Posición` = p.`Nº Pos Actual`;
    """

    # We retrieve the raw instances
    records = list(EmpleadosCompletosSig.objects.raw(query))
    total_records = len(records)
    print(f"Found {total_records} records in target dataset.")

    print("\nStep 3: Processing records...")
    updated_count = 0
    skipped_count = 0
    api_calls_count = 0

    # Local cache for this run's geocodes to prevent repeat lookups
    run_cache = {}

    for idx, emp in enumerate(records):
        lat_val = emp.latitud
        lng_val = emp.longitud

        # Check if coordinates are filled
        is_filled = lat_val and lng_val and str(lat_val).strip() != '' and str(lng_val).strip() != ''

        if is_filled:
            skipped_count += 1
            continue

        desc = emp.descripcion_ubicacion
        if not desc:
            print(f"[{idx+1}/{total_records}] Skip: Employee {emp.id_empleado} ({emp.nombres}) has no 'Descripción ubicación'")
            continue

        cleaned = clean_address(desc)

        lat, lng = None, None

        # 1. Try local run cache
        if cleaned in run_cache:
            lat, lng = run_cache[cleaned]
            source = "Run Cache"
        # 2. Try DB known cache
        elif cleaned in known_coords:
            lat, lng = known_coords[cleaned]
            source = "DB Cache"
            # Add to run cache for even faster lookup next time
            run_cache[cleaned] = (lat, lng)
        # 3. Request from Nominatim
        else:
            print(f"Geocoding '{desc}' (cleaned: '{cleaned}') via Nominatim API...")
            lat, lng = geocode_external(cleaned)
            source = "Nominatim API"
            api_calls_count += 1
            # Cache the result
            if lat is not None and lng is not None:
                run_cache[cleaned] = (lat, lng)
                known_coords[cleaned] = (lat, lng)

            # Respect API limits
            time.sleep(1.2)

        if lat is not None and lng is not None:
            # Coordinates must fit within CharField lengths
            # Convert to string and limit length
            new_lat = str(round(float(lat), 6))[:12]
            new_lng = str(round(float(lng), 6))[:13]
            if dry_run:
                print(f"[{idx+1}/{total_records}] Would update: {emp.nombres} -> Lat: {new_lat}, Lng: {new_lng} ({source})")
            else:
                emp.latitud = new_lat
                emp.longitud = new_lng
                emp.save()
                print(f"[{idx+1}/{total_records}] Updated: {emp.nombres} -> Lat: {emp.latitud}, Lng: {emp.longitud} ({source})")
            updated_count += 1
        else:
            print(f"[{idx+1}/{total_records}] Failed to resolve coordinate for '{desc}' (cleaned: '{cleaned}')")

    print("\n" + "="*40)
    print("Execution Summary:" + (" (DRY RUN, no writes)" if dry_run else ""))
    print(f"Total processed: {total_records}")
    print(f"Already filled (skipped): {skipped_count}")
    print(f"Updated with coords: {updated_count}")
    print(f"External API calls made: {api_calls_count}")
    print("="*40)

if __name__ == '__main__':
    run(dry_run="--dry-run" in sys.argv)
