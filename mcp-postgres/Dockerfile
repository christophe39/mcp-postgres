FROM python:3.12-slim

WORKDIR /app

# Installation des dépendances système (pour asyncpg et cryptography)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY server.py .

# Exposition du port
EXPOSE 8080

# Healthcheck pour Coolify
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/.well-known/oauth-protected-resource/mcp')" || exit 1

# Lancement du serveur
CMD ["python", "server.py"]
