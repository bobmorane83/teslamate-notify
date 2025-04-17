# teslamate-notify

Permet de notifier les fins de charges et trajets sur le service gratuit ntfy.

On pull toutes les minutes sur le dernier ID de la charge/trajet et on récupère les dernières données dans la base.

Un (ou plusieurs) message est envoyé sur votre topic ntfy (a renseigner) avec ces données.

Bien mettre à jour vos variables de base de données, topic ntfy et brocker MQTT.

Enjoy,