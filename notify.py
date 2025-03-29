import time
import psycopg2
import paho.mqtt.client as mqtt
import requests

# Configuration
MQTT_BROKER = "mosquitto"  # Adresse du broker MQTT
MQTT_PORT = 1883             # Port MQTT
CAR_ID = 1                   # ID de la voiture Teslamate
NTFY_TOPIC = "votre_topic"  # Topic ntfy
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Configuration de la base de données Teslamate
DB_HOST = "database"
DB_PORT = "5432"
DB_NAME = "teslamate"
DB_USER = "teslamate"
DB_PASSWORD = "password"

def query_last_charge():
    """Interroge la base PostgreSQL pour récupérer les infos de la dernière charge."""
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
            charge_energy_added, start_battery_level, end_battery_level, duration_min, cost, start_date, end_date
        FROM charging_processes
        WHERE car_id = {CAR_ID}
        ORDER BY end_date DESC
        LIMIT 1;
        """

        cur.execute(query)
        row = cur.fetchone()
        conn.close()

        if row:
            return {
                "energy_added": row[0],
                "start_battery": row[1],
                "end_battery": row[2],
                "duration": row[3],
                "cost": row[4],
                "start" : row[5],
                "end" : row[6]
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
        f"Charge terminée\n"
        f"Énergie ajoutée: {charge_data['energy_added']} kWh\n"
        f"De {charge_data['start']} à {charge_data['end']}\n"
        f"Durée: {h}h{m}\n"
        f"{charge_data['start_battery']}% -> {charge_data['end_battery']}%\n"
        f"Coût: {charge_data['cost']} €"
    )

    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), headers={"Title": "Tesla Charge Complete"})
        print("Notification envoyée via ntfy")
    except Exception as e:
        print(f"Erreur d'envoi de notification: {e}")

def on_message(client, userdata, msg):
    """Callback lors de la réception d'un message MQTT."""
    topic = msg.topic
    payload = msg.payload.decode("utf-8")

    if topic == f"teslamate/cars/{CAR_ID}/charging_state" and payload == "Complete":
        print("Charge terminée, attente de 60 secondes avant interrogation de la DB...")
        time.sleep(60)

        charge_data = query_last_charge()
        send_ntfy_notification(charge_data)

def main():
    print("Start Notify ...")
    """Configure et démarre le client MQTT."""
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Écoute uniquement le changement d'état de charge
    topic = f"teslamate/cars/{CAR_ID}/charging_state"
    client.subscribe(topic)

    print(f"Écoute du topic MQTT: {topic}")
    client.loop_forever()

if __name__ == "__main__":
    main()
