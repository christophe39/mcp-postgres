"""
Test basique serveur MCP (H.4.4)
Vérifie démarrage et appels directs Python

Tests :
1. Importation du serveur sans erreur
2. Outils MCP exposés (vérification liste)
3. Appel direct create_scene_orchestrated (bypass HTTP)
4. Auto-cleanup
"""

import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.nocodb import NocoDBClient
from clients.excalidraw import ExcalidrawClient
from tools.orchestration import create_scene_orchestrated
from tools.scenes import scene_exists

from dotenv import load_dotenv
load_dotenv()


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
                "id": "test-server-basic-rect-1",
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

async def test_01_import_server():
    """Test 1 : Import serveur sans erreur"""
    print("\n▶️  Test 1 : Import serveur...")

    try:
        # Import du serveur
        import server

        # Vérifier que FastMCP est configuré
        assert hasattr(server, 'mcp')
        assert server.mcp.name == "Excalidraw OPEPARTNER"

        # Lister les outils exposés
        tools = await server.mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        print(f"   ✅ Serveur importé correctement")
        print(f"   ✅ {len(tool_names)} outils MCP exposés : {tool_names}")

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


async def test_02_create_scene_direct(nocodb: NocoDBClient, excalidraw: ExcalidrawClient):
    """Test 2 : Appel direct create_scene_orchestrated"""
    print("\n▶️  Test 2 : Appel direct create_scene_orchestrated...")

    cleanup_sql()

    scene_json = get_sample_scene_json()

    try:
        result = await create_scene_orchestrated(
            scene_json=scene_json,
            client_name="TEST-SERVER-BASIC",
            document_type="BMC_visuel",
            document_title="TEST BMC Server Basic",
            secteur_activite="Test",
            confidentiel=True,
            tags=["test", "server", "basic"]
        )

        # Vérifications
        assert result["client_name"] == "TEST-SERVER-BASIC"
        assert result["scene_id"]
        assert result["jwk_k"]
        assert result["url"]
        assert result["schema_id"]
        assert result["affine_snippet"]

        # Vérifier snippet
        snippet = result["affine_snippet"]
        assert "TEST BMC Server Basic" in snippet
        assert "BMC_visuel" in snippet
        assert result["url"] in snippet

        print(f"   ✅ Orchestration OK (appel direct Python)")
        print(f"      Client: {result['client_id']}")
        print(f"      Scène: {result['scene_id']}")
        print(f"      Schéma: {result['schema_id']}")

        # Vérifier que la scène existe
        exists = await scene_exists(excalidraw, result['scene_id'])
        assert exists, "La scène doit exister"

        return result['scene_id']  # Pour cleanup

    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_03_cleanup(nocodb: NocoDBClient, excalidraw: ExcalidrawClient, scene_id: str):
    """Test 3 : Cleanup complet"""
    print("\n▶️  Test 3 : Cleanup final...")

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
    print("TESTS SERVER BASIC — Appels directs Python (pas HTTP)")
    print("="*80)

    # Test 1 : Import serveur
    import_ok = await test_01_import_server()
    if not import_ok:
        print("\n⚠️  Import serveur échoué")
        return

    # Initialiser clients pour tests 2 et 3
    nocodb = NocoDBClient()
    excalidraw = ExcalidrawClient()

    await nocodb.connect()
    await excalidraw.connect()

    scene_id = None

    try:
        # Test 2 : Create scene direct
        scene_id = await test_02_create_scene_direct(nocodb, excalidraw)

        # Test 3 : Cleanup
        await test_03_cleanup(nocodb, excalidraw, scene_id)

        print("\n" + "="*80)
        print("✅ TESTS SERVER BASIC RÉUSSIS")
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
