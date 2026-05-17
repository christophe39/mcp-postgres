"""
Test B Final - Phase H.2
Insertion réelle d'une scène de test dans keyv + validation navigateur
"""

import json
import sys
import os
import time

# Ajouter src/ au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import crypto


def create_test_scene():
    """Crée une scène Excalidraw simple mais visible"""
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
                "id": "test-rect-h2-001",
                "fillStyle": "solid",
                "strokeWidth": 4,
                "strokeStyle": "solid",
                "roughness": 0,
                "opacity": 100,
                "angle": 0,
                "x": 300,
                "y": 250,
                "width": 500,
                "height": 200,
                "seed": 999999,
                "groupIds": [],
                "frameId": None,
                "roundness": None,
                "boundElements": ["test-text-h2-001"],
                "updated": 1,
                "link": None,
                "locked": False,
                "strokeColor": "#1971c2",
                "backgroundColor": "#a5d8ff",
            },
            {
                "type": "text",
                "version": 1,
                "versionNonce": 222222,
                "isDeleted": False,
                "id": "test-text-h2-001",
                "fillStyle": "solid",
                "strokeWidth": 2,
                "strokeStyle": "solid",
                "roughness": 1,
                "opacity": 100,
                "angle": 0,
                "x": 370,
                "y": 320,
                "width": 360,
                "height": 60,
                "seed": 888888,
                "groupIds": [],
                "frameId": None,
                "roundness": None,
                "boundElements": [],
                "updated": 1,
                "link": None,
                "locked": False,
                "fontSize": 48,
                "fontFamily": 1,
                "text": "TEST B MCP H2",
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": "test-rect-h2-001",
                "originalText": "TEST B MCP H2",
                "lineHeight": 1.25,
            }
        ],
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff"
        },
        "files": {}
    }

    return scene


def main():
    print("\n" + "="*80)
    print("TEST B FINAL - Phase H.2: MCP → Frontend (validation navigateur)")
    print("="*80)

    # 1. Créer la scène
    scene = create_test_scene()
    scene_json = json.dumps(scene, separators=(',', ':'))
    print(f"\n✅ Scène créée: {len(scene_json)} bytes")
    print(f"   Contenu: Rectangle bleu 500x200 + texte 'TEST B MCP H2' (48px)")

    # 2. Générer clé et chiffrer
    key_bytes = crypto.generate_encryption_key()
    final_buffer, iv, jwk_k = crypto.compress_and_encrypt_scene(scene_json, key_bytes)
    print(f"\n✅ Scène chiffrée: {len(final_buffer)} bytes")
    print(f"   IV: {iv.hex()}")
    print(f"   Clé JWK.k: {jwk_k} ({len(jwk_k)} chars)")

    # 3. Créer wrapper keyv
    keyv_json = crypto.create_keyv_wrapper(final_buffer)
    print(f"\n✅ Wrapper keyv: {len(keyv_json)} bytes")

    # 4. Générer ID de test (UNIQUEMENT numérique - le backend refuse les lettres)
    timestamp = int(time.time() * 1000)  # Millisecondes
    scene_id = str(timestamp)  # Numérique pur
    scene_key = f"SCENES:{scene_id}"
    print(f"\n✅ ID de test: {scene_id} (numérique pur - requis par le backend)")

    # 5. Préparer commande SQL d'insertion
    # Échapper les apostrophes dans le JSON pour PostgreSQL
    keyv_json_escaped = keyv_json.replace("'", "''")

    insert_sql = f"""
INSERT INTO keyv (key, value, created_at_tracked)
VALUES (
    '{scene_key}',
    '{keyv_json_escaped}'::jsonb,
    NOW()
);
"""

    print("\n" + "-"*80)
    print("COMMANDE D'INSERTION:")
    print("-"*80)

    sql_file = "/tmp/test_b_insert.sql"
    with open(sql_file, 'w') as f:
        f.write(insert_sql)

    print(f"SQL écrit dans {sql_file}")
    print("\nExécution sur le VPS...")

    # 6. Exécuter l'insertion
    import subprocess

    cmd = f"""ssh root@69.62.110.207 "docker exec -i pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage" < {sql_file}"""

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n❌ Erreur lors de l'insertion: {result.stderr}")
        return False

    print(f"✅ Insertion réussie: {result.stdout.strip()}")

    # 7. Générer l'URL finale
    url = f"https://excalidraw.agnisolution.fr/#json={scene_id},{jwk_k}"

    print("\n" + "="*80)
    print("🌐 URL DE TEST À OUVRIR DANS LE NAVIGATEUR:")
    print("="*80)
    print(f"\n{url}")
    print("\n" + "="*80)

    print("\n📋 VÉRIFICATION ATTENDUE:")
    print("   ✓ Rectangle BLEU (500x200 pixels)")
    print("   ✓ Texte 'TEST B MCP H2' en blanc, centré dans le rectangle")
    print("   ✓ Police grande (48px), bien lisible")
    print("   ✓ Pas d'erreur de déchiffrement ou de corruption")

    print("\n⚠️  APRÈS VALIDATION:")
    print(f"   Nettoyer avec: DELETE FROM keyv WHERE key = '{scene_key}';")

    # Écrire les infos dans un fichier pour nettoyage facile
    cleanup_file = "/tmp/test_b_cleanup.sql"
    with open(cleanup_file, 'w') as f:
        f.write(f"DELETE FROM keyv WHERE key = '{scene_key}';\n")

    print(f"\n   Script de nettoyage écrit dans {cleanup_file}")

    return {
        "scene_id": scene_id,
        "jwk_k": jwk_k,
        "url": url,
        "cleanup_key": scene_key
    }


if __name__ == "__main__":
    result = main()
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
