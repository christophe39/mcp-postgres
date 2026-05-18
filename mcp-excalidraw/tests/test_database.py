"""
Test isolation client database.py
Phase H.3 — Clients d'intégration

Tests:
1. Connexion avec user mcp_excalidraw
2. SELECT sur keyv (lecture scène existante)
3. INSERT + DELETE sur clé de test
"""

import asyncio
import sys
import os
from pathlib import Path

# Ajouter src/ au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.database import (
    DatabaseClient,
    get_scene_from_keyv,
    insert_scene_to_keyv,
    delete_scene_from_keyv
)

# Charger .env
from dotenv import load_dotenv
load_dotenv()


async def test_1_connexion():
    """Test 1: Connexion pool PostgreSQL avec mcp_excalidraw"""
    print("\n" + "="*80)
    print("TEST 1 : Connexion PostgreSQL (user mcp_excalidraw)")
    print("="*80)

    try:
        async with DatabaseClient() as db:
            # Test query simple
            count = await db.query_value("SELECT count(*) FROM keyv")
            print(f"✅ Connexion réussie")
            print(f"   Total scènes dans keyv: {count}")

            # Vérifier user
            current_user = await db.query_value("SELECT current_user")
            print(f"   User PostgreSQL: {current_user}")

            if current_user != "mcp_excalidraw":
                print(f"⚠️  WARNING: User attendu 'mcp_excalidraw', obtenu '{current_user}'")

            return True

    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_2_select_scene():
    """Test 2: SELECT scène existante dans keyv"""
    print("\n" + "="*80)
    print("TEST 2 : SELECT scène existante")
    print("="*80)

    try:
        async with DatabaseClient() as db:
            # Récupérer n'importe quelle scène existante
            row = await db.query_one(
                """
                SELECT key, length(value::text) as value_length, created_at_tracked
                FROM keyv
                WHERE key LIKE 'SCENES:%'
                ORDER BY created_at_tracked DESC
                LIMIT 1
                """
            )

            if row is None:
                print("⚠️  Aucune scène dans keyv — impossible de tester SELECT")
                print("   (Normal si base vide, pas bloquant)")
                return True

            print(f"✅ SELECT réussi")
            print(f"   Clé: {row['key']}")
            print(f"   Taille value: {row['value_length']} bytes")
            print(f"   Date création: {row['created_at_tracked']}")

            # Test helper get_scene_from_keyv
            scene_id = row['key'].replace('SCENES:', '')
            scene = await get_scene_from_keyv(db, scene_id)

            if scene:
                print(f"\n✅ Helper get_scene_from_keyv() OK")
                print(f"   Type value: {type(scene['value'])}")
            else:
                print(f"❌ Helper get_scene_from_keyv() retourne None")
                return False

            return True

    except Exception as e:
        print(f"❌ Erreur SELECT: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_3_insert_delete():
    """Test 3: INSERT + DELETE clé de test"""
    print("\n" + "="*80)
    print("TEST 3 : INSERT + DELETE (clé de test)")
    print("="*80)

    test_scene_id = "TEST-DATABASE-CLIENT-001"
    test_keyv_wrapper = '{"value":":base64:AQAAAA==","expires":null}'

    try:
        async with DatabaseClient() as db:
            # 1. Vérifier que la clé n'existe pas
            existing = await get_scene_from_keyv(db, test_scene_id)
            if existing:
                print(f"⚠️  Clé de test existe déjà — suppression préalable")
                await delete_scene_from_keyv(db, test_scene_id)

            # 2. INSERT
            print(f"\n--- INSERT ---")
            success = await insert_scene_to_keyv(db, test_scene_id, test_keyv_wrapper)

            if not success:
                print(f"❌ INSERT échoué")
                return False

            print(f"✅ INSERT réussi: SCENES:{test_scene_id}")

            # 3. Vérifier que la clé existe maintenant
            inserted = await get_scene_from_keyv(db, test_scene_id)
            if inserted is None:
                print(f"❌ Clé non trouvée après INSERT")
                return False

            print(f"   Clé retrouvée: {inserted['key']}")
            print(f"   Value: {inserted['value']}")

            # 4. DELETE
            print(f"\n--- DELETE ---")
            deleted = await delete_scene_from_keyv(db, test_scene_id)

            if not deleted:
                print(f"❌ DELETE échoué")
                return False

            print(f"✅ DELETE réussi: SCENES:{test_scene_id}")

            # 5. Vérifier que la clé n'existe plus
            after_delete = await get_scene_from_keyv(db, test_scene_id)
            if after_delete is not None:
                print(f"❌ Clé toujours présente après DELETE")
                return False

            print(f"   Clé bien supprimée")

            return True

    except Exception as e:
        print(f"❌ Erreur INSERT/DELETE: {e}")
        import traceback
        traceback.print_exc()

        # Cleanup en cas d'erreur
        try:
            async with DatabaseClient() as db:
                await delete_scene_from_keyv(db, test_scene_id)
                print(f"\n🧹 Cleanup: clé de test supprimée")
        except:
            pass

        return False


async def run_all_tests():
    """Exécute tous les tests dans l'ordre"""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*20 + "TESTS DATABASE CLIENT - PHASE H.3" + " "*25 + "║")
    print("╚" + "═"*78 + "╝")

    results = {}

    # Test 1: Connexion
    results['connexion'] = await test_1_connexion()

    # Test 2: SELECT
    if results['connexion']:
        results['select'] = await test_2_select_scene()
    else:
        results['select'] = False
        print("\n⏭️  Test 2 skipped (connexion échouée)")

    # Test 3: INSERT/DELETE
    if results['connexion']:
        results['insert_delete'] = await test_3_insert_delete()
    else:
        results['insert_delete'] = False
        print("\n⏭️  Test 3 skipped (connexion échouée)")

    # Résumé
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*30 + "RÉSUMÉ DES TESTS" + " "*33 + "║")
    print("╚" + "═"*78 + "╝")

    print(f"\nTest 1 (Connexion)      : {'✅ RÉUSSI' if results['connexion'] else '❌ ÉCHOUÉ'}")
    print(f"Test 2 (SELECT)         : {'✅ RÉUSSI' if results['select'] else '❌ ÉCHOUÉ'}")
    print(f"Test 3 (INSERT/DELETE)  : {'✅ RÉUSSI' if results['insert_delete'] else '❌ ÉCHOUÉ'}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✅ CLIENT DATABASE.PY VALIDÉ")
        print("   → Prêt pour clients/excalidraw.py (H.3.2)")
    else:
        print("\n❌ ÉCHEC — Débugger avant de continuer")

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
