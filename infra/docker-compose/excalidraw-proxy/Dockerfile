# Proxy adaptateur Excalidraw
# Traduit les URLs entre le frontend et le backend
FROM nginx:alpine

# Copier la configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -q --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
