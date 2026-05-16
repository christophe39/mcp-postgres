# Proxy adaptateur Excalidraw
# Traduit les URLs entre le frontend et le backend
FROM nginx:alpine

# Copier la configuration
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
