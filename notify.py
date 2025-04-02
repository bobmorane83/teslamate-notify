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
                "start": start.strftime("%Y-%m-%d %H:%M") if start else "N/A",
                "end": end.strftime("%Y-%m-%d %H:%M") if end else "N/A"
            }
        else:
            return None
    except Exception as e:
        print(f"Erreur PostgreSQL: {e}")
        return None

def send_ntfy_notification(charge_data):
    """Envoie une notification avec les données de charge."""
    if not charge_data:
        print("Aucune donnée de charge trouvée.")
        return

    h, m = divmod(charge_data['duration'], 60)

    message = (
        f"Énergie ajoutée: {charge_data['energy_added']} kWh\n"
        f"De {charge_data['start']} à {charge_data['end']}\n"
        f"Durée: {h}h{m}\n"
        f"Batterie : {charge_data['start_battery']}% -> {charge_data['end_battery']}%\n"
        f"Coût: {charge_data['cost']} €"
    )

    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), headers={"Title": "Charge terminee"})
        print("Notification envoyée via ntfy")
    except Exception as e:
        print(f"Erreur d'envoi de notification: {e}")

def main():
    print("Démarrage du script de surveillance des charges...")
    last_charge_id = None

    while True:
        charge_data = query_last_charge()
        if charge_data and charge_data['id'] != last_charge_id:
            send_ntfy_notification(charge_data)
            last_charge_id = charge_data['id']

        time.sleep(60)  # Attente d'une minute avant la prochaine vérification

if __name__ == "__main__":
    main()
