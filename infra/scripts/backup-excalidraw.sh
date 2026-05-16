#!/bin/bash
# ============================================
# Script de backup automatique Excalidraw
# Base : excalidraw_storage
# Fréquence : quotidienne (cron 2h du matin)
# Auteur : Claude Code + Christophe Martin
# Date : 16 mai 2026
# ============================================

set -euo pipefail

# Configuration
BACKUP_DIR="/backup/excalidraw"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER="pk4s888o4wkc8ogokg0sg840"
DB_USER="excalidraw_backend"
DB_NAME="excalidraw_storage"
RETENTION_DAYS=7

# Couleurs pour logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de log
log() {
  echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
  echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERREUR:${NC} $1" >&2
}

warning() {
  echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ATTENTION:${NC} $1"
}

# Vérifier que le container existe et est running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  error "Container ${CONTAINER} non trouvé ou non démarré"
  exit 1
fi

# Créer le répertoire de backup si nécessaire
mkdir -p "$BACKUP_DIR"

# Nom du fichier de backup
BACKUP_FILE="$BACKUP_DIR/excalidraw_${DATE}.sql.gz"
LOG_FILE="$BACKUP_DIR/backup.log"

log "🚀 Démarrage backup de ${DB_NAME}..."

# Dump de la base avec compression gzip
if docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
  # Taille du fichier
  SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

  log "✅ Backup réussi : ${BACKUP_FILE} (${SIZE})"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS - ${BACKUP_FILE} (${SIZE})" >> "$LOG_FILE"

  # Vérifier que le fichier n'est pas vide
  if [ ! -s "$BACKUP_FILE" ]; then
    error "Le fichier de backup est vide !"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Backup file is empty" >> "$LOG_FILE"
    exit 1
  fi

  # Test d'intégrité du gzip
  if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    error "Le fichier de backup est corrompu !"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Backup file is corrupted" >> "$LOG_FILE"
    exit 1
  fi

  log "✅ Vérification intégrité OK"

else
  error "Échec du backup"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - FAILED - Backup failed" >> "$LOG_FILE"
  exit 1
fi

# Rotation des backups (garder les N derniers jours)
log "🔄 Rotation des backups (conservation : ${RETENTION_DAYS} jours)..."

DELETED_COUNT=0
while IFS= read -r old_backup; do
  rm -f "$old_backup"
  DELETED_COUNT=$((DELETED_COUNT + 1))
  log "🗑️  Supprimé : $(basename "$old_backup")"
done < <(find "$BACKUP_DIR" -name "excalidraw_*.sql.gz" -mtime +${RETENTION_DAYS} -type f)

if [ $DELETED_COUNT -gt 0 ]; then
  log "✅ ${DELETED_COUNT} ancien(s) backup(s) supprimé(s)"
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ROTATION - Deleted ${DELETED_COUNT} old backup(s)" >> "$LOG_FILE"
else
  log "ℹ️  Aucun ancien backup à supprimer"
fi

# Statistiques
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "excalidraw_*.sql.gz" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log "📊 Statistiques : ${TOTAL_BACKUPS} backup(s) conservé(s), taille totale : ${TOTAL_SIZE}"

# Lister les 5 derniers backups
log "📁 5 derniers backups :"
find "$BACKUP_DIR" -name "excalidraw_*.sql.gz" -type f -printf '%T@ %p\n' | \
  sort -rn | \
  head -5 | \
  while read -r timestamp file; do
    size=$(du -h "$file" | cut -f1)
    date=$(date -d "@${timestamp%%.*}" '+%Y-%m-%d %H:%M:%S')
    echo "   - $(basename "$file") (${size}) - ${date}"
  done

log "✅ Backup terminé avec succès"

exit 0
