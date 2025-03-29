# teslamate-notify

Permet de notifier les fins de charge sur le service gratuit ntfy (en attendant d'ajouter d'autres notifs).

A chaque fin de charge un message "Complete" est envoyé sur le topic MQTT teslamate/cars/{CAR_ID}/charging_state

Lors de la réception de ce message, on attend une minutes pour laisser le temps à un éventuel calcul du cout automatique (ie. teslamateagile) et on récupère les dernières données de charge dans la base.

Un message est envoyé sur votre topic ntfy (a renseigner) avec ces données.

Bien mettre à jour vos variables de base de données, topic ntfy et brocker MQTT.

Enjoy,