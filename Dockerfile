# Image officielle légère Python
FROM python:3.13-slim

# Empêcher Python d'écrire des fichiers .pyc et activer le buffer direct pour les logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Copie et installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source et des plugins Antigravity
COPY src/ ./src/
COPY .agents/ ./.agents/
COPY reports/ ./reports/

# Exposition du port requis par Cloud Run
EXPOSE 8080

# Lancement du serveur FastAPI
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
