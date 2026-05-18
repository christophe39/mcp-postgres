"""
Test isolation client nocodb.py
Phase H.3.3 — API NocoDB base OPEPARTNER

Tests:
1. list_clients() — lecture table Clients
2. create_client() — création client de test
3. get_client() / find_client_by_name() — retrouver client
4. delete_client() — suppression client de test
"""

import asyncio
import sys
from pathlib import Path

# Ajouter src/ au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.nocodb import NocoDBClient

# Charger .env
from dotenv import load_dotenv
load_dotenv()


async def test_1_list_clients():
    """Test 1: Lire la table Clients"""
    print("\n" + "="*80)
    print("TEST 1 : list_clients() — Lecture table Clients")
    print("="*80)

    try:
        async with NocoDBClient() as nocodb:
            clients = await nocodb.list_clients(limit=5)

            print(f"✅ Lecture réussie: {len(clients)} clients")

            if clients:
                print(f"\nPremiers clients:")
                for i, client in enumerate(clients[:3], 1):
                    print(f"   {i}. {client.get('nom_entreprise', 'N/A')} — {client.get('statut', 'N/A')}")
                    if 'Id' in client:
                        print(f"      ID: {client['id']}")

            return True

    except Exception as e:
        print(f"❌ Erreur list_clients: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_2_create_client():
    """Test 2: Créer un client de test"""
    print("\n" + "="*80)
    print("TEST 2 : create_client() — Création client de test")
    print("="*80)

    client_data = {
        "nom_entreprise": "TEST-NOCODB-CLIENT-001",
        "notes_internes": "Créé par test_nocodb.py — À SUPPRIMER"
    }

    print(f"Client à créer:")
    print(f"   Nom: {client_data['nom_entreprise']}")

    try:
        async with NocoDBClient() as nocodb:
            # Vérifier que le client n'existe pas déjà
            existing = await nocodb.find_client_by_name(client_data['nom_entreprise'])
            if existing:
                print(f"⚠️  Client de test existe déjà — suppression préalable")
                await nocodb.delete_client(existing['id'])

            # Créer le client
            created = await nocodb.create_client(client_data)
            client_id = created['id']

            # Récupérer le client complet (POST retourne seulement {id})
            client = await nocodb.get_client(client_id)

            print(f"\n✅ Client créé")
            print(f"   ID: {client_id}")
            print(f"   Nom: {client.get('nom_entreprise')}")

            return {'client_id': client_id, 'nom_entreprise': client.get('nom_entreprise')}

    except Exception as e:
        print(f"❌ Erreur create_client: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_3_get_client(test_data: dict):
    """Test 3: Retrouver le client créé"""
    print("\n" + "="*80)
    print("TEST 3 : get_client() / find_client_by_name() — Retrouver client")
    print("="*80)

    client_id = test_data['client_id']
    nom_entreprise = test_data['nom_entreprise']

    print(f"Recherche client ID: {client_id}")

    try:
        async with NocoDBClient() as nocodb:
            # Méthode 1: get_client() par ID
            client_by_id = await nocodb.get_client(client_id)

            if client_by_id is None:
                print(f"❌ get_client({client_id}) retourne None")
                return False

            print(f"✅ get_client() OK")
            print(f"   ID: {client_by_id['id']}")
            print(f"   Nom: {client_by_id['nom_entreprise']}")

            # Méthode 2: find_client_by_name()
            print(f"\nRecherche par nom: {nom_entreprise}")
            client_by_name = await nocodb.find_client_by_name(nom_entreprise)

            if client_by_name is None:
                print(f"❌ find_client_by_name() retourne None")
                return False

            print(f"✅ find_client_by_name() OK")
            print(f"   ID: {client_by_name['id']}")

            # Vérifier que les deux méthodes retournent le même client
            if client_by_id['id'] != client_by_name['id']:
                print(f"❌ IDs différents: {client_by_id['id']} != {client_by_name['id']}")
                return False

            print(f"\n✅ Cohérence: les deux méthodes retournent le même client")

            return True

    except Exception as e:
        print(f"❌ Erreur get_client: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_4_delete_client(test_data: dict):
    """Test 4: Supprimer le client de test"""
    print("\n" + "="*80)
    print("TEST 4 : delete_client() — Suppression client de test")
    print("="*80)

    client_id = test_data['client_id']

    print(f"Suppression client ID: {client_id}")

    try:
        async with NocoDBClient() as nocodb:
            deleted = await nocodb.delete_client(client_id)

            if not deleted:
                print(f"❌ delete_client() retourne False")
                return False

            print(f"✅ Client supprimé")

            # Vérifier que le client n'existe plus
            still_exists = await nocodb.get_client(client_id)

            if still_exists is not None:
                print(f"❌ Client toujours présent après suppression")
                return False

            print(f"   ✓ Client bien supprimé de NocoDB")

            return True

    except Exception as e:
        print(f"❌ Erreur delete_client: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_5_upsert_client():
    """Test 5: Upsert client (bonus)"""
    print("\n" + "="*80)
    print("TEST 5 : upsert_client() — Upsert (bonus)")
    print("="*80)

    client_data = {
        "nom_entreprise": "TEST-UPSERT-001",
        "notes_internes": "Test upsert"
    }

    try:
        async with NocoDBClient() as nocodb:
            # Premier appel: doit créer
            print("Premier upsert (création attendue)...")
            client1 = await nocodb.upsert_client(client_data)
            print(f"✅ Résultat: ID {client1['id']}")

            # Deuxième appel: doit retrouver l'existant
            print("\nDeuxième upsert (existant attendu)...")
            client2 = await nocodb.upsert_client(client_data)
            print(f"✅ Résultat: ID {client2['id']}")

            # Vérifier que c'est le même ID
            if client1['id'] != client2['id']:
                print(f"❌ IDs différents: {client1['id']} != {client2['id']}")
                print("   Upsert ne fonctionne pas correctement")
                return False

            print(f"\n✅ Upsert OK: même ID retourné ({client1['id']})")

            # Cleanup
            await nocodb.delete_client(client1['id'])
            print(f"   🧹 Cleanup: client de test supprimé")

            return True

    except Exception as e:
        print(f"❌ Erreur upsert_client: {e}")
        import traceback
        traceback.print_exc()

        # Cleanup en cas d'erreur
        try:
            async with NocoDBClient() as nocodb:
                existing = await nocodb.find_client_by_name(client_data['nom_entreprise'])
                if existing:
                    await nocodb.delete_client(existing['id'])
                    print(f"\n🧹 Cleanup: client de test supprimé")
        except:
            pass

        return False


async def run_all_tests():
    """Exécute tous les tests dans l'ordre"""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*20 + "TESTS NOCODB CLIENT - PHASE H.3.3" + " "*25 + "║")
    print("╚" + "═"*78 + "╝")

    results = {}
    test_data = {}

    # Test 1: list_clients
    results['list'] = await test_1_list_clients()

    # Test 2: create_client
    if results['list']:
        test_data = await test_2_create_client()
        results['create'] = test_data is not None
    else:
        results['create'] = False
        print("\n⏭️  Test 2 skipped (lecture échouée)")

    # Test 3: get_client / find_client_by_name
    if results['create']:
        results['get'] = await test_3_get_client(test_data)
    else:
        results['get'] = False
        print("\n⏭️  Test 3 skipped (création échouée)")

    # Test 4: delete_client
    if results['create']:
        results['delete'] = await test_4_delete_client(test_data)
    else:
        results['delete'] = False
        print("\n⏭️  Test 4 skipped (création échouée)")

    # Test 5: upsert_client (bonus)
    if results['list']:
        results['upsert'] = await test_5_upsert_client()
    else:
        results['upsert'] = False
        print("\n⏭️  Test 5 skipped (lecture échouée)")

    # Résumé
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*30 + "RÉSUMÉ DES TESTS" + " "*33 + "║")
    print("╚" + "═"*78 + "╝")

    print(f"\nTest 1 (list_clients)    : {'✅ RÉUSSI' if results['list'] else '❌ ÉCHOUÉ'}")
    print(f"Test 2 (create_client)   : {'✅ RÉUSSI' if results['create'] else '❌ ÉCHOUÉ'}")
    print(f"Test 3 (get_client)      : {'✅ RÉUSSI' if results['get'] else '❌ ÉCHOUÉ'}")
    print(f"Test 4 (delete_client)   : {'✅ RÉUSSI' if results['delete'] else '❌ ÉCHOUÉ'}")
    print(f"Test 5 (upsert_client)   : {'✅ RÉUSSI' if results['upsert'] else '❌ ÉCHOUÉ'}")

    critical_passed = results['list'] and results['create'] and results['get'] and results['delete']

    if critical_passed:
        print("\n✅ CLIENT NOCODB.PY VALIDÉ")
        print("   → Prêt pour clients/affine.py (H.3.4)")
    else:
        print("\n❌ ÉCHEC — Débugger avant de continuer")

    return critical_passed


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
