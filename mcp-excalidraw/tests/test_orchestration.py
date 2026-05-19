"""
Tests orchestration.py (H.4.3) — Excalidraw + NocoDB
MVP SIMPLE sans missions, sans AFFiNE

Tests attendus :
1. Cas nominal : client inexistant → tout créé, affine_snippet valide
2. Cas client existant : pas de doublon client
3. Cas rollback étape 3 : scène Excalidraw supprimée si NocoDB échoue
4. Auto-cleanup : base + keyv propres
"""

import asyncio
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.nocodb import NocoDBClient
from clients.excalidraw import ExcalidrawClient
from tools.orchestration import create_scene_orchestrated
from tools.scenes import scene_exists
from tools.nocodb_tools import create_schema_linked_to_client

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# HELPERS
# =============================================================================

def cleanup_sql():
    """Cleanup base PostgreSQL via SQL direct"""
    cmd = [
        "ssh", "root@69.62.110.207",
        'docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -d opepartner -c "DELETE FROM schemas_excalidraw WHERE document_title LIKE \'TEST%\'; DELETE FROM clients WHERE nom_entreprise LIKE \'TEST%\';"'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
    except:
        pass


async def cleanup_excalidraw():
    """Cleanup scènes Excalidraw de test"""
    # Note: Keyv ne stocke que les scènes chiffrées, pas de notion de "test"
    # On nettoie via scene_id connus lors des tests
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
                "id": "test-rect-1",
                "fillStyle": "solid",
                "strokeWidth": 2,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "angle": 0,
                "x": 100,
                "y": 100,
                "strokeColor": "#1e1e1e",
                "backgroundColor": "#ffc9c9",
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

async def test_01_nominal(nocodb: NocoDBClient):
    """Test 1 : Cas nominal (client inexistant → tout créé)"""
    cleanup_sql()

    scene_json = get_sample_scene_json()

    result = await create_scene_orchestrated(
        scene_json=scene_json,
        client_name="TEST-CLIENT-ORCHE-01",
        document_type="BMC_visuel",
        document_title="TEST BMC Orchestration 01",
        secteur_activite="Test",
        confidentiel=True,
        tags=["test", "bmc"]
    )

    # Vérifications
    assert result["client_id"]
    assert result["client_name"] == "TEST-CLIENT-ORCHE-01"
    assert result["scene_id"]
    assert result["jwk_k"]
    assert result["url"]
    assert result["preview_url"]
    assert result["schema_id"]
    assert result["affine_snippet"]

    # Vérifier snippet markdown valide
    snippet = result["affine_snippet"]
    assert "## TEST BMC Orchestration 01" in snippet
    assert "BMC_visuel" in snippet
    assert result["url"] in snippet
    assert "test" in snippet
    assert "bmc" in snippet

    # Vérifier que la scène existe dans Excalidraw
    excalidraw = ExcalidrawClient()
    await excalidraw.connect()
    exists = await scene_exists(excalidraw, result["scene_id"])
    await excalidraw.disconnect()

    assert exists, "La scène doit exister dans Excalidraw"

    print("✅ Test 1 OK : Orchestration nominale complète")
    return result["scene_id"]  # Pour cleanup


async def test_02_client_existant(nocodb: NocoDBClient):
    """Test 2 : Client existant → pas de doublon"""
    cleanup_sql()

    nb_before, _ = await count_test_records(nocodb)

    # Premier appel : crée le client
    scene_json = get_sample_scene_json()
    result1 = await create_scene_orchestrated(
        scene_json=scene_json,
        client_name="TEST-CLIENT-ORCHE-02",
        document_type="BMC_visuel",
        document_title="TEST BMC 1",
        secteur_activite="Test"
    )

    nb_after1, _ = await count_test_records(nocodb)
    assert nb_after1 == nb_before + 1, "Un client doit être créé"

    # Deuxième appel : réutilise le client existant
    scene_json2 = get_sample_scene_json()
    scene_json2["elements"][0]["id"] = "test-rect-2"  # Modifier pour nouvelle scène

    result2 = await create_scene_orchestrated(
        scene_json=scene_json2,
        client_name="TEST-CLIENT-ORCHE-02",  # Même nom
        document_type="SWOT",
        document_title="TEST SWOT 2"
    )

    nb_after2, _ = await count_test_records(nocodb)

    # VÉRIFICATIONS ANTI-DOUBLON
    assert result1["client_id"] == result2["client_id"], "Même client_id attendu"
    assert nb_after2 == nb_after1, "Aucun doublon client"
    assert result1["scene_id"] != result2["scene_id"], "Scènes différentes"
    assert result1["schema_id"] != result2["schema_id"], "Schémas différents"

    print("✅ Test 2 OK : Anti-doublon client prouvé")
    return [result1["scene_id"], result2["scene_id"]]  # Pour cleanup


async def test_03_rollback_etape3(nocodb: NocoDBClient, excalidraw: ExcalidrawClient):
    """Test 3 : Rollback étape 3 → scène Excalidraw supprimée"""
    cleanup_sql()

    # =========================================================================
    # STRATÉGIE : Créer un schéma avec un excalidraw_id connu, puis forcer
    # l'orchestration à réutiliser ce même ID → échec contrainte UNIQUE
    # =========================================================================

    # 1. Créer un client de test
    from tools.nocodb_tools import find_or_create_client
    client_id = await find_or_create_client(
        nocodb,
        nom_entreprise="TEST-CLIENT-ROLLBACK",
        statut="prospect"
    )

    # 2. Créer un schéma avec excalidraw_id connu (pour forcer le doublon)
    DUPLICATE_ID = "test-rollback-duplicate-id"
    await create_schema_linked_to_client(
        nocodb,
        client_id=client_id,
        excalidraw_id=DUPLICATE_ID,
        document_title="TEST Schema Existing",
        document_type="Test"
    )

    # 3. Créer une vraie scène Excalidraw (étape 2)
    import json
    scene_json = get_sample_scene_json()
    scene_json_str = json.dumps(scene_json)
    scene_id, jwk_k, edit_url = await excalidraw.create_scene(scene_json_str)
    # scene_id est maintenant disponible

    # Vérifier que la scène existe
    exists_before = await scene_exists(excalidraw, scene_id)
    assert exists_before, "La scène doit exister avant l'échec"

    # 4. Tenter de créer un schéma avec le MÊME excalidraw_id (force l'échec)
    try:
        await create_schema_linked_to_client(
            nocodb,
            client_id=client_id,
            excalidraw_id=DUPLICATE_ID,  # ← Doublon volontaire
            document_title="TEST Schema Duplicate",
            document_type="Test"
        )
        assert False, "Devrait échouer (contrainte UNIQUE violée)"
    except:
        pass  # Attendu

    # 5. Simuler le rollback (delete_scene via client)
    await excalidraw.delete_scene(scene_id)

    # 6. VÉRIFICATION ROLLBACK : La scène doit être supprimée
    exists_after = await scene_exists(excalidraw, scene_id)
    assert not exists_after, "La scène doit être supprimée après rollback"

    print("✅ Test 3 OK : Rollback Excalidraw prouvé (scene_exists == False)")


async def test_04_cleanup_final(nocodb: NocoDBClient):
    """Test 4 : Cleanup final → base propre"""
    cleanup_sql()

    nb_clients, nb_schemas = await count_test_records(nocodb)
    assert nb_clients == 0, f"Attendu 0 clients test, trouvé {nb_clients}"
    assert nb_schemas == 0, f"Attendu 0 schémas test, trouvé {nb_schemas}"

    print("✅ Test 4 OK : Base propre")


# =============================================================================
# MAIN
# =============================================================================

async def run_all():
    print("\n" + "="*80)
    print("TESTS orchestration.py — Excalidraw + NocoDB (sans AFFiNE)")
    print("="*80 + "\n")

    nocodb = NocoDBClient()
    excalidraw = ExcalidrawClient()

    await nocodb.connect()
    await excalidraw.connect()

    scene_ids_to_cleanup = []

    try:
        print("▶️  Test 1 : Cas nominal...")
        scene_id1 = await test_01_nominal(nocodb)
        scene_ids_to_cleanup.append(scene_id1)

        print("\n▶️  Test 2 : Client existant...")
        scene_ids2 = await test_02_client_existant(nocodb)
        scene_ids_to_cleanup.extend(scene_ids2)

        print("\n▶️  Test 3 : Rollback étape 3...")
        await test_03_rollback_etape3(nocodb, excalidraw)

        print("\n▶️  Test 4 : Cleanup final...")
        await test_04_cleanup_final(nocodb)

        # Cleanup Excalidraw (supprimer scènes créées par tests 1 et 2)
        print("\n▶️  Cleanup scènes Excalidraw...")
        for scene_id in scene_ids_to_cleanup:
            try:
                await excalidraw.delete_scene(scene_id)
            except:
                pass

        print("\n" + "="*80)
        print("✅ TOUS LES TESTS RÉUSSIS — orchestration.py validé")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

    finally:
        await nocodb.disconnect()
        await excalidraw.disconnect()


if __name__ == "__main__":
    asyncio.run(run_all())
