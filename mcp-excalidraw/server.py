"""
Serveur MCP Excalidraw OPEPARTNER
Phase H.4.4 — Remote-ready (FastMCP HTTP/SSE)

ARCHITECTURE :
- Serveur MCP via FastMCP (transport HTTP/SSE)
- Conçu pour déploiement REMOTE (H.6), testé en local (H.4.4)
- Auth middleware : point d'entrée prévu (H.6), désactivé en local

OUTILS MCP EXPOSÉS :
- create_scene_orchestrated : orchestration complète Excalidraw + NocoDB
- get_scene : récupère et déchiffre une scène
- update_scene : modifie une scène existante
- list_scenes : liste des scènes disponibles
- delete_scene : suppression avec confirmation
- find_or_create_client : gestion clients standalone

H.6 : Auth via bearer token, deployment Coolify, HTTPS Traefik
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastmcp import FastMCP

# Ajouter src/ au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.orchestration import create_scene_orchestrated
from tools.scenes import create_scene, get_scene, update_scene, list_scenes, delete_scene
from tools.nocodb_tools import find_or_create_client
from clients.nocodb import NocoDBClient

# Chargement .env
from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# FASTMCP APP (Serveur MCP avec transport HTTP/SSE)
# =============================================================================

mcp = FastMCP(
    "Excalidraw OPEPARTNER",
    version="H.4.4"
)


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
# OUTIL MCP HEALTH (alternative au endpoint HTTP pour healthcheck)
# =============================================================================

@mcp.tool()
async def health() -> Dict[str, str]:
    """
    Health check pour monitoring (alternative à /health endpoint)

    Returns:
        Dict avec status, service, version

    Example:
        result = await health()
        print(f"Service: {result['service']} - Status: {result['status']}")
    """
    return {
        "status": "healthy",
        "service": "mcp-excalidraw-opepartner",
        "version": "H.4.4",
        "transport": "http-sse"
    }


# =============================================================================
# POINT D'ENTRÉE AUTH (H.6 — désactivé pour test local H.4.4)
# =============================================================================

# TODO H.6 : Middleware d'authentification
# -----------------------------------------
# Insertion d'un middleware FastAPI pour vérifier les tokens/API keys
# avant d'autoriser les appels.
#
# FastMCP expose son app FastAPI via mcp.fastapi_app (instance FastAPI).
# On peut ajouter un middleware dessus.
#
# Exemple implémentation H.6 :
#
# from fastapi import Request, HTTPException
#
# @mcp.fastapi_app.middleware("http")
# async def auth_middleware(request: Request, call_next):
#     # Skip auth pour /health, /docs, /openapi.json
#     if request.url.path in ["/health", "/docs", "/openapi.json"]:
#         return await call_next(request)
#
#     # Vérifier bearer token
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         return JSONResponse(
#             status_code=401,
#             content={"error": "Unauthorized"}
#         )
#
#     # Valider token JWT/API key ici
#     token = auth_header.replace("Bearer ", "")
#     if not validate_token(token):
#         return JSONResponse(
#             status_code=401,
#             content={"error": "Invalid token"}
#         )
#
#     response = await call_next(request)
#     return response
#
# Pour H.4.4 (test local) : Auth désactivée, serveur ouvert localhost


# =============================================================================
# MAIN : Démarrage serveur
# =============================================================================

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║  MCP Excalidraw OPEPARTNER — Serveur démarré (H.4.4)          ║
╠════════════════════════════════════════════════════════════════╣
║  Transport : MCP HTTP/SSE (FastMCP)                            ║
║  Host      : {host:<50} ║
║  Port      : {port:<50} ║
║  Auth      : Désactivée (test local)                           ║
╠════════════════════════════════════════════════════════════════╣
║  Outils MCP exposés (7) :                                      ║
║  • create_excalidraw_scene (orchestration complète)            ║
║  • get_excalidraw_scene                                        ║
║  • update_excalidraw_scene                                     ║
║  • list_excalidraw_scenes                                      ║
║  • delete_excalidraw_scene (confirm=True requis)               ║
║  • find_or_create_opepartner_client                            ║
║  • health (healthcheck tool)                                   ║
╠════════════════════════════════════════════════════════════════╣
║  H.6 : Auth bearer token + déploiement Coolify + HTTPS         ║
╚════════════════════════════════════════════════════════════════╝
    """)

    # Démarrer serveur MCP (transport HTTP/SSE)
    mcp.run(transport="sse", host=host, port=port)
