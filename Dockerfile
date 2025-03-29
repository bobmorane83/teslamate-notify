# Utilisation d'une image Python légère
FROM python:3.11-slim

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers nécessaires
COPY requirements.txt .
COPY notify.py .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exécution du script au démarrage du conteneur
CMD ["python", "notify.py"]
