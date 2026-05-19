# MCP Server Excalidraw OPEPARTNER - Production
# Phase H.6 - Déploiement remote via Coolify
# Image : python:3.13-slim (Debian, plus robuste qu'Alpine/musl)

FROM python:3.13-slim

# Variables d'environnement Python (production)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Installation dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie code source
COPY . .

# Port MCP (HTTP streamable)
EXPOSE 8000

# Healthcheck Coolify (GET /health)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5).raise_for_status()"

# Commande démarrage serveur
CMD ["python", "server.py"]
