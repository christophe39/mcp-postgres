"""
Serveur MCP Excalidraw OPEPARTNER
Phase H.6 — Déploiement remote (FastMCP HTTP streamable)

ARCHITECTURE :
- Serveur MCP via FastMCP (transport HTTP streamable, recommandé remote)
- Endpoint MCP : /mcp (path standard FastMCP HTTP)
- Healthcheck : /health (route custom non protégée)
- Auth : StaticTokenVerifier (bearer token statique)

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
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
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
# AUTH CONFIGURATION (StaticTokenVerifier)
# =============================================================================

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
AUTH_BEARER_TOKEN = os.getenv("AUTH_BEARER_TOKEN", "")

if AUTH_ENABLED and AUTH_BEARER_TOKEN:
    # Mode production : auth activée avec token statique
    verifier = StaticTokenVerifier(
        tokens={
            AUTH_BEARER_TOKEN: {
                "client_id": "opepartner-user",
                "scopes": ["execute"]
            }
        },
        required_scopes=["execute"]
    )
    mcp = FastMCP("Excalidraw OPEPARTNER", version="H.6", auth=verifier)
    print("🔒 Auth activée : bearer token requis pour MCP endpoint")
else:
    # Mode dev local : pas d'auth
    mcp = FastMCP("Excalidraw OPEPARTNER", version="H.6")
    print("⚠️  Auth désactivée : mode dev local")


# =============================================================================
# ROUTE HTTP CUSTOM : /health (non protégée par auth)
# =============================================================================

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """
    Healthcheck HTTP pour Coolify (H.6)

    Route non protégée par auth (doc FastMCP : custom routes jamais protégées).
    Utilisé par Coolify pour vérifier que le service est healthy.

    Returns:
        JSONResponse avec status healthy
    """
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-excalidraw-opepartner",
        "version": "H.6",
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
