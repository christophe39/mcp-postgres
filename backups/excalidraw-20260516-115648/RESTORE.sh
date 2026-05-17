#!/bin/bash
# Script de restauration du service Excalidraw
# Créé le 2026-05-16 11:56:48

set -e

BACKUP_DIR=/root/backups/excalidraw-20260516-115648
SERVICE_DIR=/data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0

echo "=== RESTAURATION SERVICE EXCALIDRAW ==="
echo "Backup depuis: $BACKUP_DIR"
echo ""

# 1. Arrêter les containers actuels
echo "1. Arrêt des containers..."
cd $SERVICE_DIR
docker-compose stop proxy backend 2>/dev/null || true

# 2. Restaurer le docker-compose.yml
echo "2. Restauration docker-compose.yml..."
cp $BACKUP_DIR/docker-compose.yml $SERVICE_DIR/docker-compose.yml

# 3. Restaurer l'ancienne image Docker du proxy
echo "3. Restauration de l'image proxy..."
gunzip < $BACKUP_DIR/excalidraw-proxy-old.tar.gz | docker load
docker tag 77715037f1f3 excalidraw-proxy:latest

# 4. Restaurer la base PostgreSQL
echo "4. Restauration base de données PostgreSQL..."
echo "ATTENTION: Cela va ÉCRASER la base excalidraw_storage actuelle !"
read -p "Confirmer la restauration de la base ? (oui/non) " -r
if [[ $REPLY =~ ^oui$ ]]; then
    gunzip < $BACKUP_DIR/excalidraw_storage.sql.gz | docker exec -i pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend excalidraw_storage
    echo "Base restaurée."
else
    echo "Restauration de la base IGNORÉE."
fi

# 5. Recréer les containers
echo "5. Recréation des containers..."
cd $SERVICE_DIR
docker-compose up -d

echo ""
echo "=== RESTAURATION TERMINÉE ==="
echo "Vérifiez l'état avec: docker ps --filter 'name=excalidraw'"
