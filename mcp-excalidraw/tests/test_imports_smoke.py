"""
Smoke test : vérifier que tous les imports du code sont disponibles
H.6 - Avant déploiement Coolify
"""

import sys
from pathlib import Path

# Ajouter src/ au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("🔍 Smoke test : vérification imports runtime\n")

# Liste des imports à tester (extraits du code réel)
imports_to_test = [
    # server.py
    ("fastmcp", "FastMCP"),
    ("fastmcp.server.auth.providers.jwt", "StaticTokenVerifier"),
    ("starlette.responses", "JSONResponse"),
    ("dotenv", "load_dotenv"),

    # src/crypto.py
    ("cryptography.hazmat.primitives.ciphers.aead", "AESGCM"),

    # src/clients/database.py
    ("asyncpg", None),  # import asyncpg (pas from)

    # src/clients/excalidraw.py + nocodb.py
    ("httpx", None),  # import httpx

    # Code local (doit être importable)
    ("crypto", None),
    ("clients.database", "DatabaseClient"),
    ("clients.excalidraw", "ExcalidrawClient"),
    ("clients.nocodb", "NocoDBClient"),
    ("tools.orchestration", "create_scene_orchestrated"),
    ("tools.scenes", "get_scene"),
    ("tools.nocodb_tools", "find_or_create_client"),
]

errors = []

for module_name, attr_name in imports_to_test:
    try:
        if attr_name:
            exec(f"from {module_name} import {attr_name}")
            print(f"✅ from {module_name} import {attr_name}")
        else:
            exec(f"import {module_name}")
            print(f"✅ import {module_name}")
    except ImportError as e:
        error_msg = f"❌ {module_name}.{attr_name or ''} : {e}"
        print(error_msg)
        errors.append(error_msg)

print("\n" + "="*80)

if errors:
    print(f"❌ {len(errors)} imports échoués :")
    for err in errors:
        print(f"   {err}")
    sys.exit(1)
else:
    print(f"✅ Tous les {len(imports_to_test)} imports runtime sont disponibles")
    print("✅ Container prêt pour production")
    sys.exit(0)
