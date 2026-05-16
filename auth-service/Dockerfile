FROM node:18-alpine

WORKDIR /app

# Copier package.json et installer les dépendances
COPY package.json ./
RUN npm install --production

# Copier le code source
COPY server.js ./

# Exposer le port
EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1))"

# Démarrer le serveur
CMD ["node", "server.js"]
