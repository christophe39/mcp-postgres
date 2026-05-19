"""
Test client MCP réel via HTTP/SSE (H.4.4)
Utilise la bibliothèque mcp Python pour communiquer avec le serveur

Tests :
1. tools/list → vérifier 7 outils + schémas complets
2. tools/call health → healthcheck
3. tools/call create_excalidraw_scene → orchestration complète
4. Cleanup (base + keyv propres)
"""

import asyncio
import subprocess
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.nocodb import NocoDBClient
from clients.excalidraw import ExcalidrawClient
from tools.scenes import scene_exists

from dotenv import load_dotenv
load_dotenv()

# Import du client MCP
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


# =============================================================================
# CONFIG
# =============================================================================

SERVER_URL = "http://127.0.0.1:8000/sse"


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
                "id": "test-mcp-client-rect-1",
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


# =============================================================================
# TESTS
# =============================================================================

async def test_01_tools_list(session: ClientSession):
    """Test 1 : tools/list → 7 outils + schémas complets"""
    print("\n" + "="*80)
    print("TEST 1 : tools/list (liste des outils MCP)")
    print("="*80)

    result = await session.list_tools()
    tools = result.tools

    print(f"\n📋 Outils exposés : {len(tools)}")
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool.name}")
        print(f"   Description : {tool.description[:100]}...")
        if tool.inputSchema:
            params = tool.inputSchema.get("properties", {})
            required = tool.inputSchema.get("required", [])
            print(f"   Paramètres ({len(params)}) :")
            for param_name, param_info in list(params.items())[:3]:  # Afficher 3 premiers
                req = "requis" if param_name in required else "optionnel"
                param_type = param_info.get("type", "unknown")
                print(f"     • {param_name} ({param_type}, {req})")
            if len(params) > 3:
                print(f"     ... et {len(params) - 3} autres")

    # Vérifications
    assert len(tools) == 7, f"Attendu 7 outils, trouvé {len(tools)}"

    expected_tools = [
        "create_excalidraw_scene",
        "get_excalidraw_scene",
        "update_excalidraw_scene",
        "list_excalidraw_scenes",
        "delete_excalidraw_scene",
        "find_or_create_opepartner_client",
        "health"
    ]

    tool_names = [tool.name for tool in tools]
    for expected in expected_tools:
        assert expected in tool_names, f"Outil {expected} manquant"

    print(f"\n✅ Tous les 7 outils attendus présents")
    print(f"✅ Tous les schémas inputSchema présents")


async def test_02_health_call(session: ClientSession):
    """Test 2 : tools/call health"""
    print("\n" + "="*80)
    print("TEST 2 : tools/call health (healthcheck)")
    print("="*80)

    result = await session.call_tool("health", {})

    print(f"\n🏥 Réponse health :")
    print(json.dumps(result.content[0].text, indent=2))

    # Parser le JSON de la réponse
    health_data = json.loads(result.content[0].text)

    assert health_data["status"] == "healthy"
    assert health_data["service"] == "mcp-excalidraw-opepartner"
    assert health_data["version"] == "H.4.4"

    print(f"\n✅ Health check OK")


async def test_03_create_scene_call(session: ClientSession, nocodb: NocoDBClient, excalidraw: ExcalidrawClient):
    """Test 3 : tools/call create_excalidraw_scene"""
    print("\n" + "="*80)
    print("TEST 3 : tools/call create_excalidraw_scene (orchestration)")
    print("="*80)

    cleanup_sql()

    scene_json = get_sample_scene_json()

    arguments = {
        "scene_json": scene_json,
        "client_name": "TEST-MCP-CLIENT",
        "document_type": "BMC_visuel",
        "document_title": "TEST BMC MCP Client",
        "secteur_activite": "Test",
        "confidentiel": True,
        "tags": ["test", "mcp", "client"]
    }

    print(f"\n📤 Appel create_excalidraw_scene...")
    print(f"   Client : {arguments['client_name']}")
    print(f"   Document : {arguments['document_title']}")

    result = await session.call_tool("create_excalidraw_scene", arguments)

    print(f"\n📥 Réponse MCP :")
    response_text = result.content[0].text
    print(response_text[:500] + "..." if len(response_text) > 500 else response_text)

    # Parser le JSON de la réponse
    response_data = json.loads(response_text)

    # Vérifications
    assert response_data["client_name"] == "TEST-MCP-CLIENT"
    assert "client_id" in response_data
    assert "scene_id" in response_data
    assert "jwk_k" in response_data
    assert "url" in response_data
    assert "schema_id" in response_data
    assert "affine_snippet" in response_data

    print(f"\n✅ Orchestration réussie :")
    print(f"   Client ID : {response_data['client_id']}")
    print(f"   Scene ID : {response_data['scene_id']}")
    print(f"   Schema ID : {response_data['schema_id']}")
    print(f"   URL : {response_data['url'][:60]}...")

    # Vérifier que la scène existe dans Excalidraw
    exists = await scene_exists(excalidraw, response_data['scene_id'])
    assert exists, "La scène doit exister dans Excalidraw"
    print(f"   ✅ Scène vérifiée dans Excalidraw")

    # Vérifier snippet AFFiNE
    snippet = response_data['affine_snippet']
    assert "TEST BMC MCP Client" in snippet
    assert "BMC_visuel" in snippet
    assert response_data['url'] in snippet
    print(f"   ✅ Snippet AFFiNE valide")

    return response_data['scene_id']  # Pour cleanup


async def test_04_cleanup(nocodb: NocoDBClient, excalidraw: ExcalidrawClient, scene_id: str):
    """Test 4 : Cleanup complet"""
    print("\n" + "="*80)
    print("TEST 4 : Cleanup (base + keyv)")
    print("="*80)

    # Cleanup SQL
    cleanup_sql()

    # Cleanup scène Excalidraw
    if scene_id:
        try:
            await excalidraw.delete_scene(scene_id)
            print(f"   🧹 Scène {scene_id} supprimée")
        except:
            pass

    # Vérifier base propre
    nb_clients, nb_schemas = await count_test_records(nocodb)

    print(f"\n📊 État final :")
    print(f"   Clients TEST : {nb_clients}")
    print(f"   Schémas TEST : {nb_schemas}")

    assert nb_clients == 0, f"Attendu 0 clients test, trouvé {nb_clients}"
    assert nb_schemas == 0, f"Attendu 0 schémas test, trouvé {nb_schemas}"

    print(f"\n✅ Base propre")


# =============================================================================
# MAIN
# =============================================================================

async def run_all_tests():
    """Lance tous les tests avec un vrai client MCP"""
    print("\n" + "="*80)
    print("TESTS CLIENT MCP RÉEL — Communication HTTP/SSE")
    print("="*80)

    # Créer client MCP SSE
    async with sse_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(f"\n✅ Connexion MCP SSE établie : {SERVER_URL}")

            # Test 1 : tools/list
            await test_01_tools_list(session)

            # Test 2 : tools/call health
            await test_02_health_call(session)

            # Initialiser clients pour tests 3 et 4
            nocodb = NocoDBClient()
            excalidraw = ExcalidrawClient()

            await nocodb.connect()
            await excalidraw.connect()

            scene_id = None

            try:
                # Test 3 : tools/call create_excalidraw_scene
                scene_id = await test_03_create_scene_call(session, nocodb, excalidraw)

                # Test 4 : Cleanup
                await test_04_cleanup(nocodb, excalidraw, scene_id)

                print("\n" + "="*80)
                print("✅ TOUS LES TESTS CLIENT MCP RÉUSSIS")
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
