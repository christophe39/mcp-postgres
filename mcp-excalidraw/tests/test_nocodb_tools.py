"""
Tests nocodb_tools.py (H.4.2) — MVP SIMPLE sans missions
Pattern validé par curl
"""

import asyncio
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.nocodb import NocoDBClient
from tools.nocodb_tools import (
    find_or_create_client,
    create_schema_linked_to_client,
    get_schema_with_client
)

from dotenv import load_dotenv
load_dotenv()


def cleanup_sql():
    """Cleanup via SQL direct"""
    cmd = [
        "ssh", "root@69.62.110.207",
        'docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -d opepartner -c "DELETE FROM schemas_excalidraw WHERE document_title LIKE \'TEST%\'; DELETE FROM clients WHERE nom_entreprise LIKE \'TEST%\';"'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
    except:
        pass


async def count_test(nocodb):
    """Compte clients/schémas TEST-*"""
    clients = await nocodb.list_clients(limit=1000)
    schemas = await nocodb.list_schemas_excalidraw(limit=1000)
    return (
        sum(1 for c in clients if c.get("nom_entreprise", "").startswith("TEST")),
        sum(1 for s in schemas if s.get("document_title", "").startswith("TEST"))
    )


async def test_01(nocodb):
    """Test 1 : Client inexistant → créé"""
    cleanup_sql()
    client_id = await find_or_create_client(nocodb, nom_entreprise="TEST-001")
    assert client_id and len(client_id) == 36
    print("✅ Test 1 OK")


async def test_02(nocodb):
    """Test 2 : Client existant → même ID (anti-doublon)"""
    cleanup_sql()
    nb_before, _ = await count_test(nocodb)
    id1 = await find_or_create_client(nocodb, nom_entreprise="TEST-002")
    nb_after1, _ = await count_test(nocodb)
    assert nb_after1 == nb_before + 1
    id2 = await find_or_create_client(nocodb, nom_entreprise="TEST-002")
    nb_after2, _ = await count_test(nocodb)
    assert id1 == id2 and nb_after2 == nb_after1
    print("✅ Test 2 OK : Anti-doublon prouvé")


async def test_03(nocodb):
    """Test 3 : Schéma lié à client, mission_id NULL"""
    cleanup_sql()
    client_id = await find_or_create_client(nocodb, nom_entreprise="TEST-003")
    schema_id = await create_schema_linked_to_client(
        nocodb, client_id=client_id,
        excalidraw_id=f"test-{asyncio.get_event_loop().time()}",
        document_title="TEST Schema 03", document_type="BMC"
    )
    schema = await get_schema_with_client(nocodb, schema_id)
    assert schema["client_id"] == client_id and not schema.get("mission_id")
    print("✅ Test 3 OK : Schéma lié, mission_id NULL")


async def test_04(nocodb):
    """Test 4 : Échec liaison → rollback (pas d'orphelin)"""
    cleanup_sql()
    _, nb_before = await count_test(nocodb)
    try:
        await create_schema_linked_to_client(
            nocodb, client_id="00000000-0000-0000-0000-000000000000",
            excalidraw_id=f"test-rb-{asyncio.get_event_loop().time()}",
            document_title="TEST RB", document_type="Test"
        )
        assert False, "Devrait lever RuntimeError"
    except RuntimeError:
        pass
    _, nb_after = await count_test(nocodb)
    assert nb_after == nb_before
    print("✅ Test 4 OK : Rollback prouvé")


async def test_05(nocodb):
    """Test 5 : Cleanup final → base propre"""
    cleanup_sql()
    nb_c, nb_s = await count_test(nocodb)
    assert nb_c == 0 and nb_s == 0
    print("✅ Test 5 OK : Base propre")


async def run_all():
    print("\n" + "="*80)
    print("TESTS nocodb_tools.py — MVP SIMPLE (sans missions)")
    print("="*80 + "\n")
    
    nocodb = NocoDBClient()
    await nocodb.connect()
    
    try:
        await test_01(nocodb)
        await test_02(nocodb)
        await test_03(nocodb)
        await test_04(nocodb)
        await test_05(nocodb)
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS RÉUSSIS — nocodb_tools.py validé")
        print("="*80 + "\n")
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
    finally:
        await nocodb.disconnect()


if __name__ == "__main__":
    asyncio.run(run_all())
