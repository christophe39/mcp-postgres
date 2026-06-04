#!/bin/bash
# ============================================
# SCRIPT DE TEST DU SERVICE D'AUTHENTIFICATION
# ============================================
# Teste tous les endpoints et scénarios
# ============================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:3000}"
TEST_EMAIL="cmartin@agniconsult.fr"
TEST_PASSWORD="${2:-}" # Passer le mot de passe en argument

if [ -z "$TEST_PASSWORD" ]; then
  echo -e "${RED}❌ Usage: $0 [BASE_URL] [PASSWORD]${NC}"
  echo "   Exemple: $0 http://localhost:3000 MonP@ssw0rd"
  exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🧪 TESTS DU SERVICE D'AUTHENTIFICATION${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Base URL: $BASE_URL"
echo ""

TEMP_DIR=$(mktemp -d)
COOKIES_FILE="$TEMP_DIR/cookies.txt"

cleanup() {
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# ============================================
# Test 1 : Healthcheck
# ============================================
echo -e "${YELLOW}Test 1/7 : Healthcheck...${NC}"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
  echo -e "${GREEN}✅ Healthcheck OK${NC}"
else
  echo -e "${RED}❌ Healthcheck échoué${NC}"
  echo "$HEALTH_RESPONSE"
  exit 1
fi
echo ""

# ============================================
# Test 2 : Page de login accessible
# ============================================
echo -e "${YELLOW}Test 2/7 : Page de login accessible...${NC}"
LOGIN_PAGE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/login")
if [ "$LOGIN_PAGE" = "200" ]; then
  echo -e "${GREEN}✅ Page de login accessible${NC}"
else
  echo -e "${RED}❌ Page de login inaccessible (HTTP $LOGIN_PAGE)${NC}"
  exit 1
fi
echo ""

# ============================================
# Test 3 : Auth sans session (doit rediriger)
# ============================================
echo -e "${YELLOW}Test 3/7 : Auth sans session (doit rediriger)...${NC}"
AUTH_NO_SESSION=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/auth")
if [ "$AUTH_NO_SESSION" = "302" ]; then
  echo -e "${GREEN}✅ Redirection vers login OK${NC}"
else
  echo -e "${RED}❌ Auth sans session incorrecte (HTTP $AUTH_NO_SESSION, attendu 302)${NC}"
  exit 1
fi
echo ""

# ============================================
# Test 4 : Login avec mauvais mot de passe
# ============================================
echo -e "${YELLOW}Test 4/7 : Login avec mauvais mot de passe...${NC}"
BAD_LOGIN=$(curl -s -o /dev/null -w "%{http_code}" -L -c "$COOKIES_FILE" \
  -d "email=$TEST_EMAIL&password=MAUVAIS_PASSWORD" \
  "$BASE_URL/login")

if [ "$BAD_LOGIN" = "200" ] && curl -s -b "$COOKIES_FILE" "$BASE_URL/login" | grep -q "Email ou mot de passe incorrect"; then
  echo -e "${GREEN}✅ Rejet du mauvais mot de passe OK${NC}"
else
  echo -e "${RED}❌ Login avec mauvais password échoué${NC}"
  exit 1
fi
echo ""

# ============================================
# Test 5 : Login avec bons identifiants
# ============================================
echo -e "${YELLOW}Test 5/7 : Login avec bons identifiants...${NC}"
rm -f "$COOKIES_FILE" # Reset cookies
GOOD_LOGIN=$(curl -s -o /dev/null -w "%{http_code}" -L -c "$COOKIES_FILE" \
  -d "email=$TEST_EMAIL&password=$TEST_PASSWORD" \
  "$BASE_URL/login")

# Vérifier que le cookie de session a été créé
if [ -f "$COOKIES_FILE" ] && grep -q "excalidraw.sid" "$COOKIES_FILE"; then
  echo -e "${GREEN}✅ Login réussi, cookie de session créé${NC}"
else
  echo -e "${RED}❌ Login échoué, pas de cookie de session${NC}"
  cat "$COOKIES_FILE" 2>/dev/null || echo "(pas de fichier cookies)"
  exit 1
fi
echo ""

# ============================================
# Test 6 : Auth avec session valide
# ============================================
echo -e "${YELLOW}Test 6/7 : Auth avec session valide...${NC}"
AUTH_WITH_SESSION=$(curl -s -w "%{http_code}" -b "$COOKIES_FILE" "$BASE_URL/auth")
HTTP_CODE=$(echo "$AUTH_WITH_SESSION" | tail -n 1)
RESPONSE_BODY=$(echo "$AUTH_WITH_SESSION" | head -n -1)

if [ "$HTTP_CODE" = "200" ] && [ "$RESPONSE_BODY" = "OK" ]; then
  echo -e "${GREEN}✅ Auth avec session valide OK${NC}"
else
  echo -e "${RED}❌ Auth avec session échouée (HTTP $HTTP_CODE)${NC}"
  echo "Response: $RESPONSE_BODY"
  exit 1
fi
echo ""

# ============================================
# Test 7 : Rate limiting (3 tentatives)
# ============================================
echo -e "${YELLOW}Test 7/7 : Rate limiting (3 tentatives échouées)...${NC}"
rm -f "$COOKIES_FILE"

for i in 1 2 3; do
  curl -s -o /dev/null -L \
    -d "email=test@example.com&password=wrong" \
    "$BASE_URL/login"
  echo "   Tentative $i/3..."
  sleep 0.5
done

# La 4ème tentative doit être bloquée
BLOCKED_RESPONSE=$(curl -s -L -d "email=test@example.com&password=wrong" "$BASE_URL/login")
if echo "$BLOCKED_RESPONSE" | grep -q "Trop de tentatives"; then
  echo -e "${GREEN}✅ Rate limiting fonctionne (bloqué après 3 tentatives)${NC}"
else
  echo -e "${RED}❌ Rate limiting ne fonctionne pas${NC}"
  exit 1
fi
echo ""

# ============================================
# RÉSUMÉ
# ============================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ TOUS LES TESTS RÉUSSIS${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Le service d'authentification fonctionne correctement :"
echo "  ✅ Healthcheck opérationnel"
echo "  ✅ Page de login accessible"
echo "  ✅ Redirection sans session"
echo "  ✅ Rejet des mauvais identifiants"
echo "  ✅ Authentification réussie"
echo "  ✅ Session persistante"
echo "  ✅ Rate limiting actif (3 tentatives)"
echo ""
echo -e "${BLUE}🚀 Prêt pour le déploiement !${NC}"
echo ""
