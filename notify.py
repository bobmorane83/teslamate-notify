import time
import psycopg2
import requests
import os
from datetime import datetime
import pytz

# Configuration via variables d'environnement
CAR_ID = os.getenv("CAR_ID", 1)
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "votre_topic")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = os.getenv("DB_PORT", 5432)
DB_NAME = os.getenv("DB_NAME", "teslamate")
DB_USER = os.getenv("DB_USER", "teslamate")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

def query_last_charge():
    """Interroge la base PostgreSQL pour récupérer l'ID et les infos de la dernière charge."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()

        query = f"""
        SELECT id, charge_energy_added, start_battery_level, end_battery_level, duration_min, cost, start_date, end_date
        FROM charging_processes
        WHERE car_id = {CAR_ID}
        AND end_date IS NOT NULL
        ORDER BY end_date DESC
        LIMIT 1;
        """

        cur.execute(query)
        row = cur.fetchone()
        conn.close()

        if row:
            paris_tz = pytz.timezone("Europe/Paris")
            start = row[6].astimezone(paris_tz) if row[6] else None
            end = row[7].astimezone(paris_tz) if row[7] else None

            return {
                "id": row[0],
                "energy_added": row[1],
                "start_battery": row[2],
                "end_battery": row[3],
                "duration": row[4],
                "cost": row[5],
                "start": start.strftime("%Y-%m-%d %H:%M:%S %Z") if start else "N/A",
                "end": end.strftime("%Y-%m-%d %H:%M:%S %Z") if end else "N/A"
            }
        else:
            return None
    except Exception as e:
        print(f"Erreur PostgreSQL: {e}")
        return None

def query_last_drive():
    """Interroge la base PostgreSQL pour récupérer l'ID et les infos du dernier trajet."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()

        query = f"""
          SELECT
            drives.id as drive_id,
            start_date,
            end_date,
            duration_min,
            distance,
            start_position.battery_level as start_battery_level,
            end_position.battery_level as end_battery_level,
            COALESCE(start_geofence.name, CONCAT_WS(', ', COALESCE(start_address.name, nullif(CONCAT_WS(' ', start_address.road, start_address.house_number), '')), start_address.city)) AS start_address,
            COALESCE(end_geofence.name, CONCAT_WS(', ', COALESCE(end_address.name, nullif(CONCAT_WS(' ', end_address.road, end_address.house_number), '')), end_address.city)) AS end_address,
            case when (start_position.battery_level != start_position.usable_battery_level OR end_position.battery_level != end_position.usable_battery_level) = true then true else false end  as reduced_range,
                duration_min > 1 AND distance > 1 AND (
                start_position.usable_battery_level IS NULL OR end_position.usable_battery_level IS NULL	OR
                (end_position.battery_level - end_position.usable_battery_level) = 0
            ) as is_sufficiently_precise,
          NULLIF(GREATEST(start_rated_range_km - end_rated_range_km, 0), 0) * car.efficiency / convert_km(distance::numeric, 'km') * 1000 as "consumption_Wh_km"
          FROM drives
          LEFT JOIN addresses start_address ON start_address_id = start_address.id
          LEFT JOIN addresses end_address ON end_address_id = end_address.id
          LEFT JOIN positions start_position ON start_position_id = start_position.id
          LEFT JOIN positions end_position ON end_position_id = end_position.id
          LEFT JOIN geofences start_geofence ON start_geofence_id = start_geofence.id
          LEFT JOIN geofences end_geofence ON end_geofence_id = end_geofence.id
          LEFT JOIN cars car ON car.id = drives.car_id
          WHERE drives.car_id = 1
          AND end_date IS NOT NULL
          ORDER BY end_date DESC
          LIMIT 1;
        """

        cur.execute(query)
        row = cur.fetchone()
        conn.close()

        if row:
            paris_tz = pytz.timezone("Europe/Paris")
            start = row[1].astimezone(paris_tz) if row[1] else None
            end = row[2].astimezone(paris_tz) if row[2] else None

            return {
                "id": row[0],
                "start": start.strftime("%Y-%m-%d %H:%M:%S %Z") if start else "N/A",
                "end": end.strftime("%Y-%m-%d %H:%M:%S %Z") if end else "N/A",
                "duration": row[3],
                "distance": row[4],
                "start_battery": row[5],
                "end_battery": row[6],
                "start_addr": row[7],
                "end_addr": row[8],
                "conso": row[11]
            }
        else:
            return None
    except Exception as e:
        print(f"Erreur PostgreSQL: {e}")
        return None

def send_ntfy_notification(message, title):
    """Envoie une notification avec un message et un titre."""
    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), headers={"Title": title})
        print(f"Notification envoyée: {title}")
    except Exception as e:
        print(f"Erreur d'envoi de notification: {e}")

def main():
    print("Démarrage du script de surveillance des charges et trajets...")
    last_charge_id = None
    last_drive_id = None

    while True:
        charge_data = query_last_charge()
#        print(charge_data)
        if charge_data and charge_data['id'] != last_charge_id and charge_data['cost'] != None:
            h, m = divmod(charge_data['duration'], 60)
            message = (
                f"Énergie ajoutée: {charge_data['energy_added']} kWh\n"
                f"De {charge_data['start']} à {charge_data['end']}\n"
                f"Durée: {h}h{m}\n"
                f"Batterie: {charge_data['start_battery']}% -> {charge_data['end_battery']}%\n"
                f"Coût: {charge_data['cost']} €"
            )
            send_ntfy_notification(message, "Charge finie")
            last_charge_id = charge_data['id']

        drive_data = query_last_drive()
#        print(drive_data)
        if drive_data and drive_data['id'] != last_drive_id and drive_data['distance'] != None:
            h, m = divmod(drive_data['duration'], 60)
            message = (
                f"De: {drive_data['start_addr']}\n"
                f"a: {drive_data['end_addr']}\n"
                f"Distance: {round(drive_data['distance'],1)} km\n"
                f"Durée: {h}h{m}\n"
                f"Conso: {round(drive_data['conso'],1)} Wh/km\n"
                f"Batterie: {drive_data['start_battery']}% -> {drive_data['end_battery']}%\n"
#                f"Vitesse moyenne: {drive_data['avg_speed']:.2f} km/h"
            )
            send_ntfy_notification(message, "Fin de trajet")
            last_drive_id = drive_data['id']

        time.sleep(60)  # Attente d'une minute avant la prochaine vérification

if __name__ == "__main__":
    main()
