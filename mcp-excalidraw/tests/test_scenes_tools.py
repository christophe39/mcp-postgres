"""
Test isolation outils scenes.py
Phase H.4.1 — Outils MCP de base

Tests:
1. create_scene() — création + validation retour
2. get_scene() — lecture + vérification contenu
3. update_scene() — modification + vérification
4. list_scenes() — listing avec métadonnées
5. delete_scene() — suppression avec confirmation
6. delete_scene() sans confirm — doit échouer (sécurité)
"""

import asyncio
import json
import sys
from pathlib import Path

# Ajouter src/ au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.scenes import (
    create_scene,
    get_scene,
    update_scene,
    list_scenes,
    delete_scene
)

# Charger .env
from dotenv import load_dotenv
load_dotenv()


def create_test_scene() -> str:
    """Crée une scène Excalidraw minimaliste pour tests"""
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {
                "type": "rectangle",
                "version": 1,
                "versionNonce": 111111,
                "isDeleted": False,
                "id": "test-scenes-tools-001",
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
                "backgroundColor": "#a5d8ff",
            }
        ],
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff"
        },
        "files": {}
    }

    return json.dumps(scene, separators=(',', ':'))


async def test_1_create_scene():
    """Test 1: Créer une scène via outil MCP"""
    print("\n" + "="*80)
    print("TEST 1 : create_scene() — Création via outil MCP")
    print("="*80)

    scene_json = create_test_scene()

    print(f"Scène test: {len(scene_json)} bytes")

    try:
        result = await create_scene(scene_json)

        print(f"\n✅ Scène créée")
        print(f"   ID: {result['scene_id']}")
        print(f"   Clé: {result['jwk_k']} ({len(result['jwk_k'])} chars)")
        print(f"   URL: {result['url']}")
        print(f"   Taille: {result['size_bytes']} bytes")

        # Validations
        assert 'scene_id' in result
        assert 'jwk_k' in result
        assert 'url' in result
        assert len(result['jwk_k']) == 22
        assert result['size_bytes'] == len(scene_json)

        print(f"   ✓ Format retour validé")

        return result

    except Exception as e:
        print(f"❌ Erreur create_scene: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_2_get_scene(test_data: dict):
    """Test 2: Récupérer une scène via outil MCP"""
    print("\n" + "="*80)
    print("TEST 2 : get_scene() — Lecture via outil MCP")
    print("="*80)

    scene_id = test_data['scene_id']
    jwk_k = test_data['jwk_k']

    print(f"Récupération scène: {scene_id}")

    try:
        result = await get_scene(scene_id, jwk_k)

        print(f"\n✅ Scène récupérée")
        print(f"   ID: {result['scene_id']}")
        print(f"   Taille: {result['size_bytes']} bytes")
        print(f"   Type: {result['scene_data']['type']}")
        print(f"   Éléments: {len(result['scene_data']['elements'])}")

        # Validations
        assert result['scene_id'] == scene_id
        assert result['scene_data']['type'] == 'excalidraw'
        assert len(result['scene_data']['elements']) == 1
        assert result['scene_data']['elements'][0]['id'] == 'test-scenes-tools-001'

        print(f"   ✓ Contenu validé")

        # Stocker pour test 3
        test_data['original_scene'] = result['scene_data']

        return True

    except Exception as e:
        print(f"❌ Erreur get_scene: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_3_update_scene(test_data: dict):
    """Test 3: Mettre à jour une scène via outil MCP"""
    print("\n" + "="*80)
    print("TEST 3 : update_scene() — Modification via outil MCP")
    print("="*80)

    scene_id = test_data['scene_id']
    jwk_k = test_data['jwk_k']
    original_scene = test_data['original_scene']

    print(f"Modification scène: {scene_id}")

    # Modifier la scène (ajouter un élément)
    modified_scene = original_scene.copy()
    modified_scene['elements'] = original_scene['elements'].copy()
    modified_scene['elements'].append({
        "type": "text",
        "version": 1,
        "versionNonce": 222222,
        "isDeleted": False,
        "id": "test-scenes-tools-002",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "x": 150,
        "y": 150,
        "width": 200,
        "height": 50,
        "seed": 654321,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "boundElements": [],
        "updated": 2,
        "link": None,
        "locked": False,
        "text": "TEST UPDATE",
        "fontSize": 20,
        "fontFamily": 1,
        "textAlign": "left",
        "verticalAlign": "top",
        "baseline": 18,
        "containerId": None,
        "originalText": "TEST UPDATE"
    })

    modified_json = json.dumps(modified_scene, separators=(',', ':'))

    print(f"   Éléments originaux: {len(original_scene['elements'])}")
    print(f"   Éléments modifiés: {len(modified_scene['elements'])}")

    try:
        result = await update_scene(scene_id, jwk_k, modified_json)

        print(f"\n✅ Scène mise à jour")
        print(f"   ID: {result['scene_id']}")
        print(f"   Nouvelle clé: {result['jwk_k']}")
        print(f"   Taille: {result['size_bytes']} bytes")

        # Validations
        assert result['scene_id'] == scene_id
        assert result['updated'] == True
        assert result['size_bytes'] == len(modified_json)

        print(f"   ✓ Mise à jour validée")

        # Vérifier que la modification est persistée
        print(f"\n   Vérification persistance...")
        updated = await get_scene(scene_id, result['jwk_k'])

        assert len(updated['scene_data']['elements']) == 2
        assert updated['scene_data']['elements'][1]['id'] == 'test-scenes-tools-002'
        assert updated['scene_data']['elements'][1]['text'] == 'TEST UPDATE'

        print(f"   ✓ Persistance confirmée (2 éléments)")

        # Stocker nouvelle clé pour test 5
        test_data['jwk_k'] = result['jwk_k']

        return True

    except Exception as e:
        print(f"❌ Erreur update_scene: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_4_list_scenes():
    """Test 4: Lister les scènes via outil MCP"""
    print("\n" + "="*80)
    print("TEST 4 : list_scenes() — Listing via outil MCP")
    print("="*80)

    try:
        result = await list_scenes(limit=5)

        print(f"\n✅ Listing réussi")
        print(f"   Total: {result['total']} scènes")
        print(f"   Limit: {result['limit']}")
        print(f"   Offset: {result['offset']}")

        if result['scenes']:
            print(f"\n   Premières scènes:")
            for i, scene in enumerate(result['scenes'][:3], 1):
                print(f"   {i}. {scene['scene_id']}")
                print(f"      Créée: {scene['created_at']}")
                print(f"      Taille: {scene['size_bytes']} bytes")

        # Validations
        assert 'scenes' in result
        assert 'total' in result
        assert result['total'] >= 0
        assert result['limit'] == 5

        print(f"\n   ✓ Format retour validé")

        return True

    except Exception as e:
        print(f"❌ Erreur list_scenes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_5_delete_scene_without_confirm(test_data: dict):
    """Test 5: Tenter suppression sans confirm (doit échouer)"""
    print("\n" + "="*80)
    print("TEST 5 : delete_scene() sans confirm — Sécurité")
    print("="*80)

    scene_id = test_data['scene_id']

    print(f"Tentative suppression sans confirm: {scene_id}")

    try:
        # Doit lever ValueError
        result = await delete_scene(scene_id, confirm=False)

        print(f"❌ Suppression autorisée sans confirm — ÉCHEC SÉCURITÉ")
        return False

    except ValueError as e:
        print(f"\n✅ Suppression refusée (attendu)")
        print(f"   Message: {str(e)[:100]}...")
        print(f"   ✓ Sécurité validée")
        return True

    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_6_delete_scene_with_confirm(test_data: dict):
    """Test 6: Supprimer avec confirm (doit réussir)"""
    print("\n" + "="*80)
    print("TEST 6 : delete_scene() avec confirm=True — Suppression")
    print("="*80)

    scene_id = test_data['scene_id']

    print(f"Suppression scène: {scene_id}")

    try:
        result = await delete_scene(scene_id, confirm=True)

        print(f"\n✅ Scène supprimée")
        print(f"   ID: {result['scene_id']}")
        print(f"   Deleted: {result['deleted']}")

        # Validations
        assert result['scene_id'] == scene_id
        assert result['deleted'] == True

        print(f"   ✓ Suppression validée")

        # Vérifier que la scène n'existe plus
        print(f"\n   Vérification disparition...")
        try:
            await get_scene(scene_id, test_data['jwk_k'])
            print(f"❌ Scène toujours accessible après suppression")
            return False
        except Exception:
            print(f"   ✓ Scène bien supprimée (inaccessible)")

        return True

    except Exception as e:
        print(f"❌ Erreur delete_scene: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_7_url_stability_after_update():
    """Test 7: CRITIQUE - Vérifier que l'URL reste identique après update"""
    print("\n" + "="*80)
    print("TEST 7 : Stabilité URL après update — CRITIQUE pour workflow réel")
    print("="*80)

    scene_json = create_test_scene()

    print(f"Scène test: {len(scene_json)} bytes")

    try:
        # 1. Créer scène initiale
        print("\n1. Création scène initiale...")
        result_create = await create_scene(scene_json)

        scene_id = result_create['scene_id']
        jwk_k_original = result_create['jwk_k']
        url_original = result_create['url']

        print(f"   ✓ Scène créée")
        print(f"     ID: {scene_id}")
        print(f"     Clé: {jwk_k_original}")
        print(f"     URL: {url_original}")

        # 2. Modifier la scène
        print("\n2. Modification de la scène...")
        current = await get_scene(scene_id, jwk_k_original)
        scene_data = current['scene_data']

        # Ajouter un élément
        scene_data['elements'].append({
            "type": "text",
            "version": 1,
            "versionNonce": 999999,
            "isDeleted": False,
            "id": "test-url-stability",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "x": 200,
            "y": 200,
            "width": 150,
            "height": 40,
            "seed": 888888,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "boundElements": [],
            "updated": 3,
            "link": None,
            "locked": False,
            "text": "URL STABLE",
            "fontSize": 20,
            "fontFamily": 1,
            "textAlign": "left",
            "verticalAlign": "top",
            "baseline": 18,
            "containerId": None,
            "originalText": "URL STABLE"
        })

        modified_json = json.dumps(scene_data, separators=(',', ':'))
        print(f"   ✓ Élément ajouté (1 → {len(scene_data['elements'])} éléments)")

        # 3. Update avec la clé ORIGINALE
        print("\n3. Update de la scène...")
        result_update = await update_scene(scene_id, jwk_k_original, modified_json)

        scene_id_updated = result_update['scene_id']
        jwk_k_updated = result_update['jwk_k']
        url_updated = result_update['url']

        print(f"   ✓ Scène mise à jour")
        print(f"     ID: {scene_id_updated}")
        print(f"     Clé: {jwk_k_updated}")
        print(f"     URL: {url_updated}")

        # 4. VÉRIFICATIONS CRITIQUES
        print("\n4. Vérifications critiques...")

        # 4.1. ID identique
        if scene_id_updated != scene_id:
            print(f"   ❌ ID changé : {scene_id} → {scene_id_updated}")
            return False
        print(f"   ✓ ID inchangé : {scene_id}")

        # 4.2. Clé IDENTIQUE (critique)
        if jwk_k_updated != jwk_k_original:
            print(f"   ❌ CLÉ CHANGÉE : {jwk_k_original} → {jwk_k_updated}")
            print(f"      ÉCHEC CRITIQUE : tous les liens existants sont MORTS")
            return False
        print(f"   ✓ Clé identique : {jwk_k_original}")

        # 4.3. URL IDENTIQUE (critique)
        if url_updated != url_original:
            print(f"   ❌ URL CHANGÉE :")
            print(f"      Avant : {url_original}")
            print(f"      Après : {url_updated}")
            print(f"      ÉCHEC CRITIQUE : liens collés dans AFFiNE sont MORTS")
            return False
        print(f"   ✓ URL identique : {url_original}")

        # 5. Vérifier que le contenu MODIFIÉ est accessible avec la clé ORIGINALE
        print("\n5. Vérification contenu modifié avec clé originale...")
        updated_scene = await get_scene(scene_id, jwk_k_original)

        if len(updated_scene['scene_data']['elements']) != 2:
            print(f"   ❌ Nombre d'éléments incorrect : {len(updated_scene['scene_data']['elements'])}")
            return False

        new_element = updated_scene['scene_data']['elements'][1]
        if new_element['text'] != "URL STABLE":
            print(f"   ❌ Contenu modifié non trouvé")
            return False

        print(f"   ✓ Contenu modifié accessible avec clé originale")
        print(f"     Éléments : 1 → 2")
        print(f"     Texte ajouté : '{new_element['text']}'")

        # 6. Cleanup
        print("\n6. Cleanup...")
        await delete_scene(scene_id, confirm=True)
        print(f"   ✓ Scène de test supprimée")

        print("\n" + "="*80)
        print("✅ TEST CRITIQUE RÉUSSI")
        print("   → URL reste IDENTIQUE après update")
        print("   → Clé reste IDENTIQUE après update")
        print("   → Contenu modifié déchiffrable avec clé originale")
        print("   → Liens existants (AFFiNE, docs) restent VALIDES")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n❌ Erreur test stabilité URL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Exécute tous les tests dans l'ordre"""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*20 + "TESTS SCENES TOOLS - PHASE H.4.1" + " "*26 + "║")
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

    # Test 3: update_scene
    if results['create'] and results['get']:
        results['update'] = await test_3_update_scene(test_data)
    else:
        results['update'] = False
        print("\n⏭️  Test 3 skipped (tests précédents échoués)")

    # Test 4: list_scenes
    results['list'] = await test_4_list_scenes()

    # Test 5: delete sans confirm
    if results['create']:
        results['delete_no_confirm'] = await test_5_delete_scene_without_confirm(test_data)
    else:
        results['delete_no_confirm'] = False
        print("\n⏭️  Test 5 skipped (création échouée)")

    # Test 6: delete avec confirm
    if results['create']:
        results['delete_confirm'] = await test_6_delete_scene_with_confirm(test_data)
    else:
        results['delete_confirm'] = False
        print("\n⏭️  Test 6 skipped (création échouée)")

    # Test 7: URL stability (CRITIQUE)
    results['url_stability'] = await test_7_url_stability_after_update()

    # Résumé
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*30 + "RÉSUMÉ DES TESTS" + " "*33 + "║")
    print("╚" + "═"*78 + "╝")

    print(f"\nTest 1 (create_scene)         : {'✅ RÉUSSI' if results['create'] else '❌ ÉCHOUÉ'}")
    print(f"Test 2 (get_scene)            : {'✅ RÉUSSI' if results['get'] else '❌ ÉCHOUÉ'}")
    print(f"Test 3 (update_scene)         : {'✅ RÉUSSI' if results['update'] else '❌ ÉCHOUÉ'}")
    print(f"Test 4 (list_scenes)          : {'✅ RÉUSSI' if results['list'] else '❌ ÉCHOUÉ'}")
    print(f"Test 5 (delete sans confirm)  : {'✅ RÉUSSI' if results['delete_no_confirm'] else '❌ ÉCHOUÉ'}")
    print(f"Test 6 (delete avec confirm)  : {'✅ RÉUSSI' if results['delete_confirm'] else '❌ ÉCHOUÉ'}")
    print(f"Test 7 (URL stability)        : {'✅ RÉUSSI' if results['url_stability'] else '❌ ÉCHOUÉ'} 🔥 CRITIQUE")

    critical_passed = all(results.values())

    if critical_passed:
        print("\n✅ OUTILS SCENES.PY VALIDÉS")
        print("   → CRUD complet fonctionnel")
        print("   → Sécurité delete_scene prouvée")
        print("   → Stabilité URL après update PROUVÉE (critique workflow)")
        print("   → Prêt pour H.4.2 (nocodb_tools.py)")
    else:
        print("\n❌ ÉCHEC — Débugger avant de continuer")

    return critical_passed


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
