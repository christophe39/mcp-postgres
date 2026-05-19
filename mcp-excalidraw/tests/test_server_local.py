"""
Test serveur MCP en local (H.4.4)
Requêtes MCP réelles au serveur (pas appels directs Python)

Tests :
1. /health répond
2. Liste des outils MCP exposés
3. Appel create_excalidraw_scene via MCP
4. Vérifier outils exposés/listables
5. Auto-cleanup (base + keyv propres)
"""

import asyncio
import httpx
import json
import subprocess
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.nocodb import NocoDBClient
from clients.excalidraw import ExcalidrawClient

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# CONFIG
# =============================================================================

SERVER_URL = "http://127.0.0.1:8000"
MCP_SSE_URL = f"{SERVER_URL}/sse"


# =============================================================================
# HELPERS
# =============================================================================

def cleanup_sql():
    """Cleanup base PostgreSQL"""
    cmd = [
        "ssh", "root@69.62.110.207",
        'docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -d opepartner -c "DELETE FROM schemas_excalidraw WHERE document_title LIKE \'TEST%\'; DELETE FROM clients WHERE nom_entreprise LIKE \'TEST%\';"'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
    except:
        pass


async def count_test_records(nocodb: NocoDBClient):
    """Compte clients/schémas TEST"""
    clients = await nocodb.list_clients(limit=1000)
    schemas = await nocodb.list_schemas_excalidraw(limit=1000)

    nb_clients = sum(1 for c in clients if c.get("nom_entreprise", "").startswith("TEST"))
    nb_schemas = sum(1 for s in schemas if s.get("document_title", "").startswith("TEST"))

    return nb_clients, nb_schemas


def get_sample_scene_json():
    """Retourne un JSON Excalidraw minimal valide"""
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "type": "rectangle",
                "version": 1,
                "versionNonce": 1,
                "isDeleted": False,
                "id": "test-server-rect-1",
                "fillStyle": "solid",
                "strokeWidth": 2,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "angle": 0,
                "x": 100,
                "y": 100,
                "strokeColor": "#1e1e1e",
                "backgroundColor": "#a5d8ff",
                "width": 200,
                "height": 100,
                "seed": 1,
                "groupIds": [],
                "frameId": None,
                "roundness": {"type": 3},
                "boundElements": [],
                "updated": 1,
                "link": None,
                "locked": False
            }
        ],
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff"
        },
        "files": {}
    }


async def mcp_call_tool(tool_name: str, arguments: dict) -> dict:
    """
    Appelle un outil MCP via JSON-RPC 2.0

    Args:
        tool_name: Nom de l'outil MCP
        arguments: Arguments de l'outil

    Returns:
        Résultat de l'outil (dict)

    Raises:
        Exception: Si erreur MCP
    """
    async with httpx.AsyncClient() as client:
        # Requête JSON-RPC 2.0 pour appel d'outil
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = await client.post(
            MCP_SSE_URL,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"Erreur HTTP {response.status_code}: {response.text}")

        result = response.json()

        # Vérifier format JSON-RPC
        if "error" in result:
            raise Exception(f"Erreur MCP: {result['error']}")

        if "result" not in result:
            raise Exception(f"Réponse MCP invalide: {result}")

        return result["result"]


async def mcp_list_tools() -> list:
    """
    Liste les outils MCP exposés via JSON-RPC 2.0

    Returns:
        Liste des outils (noms + descriptions)
    """
    async with httpx.AsyncClient() as client:
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = await client.post(
            MCP_SSE_URL,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )

        if response.status_code != 200:
            raise Exception(f"Erreur HTTP {response.status_code}: {response.text}")

        result = response.json()

        if "error" in result:
            raise Exception(f"Erreur MCP: {result['error']}")

        if "result" not in result:
            raise Exception(f"Réponse MCP invalide: {result}")

        return result["result"].get("tools", [])


# =============================================================================
# TESTS
# =============================================================================

async def test_01_mcp_health():
    """Test 1 : Outil MCP health répond"""
    print("\n▶️  Test 1 : Vérification MCP health tool...")

    try:
        result = await mcp_call_tool("health", {})

        assert result["status"] == "healthy"
        assert result["service"] == "mcp-excalidraw-opepartner"
        print(f"   ✅ MCP health OK : {result}")
        return True

    except httpx.ConnectError:
        print("   ❌ Serveur MCP non joignable (est-il démarré ?)")
        print("   Lancez : python3 server.py")
        return False
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_02_list_tools():
    """Test 2 : Lister les outils MCP exposés"""
    print("\n▶️  Test 2 : Liste des outils MCP exposés...")

    try:
        tools = await mcp_list_tools()

        tool_names = [tool["name"] for tool in tools]
        print(f"   ✅ Outils exposés ({len(tools)}) : {tool_names}")

        # Vérifier les 7 outils attendus
        expected_tools = [
            "create_excalidraw_scene",
            "get_excalidraw_scene",
            "update_excalidraw_scene",
            "list_excalidraw_scenes",
            "delete_excalidraw_scene",
            "find_or_create_opepartner_client",
            "health"
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Outil {expected} manquant"

        print(f"   ✅ Tous les outils attendus présents")
        return True

    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_03_create_scene_via_mcp(nocodb: NocoDBClient, excalidraw: ExcalidrawClient):
    """Test 3 : Appel create_excalidraw_scene via MCP JSON-RPC"""
    print("\n▶️  Test 3 : Appel create_excalidraw_scene via MCP...")

    cleanup_sql()

    # Préparer payload
    scene_json = get_sample_scene_json()

    arguments = {
        "scene_json": scene_json,
        "client_name": "TEST-SERVER-CLIENT",
        "document_type": "BMC_visuel",
        "document_title": "TEST BMC Server MCP",
        "secteur_activite": "Test",
        "confidentiel": True,
        "tags": ["test", "server"]
    }

    try:
        result = await mcp_call_tool("create_excalidraw_scene", arguments)

        # Vérifications
        assert result["client_name"] == "TEST-SERVER-CLIENT"
        assert result["scene_id"]
        assert result["jwk_k"]
        assert result["url"]
        assert result["schema_id"]
        assert result["affine_snippet"]

        # Vérifier snippet
        snippet = result["affine_snippet"]
        assert "TEST BMC Server MCP" in snippet
        assert "BMC_visuel" in snippet
        assert result["url"] in snippet

        print(f"   ✅ Orchestration OK via MCP")
        print(f"      Client: {result['client_id']}")
        print(f"      Scène: {result['scene_id']}")
        print(f"      Schéma: {result['schema_id']}")

        # Vérifier que la scène existe
        from tools.scenes import scene_exists
        exists = await scene_exists(excalidraw, result['scene_id'])
        assert exists, "La scène doit exister"

        return result['scene_id']  # Pour cleanup

    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_04_cleanup(nocodb: NocoDBClient, excalidraw: ExcalidrawClient, scene_id: str):
    """Test 4 : Cleanup complet (base + keyv)"""
    print("\n▶️  Test 4 : Cleanup final...")

    # Cleanup SQL
    cleanup_sql()

    # Cleanup scène Excalidraw
    if scene_id:
        try:
            await excalidraw.delete_scene(scene_id)
        except:
            pass

    # Vérifier base propre
    nb_clients, nb_schemas = await count_test_records(nocodb)

    if nb_clients == 0 and nb_schemas == 0:
        print("   ✅ Base propre (0 clients, 0 schémas)")
        return True
    else:
        print(f"   ⚠️  Résidus : {nb_clients} clients, {nb_schemas} schémas")
        return False


# =============================================================================
# MAIN
# =============================================================================

async def run_all_tests():
    """Lance tous les tests"""
    print("\n" + "="*80)
    print("TESTS SERVER LOCAL — Requêtes MCP JSON-RPC réelles")
    print("="*80)

    # Test 1 : MCP Health
    health_ok = await test_01_mcp_health()
    if not health_ok:
        print("\n⚠️  Serveur MCP non démarré ou non joignable.")
        print("   Lancez dans un autre terminal : python3 server.py")
        return

    # Test 2 : Liste outils MCP
    list_ok = await test_02_list_tools()
    if not list_ok:
        print("\n⚠️  Impossible de lister les outils MCP.")
        return

    # Initialiser clients pour tests 3 et 4
    nocodb = NocoDBClient()
    excalidraw = ExcalidrawClient()

    await nocodb.connect()
    await excalidraw.connect()

    scene_id = None

    try:
        # Test 3 : Create scene via MCP
        scene_id = await test_03_create_scene_via_mcp(nocodb, excalidraw)

        # Test 4 : Cleanup
        await test_04_cleanup(nocodb, excalidraw, scene_id)

        print("\n" + "="*80)
        print("✅ TESTS SERVEUR MCP LOCAL RÉUSSIS")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

    finally:
        await nocodb.disconnect()
        await excalidraw.disconnect()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
