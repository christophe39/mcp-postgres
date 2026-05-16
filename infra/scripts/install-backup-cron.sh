#!/bin/bash
# ============================================
# Script d'installation du cron de backup
# À exécuter UNE SEULE FOIS sur le VPS
# ============================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
  echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warning() {
  echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ATTENTION:${NC} $1"
}

# Copier le script de backup dans /root/
BACKUP_SCRIPT="/root/backup-excalidraw.sh"

if [ -f "$BACKUP_SCRIPT" ]; then
  warning "Le script $BACKUP_SCRIPT existe déjà"
  read -p "Écraser ? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Installation annulée"
    exit 0
  fi
fi

log "📋 Copie du script de backup vers ${BACKUP_SCRIPT}..."
cp "$(dirname "$0")/backup-excalidraw.sh" "$BACKUP_SCRIPT"
chmod +x "$BACKUP_SCRIPT"

log "✅ Script copié et rendu exécutable"

# Tester le script
log "🧪 Test du script de backup..."
if "$BACKUP_SCRIPT"; then
  log "✅ Test réussi"
else
  echo "❌ Le test a échoué, vérifier les logs ci-dessus"
  exit 1
fi

# Ajouter le cron job
CRON_LINE="0 2 * * * /root/backup-excalidraw.sh >> /var/log/backup-excalidraw.log 2>&1"

log "📅 Configuration du cron job (tous les jours à 2h du matin)..."

# Vérifier si le cron existe déjà
if crontab -l 2>/dev/null | grep -q "backup-excalidraw.sh"; then
  warning "Le cron job existe déjà dans la crontab"
  log "📋 Crontab actuelle :"
  crontab -l | grep "backup-excalidraw.sh"
else
  # Ajouter le cron
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
  log "✅ Cron job ajouté"
fi

# Créer le fichier de log
touch /var/log/backup-excalidraw.log
chmod 644 /var/log/backup-excalidraw.log

log "✅ Installation terminée"
log ""
log "📋 Informations :"
log "   - Script : ${BACKUP_SCRIPT}"
log "   - Cron : Tous les jours à 2h00"
log "   - Log cron : /var/log/backup-excalidraw.log"
log "   - Backups : /backup/excalidraw/"
log "   - Rétention : 7 jours"
log ""
log "🔍 Pour vérifier :"
log "   crontab -l | grep backup-excalidraw"
log "   ls -lh /backup/excalidraw/"
log "   tail -f /var/log/backup-excalidraw.log"
log ""
log "🧪 Pour tester manuellement :"
log "   /root/backup-excalidraw.sh"

exit 0
