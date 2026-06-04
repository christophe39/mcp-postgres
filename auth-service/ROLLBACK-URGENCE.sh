#!/bin/bash
# ============================================
# SCRIPT DE ROLLBACK D'URGENCE
# ============================================
# Ce script revient à la version BasicAuth
# en 30 secondes maximum
# ============================================

set -e

echo "🚨 ROLLBACK D'URGENCE EN COURS..."
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VPS_HOST="root@69.62.110.207"
CONTAINER_NAME="l400k4gwo0kgw440w4848gc0-145306625781"

echo -e "${YELLOW}Étape 1/3 : Vérification du conteneur...${NC}"
ssh $VPS_HOST "docker ps | grep $CONTAINER_NAME" || {
  echo -e "${RED}❌ Conteneur non trouvé${NC}"
  exit 1
}
echo -e "${GREEN}✅ Conteneur trouvé${NC}"
echo ""

echo -e "${YELLOW}Étape 2/3 : Checkout de la branche main...${NC}"
git checkout main
echo -e "${GREEN}✅ Branche main activée${NC}"
echo ""

echo -e "${YELLOW}Étape 3/3 : Redéploiement sur Coolify...${NC}"
echo "   Option A : Push sur GitHub (Coolify rebuild auto)"
echo "   Option B : Rebuild manuel dans Coolify"
echo ""
echo -e "${YELLOW}Voulez-vous pusher sur GitHub maintenant ? (y/n)${NC}"
read -r PUSH_NOW

if [ "$PUSH_NOW" = "y" ]; then
  git push origin main
  echo -e "${GREEN}✅ Push effectué, Coolify va rebuilder automatiquement${NC}"
  echo ""
  echo "Surveillez les logs :"
  echo "  ssh $VPS_HOST 'docker logs $CONTAINER_NAME -f'"
else
  echo -e "${YELLOW}ℹ️  Rebuild manuel requis dans Coolify${NC}"
  echo "  1. Aller sur https://coolify.agnisolution.fr"
  echo "  2. Trouver l'app 'excalidraw-auth'"
  echo "  3. Cliquer 'Force Rebuild'"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ ROLLBACK PRÉPARÉ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "⏱️  Temps estimé : 2-3 minutes (rebuild)"
echo ""
echo "📊 Vérification :"
echo "  curl https://exca-auth.agnisolution.fr/health"
echo ""
