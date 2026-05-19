#!/bin/bash
# Script de test serveur local (H.4.4)

echo "════════════════════════════════════════════════════════════"
echo "  Test serveur MCP local (H.4.4)"
echo "════════════════════════════════════════════════════════════"

# Démarrer serveur en background
echo "▶️  Démarrage serveur..."
python3 server.py > /tmp/mcp_server.log 2>&1 &
SERVER_PID=$!

# Attendre que le serveur soit prêt
echo "   Attente démarrage (5s)..."
sleep 5

# Vérifier que le serveur répond
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Serveur démarré (PID: $SERVER_PID)"
else
    echo "   ❌ Serveur non joignable"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Lancer les tests
echo ""
echo "▶️  Lancement tests..."
python3 tests/test_server_local.py

TEST_EXIT=$?

# Arrêter le serveur
echo ""
echo "▶️  Arrêt serveur..."
kill $SERVER_PID 2>/dev/null
sleep 1

if [ $TEST_EXIT -eq 0 ]; then
    echo "✅ Tests réussis"
else
    echo "❌ Tests échoués"
fi

exit $TEST_EXIT
