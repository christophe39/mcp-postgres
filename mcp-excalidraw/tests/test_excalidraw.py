"""
Test isolation client excalidraw.py
Phase H.3.2 — CRUD scènes avec chiffrement E2E

Tests:
1. create_scene() → insert chiffrée dans keyv
2. get_scene() → lecture + déchiffrement
3. Round-trip: JSON original = JSON déchiffré
4. delete_scene() → nettoyage
"""

import asyncio
import json
import sys
from pathlib import Path

# Ajouter src/ au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.excalidraw import ExcalidrawClient

# Charger .env
from dotenv import load_dotenv
load_dotenv()


def create_test_scene() -> dict:
    """Crée une scène Excalidraw minimaliste pour tests"""
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "type": "rectangle",
                "version": 1,
                "versionNonce": 111111,
                "isDeleted": False,
                "id": "test-excalidraw-client-001",
                "fillStyle": "solid",
                "strokeWidth": 2,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "angle": 0,
                "x": 100,
                "y": 100,
                "width": 300,
                "height": 200,
                "seed": 123456,
                "groupIds": [],
                "frameId": None,
                "roundness": None,
                "boundElements": [],
                "updated": 1,
                "link": None,
                "locked": False,
                "strokeColor": "#1e1e1e",
                "backgroundColor": "#ffec99",
            }
        ],
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff"
        },
        "files": {}
    }


async def test_1_create_scene():
    """Test 1: Créer une scène chiffrée dans keyv"""
    print("\n" + "="*80)
    print("TEST 1 : create_scene() — Création + chiffrement")
    print("="*80)

    scene = create_test_scene()
    scene_json = json.dumps(scene, separators=(',', ':'))

    print(f"Scène test: {len(scene_json)} bytes")
    print(f"  Type: {scene['type']}")
    print(f"  Éléments: {len(scene['elements'])}")

    try:
        async with ExcalidrawClient() as client:
            scene_id, jwk_k, url = await client.create_scene(scene_json)

            print(f"\n✅ Scène créée et chiffrée")
            print(f"   ID: {scene_id}")
            print(f"   Clé JWK.k: {jwk_k} ({len(jwk_k)} chars)")
            print(f"   URL: {url}")

            # Vérifier que la scène existe
            exists = await client.scene_exists(scene_id)
            if not exists:
                print(f"❌ Scène non trouvée après création")
                return None

            print(f"   ✓ Scène vérifiée dans keyv")

            return {
                'scene_id': scene_id,
                'jwk_k': jwk_k,
                'url': url,
                'original_json': scene_json
            }

    except Exception as e:
        print(f"❌ Erreur create_scene: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_2_get_scene(test_data: dict):
    """Test 2: Récupérer et déchiffrer la scène"""
    print("\n" + "="*80)
    print("TEST 2 : get_scene() — Lecture + déchiffrement")
    print("="*80)

    scene_id = test_data['scene_id']
    jwk_k = test_data['jwk_k']

    print(f"Récupération scène: {scene_id}")
    print(f"Clé JWK.k: {jwk_k}")

    try:
        async with ExcalidrawClient() as client:
            decrypted_json = await client.get_scene(scene_id, jwk_k)

            if decrypted_json is None:
                print(f"❌ get_scene() retourne None")
                return False

            print(f"\n✅ Scène déchiffrée")
            print(f"   Taille: {len(decrypted_json)} bytes")

            # Parser pour vérifier que c'est du JSON valide
            try:
                decrypted_scene = json.loads(decrypted_json)
                print(f"   Type: {decrypted_scene.get('type')}")
                print(f"   Éléments: {len(decrypted_scene.get('elements', []))}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON invalide après déchiffrement: {e}")
                return False

            # Stocker pour test 3
            test_data['decrypted_json'] = decrypted_json

            return True

    except Exception as e:
        print(f"❌ Erreur get_scene: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_3_roundtrip(test_data: dict):
    """Test 3: Vérifier round-trip (original = déchiffré)"""
    print("\n" + "="*80)
    print("TEST 3 : Round-trip — JSON original vs déchiffré")
    print("="*80)

    original = test_data['original_json']
    decrypted = test_data['decrypted_json']

    print(f"JSON original: {len(original)} bytes")
    print(f"JSON déchiffré: {len(decrypted)} bytes")

    if original == decrypted:
        print(f"\n✅ ROUND-TRIP RÉUSSI — JSON strictement identique")
        return True
    else:
        print(f"\n❌ ROUND-TRIP ÉCHOUÉ — JSON différent")

        # Afficher les différences
        import difflib
        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            decrypted.splitlines(keepends=True),
            lineterm='',
            n=0
        ))

        if diff:
            print("\nPremières différences:")
            for line in diff[:20]:
                print(line.rstrip())

        return False


async def test_4_delete_scene(test_data: dict):
    """Test 4: Supprimer la scène de test"""
    print("\n" + "="*80)
    print("TEST 4 : delete_scene() — Nettoyage")
    print("="*80)

    scene_id = test_data['scene_id']

    print(f"Suppression scène: {scene_id}")

    try:
        async with ExcalidrawClient() as client:
            deleted = await client.delete_scene(scene_id)

            if not deleted:
                print(f"❌ Suppression échouée")
                return False

            print(f"✅ Scène supprimée")

            # Vérifier que la scène n'existe plus
            still_exists = await client.scene_exists(scene_id)
            if still_exists:
                print(f"❌ Scène toujours présente après suppression")
                return False

            print(f"   ✓ Scène bien supprimée de keyv")

            return True

    except Exception as e:
        print(f"❌ Erreur delete_scene: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_5_list_scenes():
    """Test 5: Lister les scènes (bonus)"""
    print("\n" + "="*80)
    print("TEST 5 : list_scenes() — Listing (bonus)")
    print("="*80)

    try:
        async with ExcalidrawClient() as client:
            scenes = await client.list_scenes(limit=5)

            print(f"✅ Listing réussi: {len(scenes)} scènes récentes")

            for i, scene in enumerate(scenes, 1):
                print(f"   {i}. {scene['scene_id']}")
                print(f"      Créée: {scene['created_at']}")
                print(f"      Taille: {scene['size_bytes']} bytes")

            return True

    except Exception as e:
        print(f"❌ Erreur list_scenes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Exécute tous les tests dans l'ordre"""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*18 + "TESTS EXCALIDRAW CLIENT - PHASE H.3.2" + " "*23 + "║")
    print("╚" + "═"*78 + "╝")

    results = {}
    test_data = {}

    # Test 1: create_scene
    test_data = await test_1_create_scene()
    results['create'] = test_data is not None

    # Test 2: get_scene
    if results['create']:
        results['get'] = await test_2_get_scene(test_data)
    else:
        results['get'] = False
        print("\n⏭️  Test 2 skipped (création échouée)")

    # Test 3: round-trip
    if results['create'] and results['get']:
        results['roundtrip'] = await test_3_roundtrip(test_data)
    else:
        results['roundtrip'] = False
        print("\n⏭️  Test 3 skipped (tests précédents échoués)")

    # Test 4: delete_scene
    if results['create']:
        results['delete'] = await test_4_delete_scene(test_data)
    else:
        results['delete'] = False
        print("\n⏭️  Test 4 skipped (création échouée)")

    # Test 5: list_scenes (bonus)
    results['list'] = await test_5_list_scenes()

    # Résumé
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*30 + "RÉSUMÉ DES TESTS" + " "*33 + "║")
    print("╚" + "═"*78 + "╝")

    print(f"\nTest 1 (create_scene)    : {'✅ RÉUSSI' if results['create'] else '❌ ÉCHOUÉ'}")
    print(f"Test 2 (get_scene)       : {'✅ RÉUSSI' if results['get'] else '❌ ÉCHOUÉ'}")
    print(f"Test 3 (round-trip)      : {'✅ RÉUSSI' if results['roundtrip'] else '❌ ÉCHOUÉ'}")
    print(f"Test 4 (delete_scene)    : {'✅ RÉUSSI' if results['delete'] else '❌ ÉCHOUÉ'}")
    print(f"Test 5 (list_scenes)     : {'✅ RÉUSSI' if results['list'] else '❌ ÉCHOUÉ'}")

    critical_passed = results['create'] and results['get'] and results['roundtrip'] and results['delete']

    if critical_passed:
        print("\n✅ CLIENT EXCALIDRAW.PY VALIDÉ")
        print("   → Round-trip chiffrement prouvé")
        print("   → Prêt pour clients/nocodb.py (H.3.3)")
    else:
        print("\n❌ ÉCHEC — Débugger avant de continuer")

    return critical_passed


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
