"""Smoke test imports runtime (H.6 pre-deployment)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

imports = [
    ("fastmcp", "FastMCP"),
    ("fastmcp.server.auth.providers.jwt", "StaticTokenVerifier"),
    ("starlette.responses", "JSONResponse"),
    ("dotenv", "load_dotenv"),
    ("cryptography.hazmat.primitives.ciphers.aead", "AESGCM"),
    ("asyncpg", None),
    ("httpx", None),
    ("crypto", None),
    ("clients.database", "DatabaseClient"),
    ("clients.excalidraw", "ExcalidrawClient"),
    ("clients.nocodb", "NocoDBClient"),
]

errors = []
for mod, attr in imports:
    try:
        exec(f"from {mod} import {attr}" if attr else f"import {mod}")
        print(f"✅ {mod}.{attr or ''}")
    except ImportError as e:
        errors.append(f"{mod}: {e}")
        print(f"❌ {mod}.{attr or ''}")

if errors:
    print(f"\n❌ {len(errors)} imports échoués")
    sys.exit(1)
print(f"\n✅ {len(imports)} imports OK")
