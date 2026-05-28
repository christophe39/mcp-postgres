"""
Serveur MCP Excalidraw OPEPARTNER
Phase H.7 — MultiAuth OIDC + bearer fallback
Keycloak realm "mcp" + token statique legacy (scripts/agents)

ARCHITECTURE :
- Serveur MCP via FastMCP (transport HTTP streamable, recommandé remote)
- Endpoint MCP : /mcp (path standard FastMCP HTTP)
- Healthcheck : /health (route custom non protégée)
- Auth : MultiAuth (OIDCProxy + StaticTokenVerifier fallback)
- OIDC : Keycloak realm "mcp" (client "mcp-excalidraw")
- Bearer fallback : token statique pour scripts legacy

OUTILS MCP EXPOSÉS :
- create_excalidraw_scene : orchestration complète Excalidraw + NocoDB
- get_excalidraw_scene : récupère et déchiffre une scène
- update_excalidraw_scene : modifie une scène existante
- list_excalidraw_scenes : liste des scènes disponibles
- delete_excalidraw_scene : suppression avec confirmation
- find_or_create_opepartner_client : gestion clients standalone
- health : healthcheck MCP tool (legacy, utilisé en H.4.4)

DÉPLOIEMENT :
- Local dev : AUTH_ENABLED=false (pas d'auth)
- Remote prod : AUTH_ENABLED=true + AUTH_BEARER_TOKEN (token statique)
- Coolify healthcheck : GET /health (HTTP, pas MCP)
"""

import os
import sys
import json
import hashlib
import base64
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastmcp import FastMCP
from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
from starlette.responses import JSONResponse

# Ajouter src/ au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.orchestration import create_scene_orchestrated
from tools.scenes import get_scene, update_scene, list_scenes, delete_scene
from tools.nocodb_tools import find_or_create_client
from clients.nocodb import NocoDBClient

# Chargement .env
from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# AUTH CONFIGURATION (MultiAuth : OIDCProxy + StaticTokenVerifier)
# =============================================================================

def derive_fernet_key(s: str) -> bytes:
    """Dérive une clé Fernet 32-byte URL-safe depuis une string."""
    return base64.urlsafe_b64encode(hashlib.sha256(s.encode()).digest())


AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

if AUTH_ENABLED:
    # Mode production : MultiAuth avec OIDC principal + bearer fallback

    # Variables d'environnement OIDC (Keycloak realm "mcp")
    OIDC_CONFIG_URL = os.getenv("OIDC_CONFIG_URL")
    OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
    MCP_BASE_URL = os.getenv("MCP_BASE_URL")
    REDIS_URL = os.getenv("REDIS_URL")
    JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY")
    FERNET_SECRET = os.getenv("FERNET_SECRET")

    # Token bearer statique (fallback pour scripts legacy)
    AUTH_BEARER_TOKEN = os.getenv("AUTH_BEARER_TOKEN", "")

    # Validation config OIDC (toutes obligatoires)
    missing_vars = []
    if not OIDC_CONFIG_URL:
        missing_vars.append("OIDC_CONFIG_URL")
    if not OIDC_CLIENT_ID:
        missing_vars.append("OIDC_CLIENT_ID")
    if not OIDC_CLIENT_SECRET:
        missing_vars.append("OIDC_CLIENT_SECRET")
    if not MCP_BASE_URL:
        missing_vars.append("MCP_BASE_URL")
    if not REDIS_URL:
        missing_vars.append("REDIS_URL")
    if not JWT_SIGNING_KEY:
        missing_vars.append("JWT_SIGNING_KEY")
    if not FERNET_SECRET:
        missing_vars.append("FERNET_SECRET")

    if missing_vars:
        raise ValueError(f"Missing required OIDC environment variables: {', '.join(missing_vars)}")

    # Setup storage Redis chiffré (pattern validé mcp-jouet)
    fernet = Fernet(derive_fernet_key(FERNET_SECRET))
    store = RedisStore(url=REDIS_URL)
    encrypted_store = FernetEncryptionWrapper(
        key_value=store,
        fernet=fernet,
        raise_on_decryption_error=False,
    )

    # Provider OIDC principal (Keycloak)
    oidc_proxy = OIDCProxy(
        config_url=OIDC_CONFIG_URL,
        client_id=OIDC_CLIENT_ID,
        client_secret=OIDC_CLIENT_SECRET,
        audience=MCP_BASE_URL,              # Recommandé pour prod (Keycloak best practice)
        base_url=MCP_BASE_URL,
        redirect_path="/auth/callback",
        required_scopes=["openid", "mcp:execute"],
        jwt_signing_key=JWT_SIGNING_KEY,
        client_storage=encrypted_store,
    )

    # Verifier fallback (bearer statique pour scripts legacy)
    verifiers = []
    if AUTH_BEARER_TOKEN:
        static_verifier = StaticTokenVerifier(
            tokens={
                AUTH_BEARER_TOKEN: {
                    "client_id": "legacy-bearer-script",
                    "scopes": ["mcp:execute"]
                }
            },
            required_scopes=["mcp:execute"]
        )
        verifiers.append(static_verifier)

    # MultiAuth : OIDC en premier, bearer en fallback
    auth = MultiAuth(
        server=oidc_proxy,
        verifiers=verifiers,
        required_scopes=["mcp:execute"]
    )

    mcp = FastMCP("Excalidraw OPEPARTNER", version="H.7", auth=auth)
    print(f"""
🔒 Auth MultiAuth activée :
   • OIDC principal : {OIDC_CLIENT_ID} @ {OIDC_CONFIG_URL}
   • Bearer fallback : {'✅ Activé' if AUTH_BEARER_TOKEN else '❌ Désactivé'}
   • Scopes requis : openid, mcp:execute
""")
else:
    # Mode dev local : pas d'auth
    mcp = FastMCP("Excalidraw OPEPARTNER", version="H.7")
    print("⚠️  Auth désactivée : mode dev local")


# =============================================================================
# ROUTE HTTP CUSTOM : /health (non protégée par auth)
# =============================================================================

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """
    Healthcheck HTTP pour Coolify (H.7)

    Route non protégée par auth (doc FastMCP : custom routes jamais protégées).
    Utilisé par Coolify pour vérifier que le service est healthy.

    Returns:
        JSONResponse avec status healthy
    """
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-excalidraw-opepartner",
        "version": "H.7",
        "transport": "http",
        "endpoint": "/mcp"
    })


# =============================================================================
# OUTILS MCP EXPOSÉS À CLAUDE
# =============================================================================

@mcp.tool()
async def create_excalidraw_scene(
    scene_json: Dict[str, Any],
    client_name: str,
    document_type: str,
    document_title: str,
    secteur_activite: Optional[str] = None,
    confidentiel: bool = True,
    tags: Optional[List[str]] = None,
    notes_internal: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crée une scène Excalidraw chiffrée + entrée NocoDB liée à un client

    Orchestration complète Excalidraw + NocoDB OPEPARTNER.

    Args:
        scene_json: JSON Excalidraw complet ({"type":"excalidraw","version":2,"elements":[...],...})
        client_name: Nom du client (anti-doublon automatique)
        document_type: Type de document (ex: "BMC_visuel", "PESTEL", "SWOT")
        document_title: Titre du document
        secteur_activite: Secteur d'activité optionnel
        confidentiel: Marquer comme confidentiel (défaut: True)
        tags: Tags optionnels (liste de strings)
        notes_internal: Notes internes optionnelles

    Returns:
        Dict avec client_id, scene_id, url, schema_id, affine_snippet

    Example:
        scene = {
            "type": "excalidraw",
            "version": 2,
            "elements": [{"type": "rectangle", ...}],
            "appState": {},
            "files": {}
        }

        result = await create_excalidraw_scene(
            scene_json=scene,
            client_name="Dupont SAS",
            document_type="BMC_visuel",
            document_title="BMC — Dupont SAS",
            tags=["BMC", "stratégie"]
        )

        print(f"Scène créée : {result['url']}")
        print(f"Snippet AFFiNE :\n{result['affine_snippet']}")
    """
    return await create_scene_orchestrated(
        scene_json=scene_json,
        client_name=client_name,
        document_type=document_type,
        document_title=document_title,
        secteur_activite=secteur_activite,
        confidentiel=confidentiel,
        tags=tags,
        notes_internal=notes_internal
    )


@mcp.tool()
async def get_excalidraw_scene(
    scene_id: str,
    jwk_k: str
) -> Dict[str, Any]:
    """
    Récupère et déchiffre une scène Excalidraw

    Args:
        scene_id: ID de scène (ex: "1779030793059")
        jwk_k: Clé de déchiffrement base64url 22 chars

    Returns:
        Dict avec scene_id, scene_data (JSON déchiffré), size_bytes

    Example:
        result = await get_excalidraw_scene("1779030793059", "R0dHIsECVzcIVDztmUTNyw")
        scene = result['scene_data']
        print(f"Éléments : {len(scene['elements'])}")
    """
    return await get_scene(scene_id, jwk_k)


@mcp.tool()
async def update_excalidraw_scene(
    scene_id: str,
    jwk_k: str,
    scene_json: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Met à jour une scène existante (même ID, même clé, nouvel IV)

    Args:
        scene_id: ID de scène à modifier
        jwk_k: Clé de déchiffrement (prouve le droit de modifier)
        scene_json: Nouveau JSON Excalidraw complet

    Returns:
        Dict avec scene_id, jwk_k (identique), url (identique), updated=True

    Example:
        # Récupérer la scène
        current = await get_excalidraw_scene(scene_id, jwk_k)

        # Modifier
        scene = current['scene_data']
        scene['elements'].append({...})

        # Sauvegarder (URL reste identique)
        result = await update_excalidraw_scene(scene_id, jwk_k, scene)
    """
    # Convertir dict en JSON string pour update_scene
    scene_json_str = json.dumps(scene_json)
    return await update_scene(scene_id, jwk_k, scene_json_str)


@mcp.tool()
async def list_excalidraw_scenes(
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Liste les scènes disponibles

    Args:
        limit: Nombre max de scènes (défaut: 100, max: 1000)
        offset: Offset pour pagination (défaut: 0)

    Returns:
        Dict avec scenes (liste), total, limit, offset

    Example:
        result = await list_excalidraw_scenes(limit=10)
        for scene in result['scenes']:
            print(f"{scene['scene_id']} — {scene['created_at']}")
    """
    return await list_scenes(limit, offset)


@mcp.tool()
async def delete_excalidraw_scene(
    scene_id: str,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Supprime une scène (RGPD droit à l'oubli)

    ATTENTION : Opération IRRÉVERSIBLE. Requiert confirm=True.

    Args:
        scene_id: ID de scène à supprimer
        confirm: Doit être True pour confirmer la suppression

    Returns:
        Dict avec scene_id, deleted=True

    Example:
        # INCORRECT (refusé)
        await delete_excalidraw_scene(scene_id)  # ValueError

        # CORRECT
        result = await delete_excalidraw_scene(scene_id, confirm=True)
        print(f"Scène {result['scene_id']} supprimée")
    """
    return await delete_scene(scene_id, confirm)


@mcp.tool()
async def find_or_create_opepartner_client(
    client_name: str,
    secteur_activite: Optional[str] = None,
    statut: str = "prospect"
) -> Dict[str, str]:
    """
    Trouve ou crée un client (anti-doublon sur nom)

    Args:
        client_name: Nom du client
        secteur_activite: Secteur d'activité optionnel
        statut: Statut du client (défaut: "prospect")

    Returns:
        Dict avec client_id (UUID)

    Example:
        result = await find_or_create_opepartner_client("Dupont SAS", "Industrie")
        print(f"Client ID: {result['client_id']}")
    """
    async with NocoDBClient() as nocodb:
        client_id = await find_or_create_client(
            nocodb,
            nom_entreprise=client_name,
            secteur_activite=secteur_activite,
            statut=statut
        )

    return {"client_id": client_id}


# =============================================================================
# MAIN : Démarrage serveur
# =============================================================================

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))

    auth_status = "🔒 Activée (bearer token)" if AUTH_ENABLED else "⚠️  Désactivée (dev local)"

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║  MCP Excalidraw OPEPARTNER — Serveur démarré (H.6)            ║
╠════════════════════════════════════════════════════════════════╣
║  Transport : HTTP streamable (recommandé remote)               ║
║  Endpoint  : http://{host}:{port}/mcp{' ' * (37 - len(host) - len(str(port)))} ║
║  Health    : http://{host}:{port}/health{' ' * (34 - len(host) - len(str(port)))} ║
║  Auth      : {auth_status:<50} ║
╠════════════════════════════════════════════════════════════════╣
║  Outils MCP exposés (6) :                                      ║
║  • create_excalidraw_scene (orchestration complète)            ║
║  • get_excalidraw_scene                                        ║
║  • update_excalidraw_scene                                     ║
║  • list_excalidraw_scenes                                      ║
║  • delete_excalidraw_scene (confirm=True requis)               ║
║  • find_or_create_opepartner_client                            ║
╠════════════════════════════════════════════════════════════════╣
║  Doc FastMCP : transport HTTP streamable (pas SSE legacy)      ║
║  /health : route custom non protégée (Coolify healthcheck)     ║
║  Auth : StaticTokenVerifier (token statique, pas JWT)          ║
╚════════════════════════════════════════════════════════════════╝
    """)

    # Démarrer serveur MCP (transport HTTP streamable - recommandé remote)
    mcp.run(transport="http", host=host, port=port)
