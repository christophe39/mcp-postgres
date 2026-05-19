#!/bin/bash
# Script de test client MCP réel (H.4.4)

echo "════════════════════════════════════════════════════════════"
echo "  Test client MCP réel via HTTP/SSE (H.4.4)"
echo "════════════════════════════════════════════════════════════"

# Démarrer serveur en background
echo "▶️  Démarrage serveur MCP..."
source .venv/bin/activate
python3 server.py > /tmp/mcp_server_real.log 2>&1 &
SERVER_PID=$!

# Attendre que le serveur soit prêt
echo "   Attente démarrage (5s)..."
sleep 5

# Vérifier que le serveur répond
if curl -s http://127.0.0.1:8000/sse > /dev/null 2>&1; then
    echo "   ✅ Serveur MCP démarré (PID: $SERVER_PID)"
else
    echo "   ❌ Serveur MCP non joignable"
    kill $SERVER_PID 2>/dev/null
    cat /tmp/mcp_server_real.log
    exit 1
fi

# Lancer les tests avec client MCP réel
echo ""
echo "▶️  Lancement tests client MCP..."
python3 tests/test_mcp_client.py

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
    echo "--- Logs serveur ---"
    cat /tmp/mcp_server_real.log
fi

exit $TEST_EXIT
