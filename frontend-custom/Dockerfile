# =====================================================
# Dockerfile - Excalidraw Frontend Custom OPEPARTNER
# =====================================================
# Build Excalidraw avec nos propres variables d'environnement
# pour pointer vers notre backend self-hosted
# =====================================================

# Stage 1 : Build
FROM node:20-alpine AS builder

# Installation des dépendances système
RUN apk add --no-cache git

# Clone du repo Excalidraw (version stable)
WORKDIR /app
RUN git clone --depth 1 --branch master https://github.com/excalidraw/excalidraw.git .

# Installation des dépendances Node.js
RUN yarn install --frozen-lockfile

# Variables d'environnement pour le build (AVANT le build, pas ARG)
ENV VITE_APP_BACKEND_V2_GET_URL=https://exca-api.agnisolution.fr/api/v2/
ENV VITE_APP_BACKEND_V2_POST_URL=https://exca-api.agnisolution.fr/api/v2/post/
ENV VITE_APP_DISABLE_TRACKING=true

# Build de l'application
RUN yarn build:app:docker

# Stage 2 : Production
FROM nginx:alpine

# Copie des fichiers buildés
COPY --from=builder /app/excalidraw-app/build /usr/share/nginx/html

# Configuration nginx pour SPA
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
