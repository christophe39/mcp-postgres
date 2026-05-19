"""
Outils MCP pour manipulation de scènes Excalidraw
Phase H.4.1 — CRUD de base

Outils exposés à Claude :
- create_scene : crée scène chiffrée (retourne ID, clé, URL)
- get_scene : récupère et déchiffre une scène
- update_scene : modifie une scène existante
- list_scenes : liste des scènes disponibles
- delete_scene : suppression avec confirmation (RGPD)

Architecture : ces outils wrappent ExcalidrawClient (Phase H.3.2).
Orchestration NocoDB viendra en Phase H.4.3.
"""

import json
from typing import Optional, List, Dict, Any, Tuple
import sys
from pathlib import Path

# Import clients validés Phase H.3
sys.path.insert(0, str(Path(__file__).parent.parent))
from clients.excalidraw import ExcalidrawClient


async def create_scene(
    scene_json: str,
    scene_id: Optional[str] = None,
    database_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crée une scène Excalidraw chiffrée

    Outil MCP : crée une scène dans le backend Excalidraw avec chiffrement E2E.
    Retourne l'ID, la clé de déchiffrement, et l'URL complète.

    Args:
        scene_json: JSON Excalidraw complet (str)
                   Format: {"type":"excalidraw","version":2,"elements":[...],"appState":{...},"files":{}}
        scene_id: ID optionnel (défaut: génération automatique)
        database_url: URL PostgreSQL optionnelle (défaut: env DATABASE_URL)

    Returns:
        Dict avec:
        - scene_id: ID numérique de la scène (ex: "1779030793059")
        - jwk_k: Clé de déchiffrement base64url 22 chars (ex: "R0dHIsECVzcIVDztmUTNyw")
        - url: URL complète pour ouvrir dans Excalidraw
               Format: https://excalidraw.agnisolution.fr/#json={scene_id},{jwk_k}
        - size_bytes: Taille du JSON original

    Raises:
        ValueError: Si scene_json invalide (pas du JSON ou format incorrect)
        RuntimeError: Si échec de création

    Example:
        scene = {"type": "excalidraw", "version": 2, "elements": [...], ...}
        result = await create_scene(json.dumps(scene))
        print(f"Scène créée : {result['url']}")
        print(f"Clé à conserver : {result['jwk_k']}")
    """
    # Validation JSON
    try:
        scene_data = json.loads(scene_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"scene_json invalide : {e}")

    # Validation format Excalidraw minimal
    if not isinstance(scene_data, dict):
        raise ValueError("scene_json doit être un objet JSON")

    if scene_data.get("type") != "excalidraw":
        raise ValueError("scene_json.type doit être 'excalidraw'")

    if "elements" not in scene_data:
        raise ValueError("scene_json.elements requis")

    # Création via ExcalidrawClient
    async with ExcalidrawClient(database_url=database_url) as client:
        scene_id_created, jwk_k, url = await client.create_scene(
            scene_json,
            scene_id=scene_id
        )

    return {
        "scene_id": scene_id_created,
        "jwk_k": jwk_k,
        "url": url,
        "size_bytes": len(scene_json)
    }


async def get_scene(
    scene_id: str,
    jwk_k: str,
    database_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Récupère et déchiffre une scène Excalidraw

    Outil MCP : récupère une scène depuis le backend, la déchiffre,
    et retourne le JSON Excalidraw original.

    Args:
        scene_id: ID de scène (ex: "1779030793059")
        jwk_k: Clé de déchiffrement base64url 22 chars
        database_url: URL PostgreSQL optionnelle

    Returns:
        Dict avec:
        - scene_id: ID de la scène
        - scene_data: JSON Excalidraw déchiffré (dict)
        - size_bytes: Taille du JSON

    Raises:
        ValueError: Si scene_id ou jwk_k invalide
        Exception: Si scène inexistante ou déchiffrement échoue

    Example:
        result = await get_scene("1779030793059", "R0dHIsECVzcIVDztmUTNyw")
        scene = result['scene_data']
        print(f"Éléments : {len(scene['elements'])}")
    """
    if not scene_id:
        raise ValueError("scene_id requis")

    if not jwk_k or len(jwk_k) != 22:
        raise ValueError("jwk_k doit faire 22 caractères")

    async with ExcalidrawClient(database_url=database_url) as client:
        scene_json = await client.get_scene(scene_id, jwk_k)

    if scene_json is None:
        raise Exception(f"Scène {scene_id} introuvable")

    # Parser pour retourner le dict
    scene_data = json.loads(scene_json)

    return {
        "scene_id": scene_id,
        "scene_data": scene_data,
        "size_bytes": len(scene_json)
    }


async def update_scene(
    scene_id: str,
    jwk_k: str,
    scene_json: str,
    database_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Met à jour une scène existante (même ID, même clé, nouvel IV)

    Outil MCP : modifie le contenu d'une scène existante.
    Pratique AES-GCM correcte : réutilise la MÊME clé de chiffrement,
    génère un NOUVEL IV. L'URL #json=ID,clé reste IDENTIQUE.

    Comportement frontend : quand l'utilisateur "Save" une scène modifiée,
    le frontend garde la même clé (dans l'URL) mais rechiffre avec un nouvel IV.
    Ce comportement est reproduit ici.

    Args:
        scene_id: ID de scène à modifier
        jwk_k: Clé de déchiffrement (identifie la scène, prouve le droit de modifier)
        scene_json: Nouveau JSON Excalidraw complet
        database_url: URL PostgreSQL optionnelle

    Returns:
        Dict avec:
        - scene_id: ID de la scène (inchangé)
        - jwk_k: Clé (IDENTIQUE à l'entrée — URL stable)
        - url: URL complète (IDENTIQUE — liens existants restent valides)
        - size_bytes: Taille du nouveau JSON
        - updated: True

    Raises:
        ValueError: Si scene_json invalide
        Exception: Si scène inexistante ou clé incorrecte

    Example:
        # Récupérer la scène
        current = await get_scene(scene_id, jwk_k)
        original_url = f"https://excalidraw...//#json={scene_id},{jwk_k}"

        # Modifier
        scene = current['scene_data']
        scene['elements'].append({...})

        # Sauvegarder
        result = await update_scene(scene_id, jwk_k, json.dumps(scene))

        # L'URL reste identique
        assert result['url'] == original_url
        assert result['jwk_k'] == jwk_k
    """
    # Validation JSON
    try:
        scene_data = json.loads(scene_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"scene_json invalide : {e}")

    if not isinstance(scene_data, dict):
        raise ValueError("scene_json doit être un objet JSON")

    if scene_data.get("type") != "excalidraw":
        raise ValueError("scene_json.type doit être 'excalidraw'")

    # Import crypto pour conversion jwk_k → key_bytes
    import crypto as crypto_module

    async with ExcalidrawClient(database_url=database_url) as client:
        # Vérifier que la scène existe et que la clé est correcte
        existing = await client.get_scene(scene_id, jwk_k)

        if existing is None:
            raise Exception(f"Scène {scene_id} introuvable ou clé incorrecte")

        # Convertir jwk_k en key_bytes pour réutiliser la MÊME clé
        encryption_key = crypto_module.jwk_k_to_key_bytes(jwk_k)

        # Supprimer l'ancienne version
        deleted = await client.delete_scene(scene_id)
        if not deleted:
            raise RuntimeError(f"Échec suppression ancienne version {scene_id}")

        # Créer la nouvelle version avec le MÊME ID et la MÊME clé
        # (nouvel IV généré automatiquement par compress_and_encrypt_scene)
        scene_id_new, jwk_k_new, url = await client.create_scene(
            scene_json,
            scene_id=scene_id,
            encryption_key=encryption_key
        )

    # Vérifier que l'ID et la clé n'ont PAS changé
    if scene_id_new != scene_id:
        raise RuntimeError(f"ID changé après update : {scene_id} → {scene_id_new}")

    if jwk_k_new != jwk_k:
        raise RuntimeError(
            f"Clé changée après update (BUG) : {jwk_k} → {jwk_k_new}. "
            f"La clé doit rester identique pour que les liens existants fonctionnent."
        )

    return {
        "scene_id": scene_id,
        "jwk_k": jwk_k,  # IDENTIQUE à l'entrée
        "url": url,
        "size_bytes": len(scene_json),
        "updated": True
    }


async def list_scenes(
    limit: int = 100,
    offset: int = 0,
    database_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Liste les scènes disponibles

    Outil MCP : liste les métadonnées des scènes stockées.
    Ne retourne PAS le contenu (car les clés ne sont pas connues).

    Args:
        limit: Nombre max de scènes à retourner (défaut: 100)
        offset: Offset pour pagination (défaut: 0)
        database_url: URL PostgreSQL optionnelle

    Returns:
        Dict avec:
        - scenes: Liste de dicts (scene_id, created_at, size_bytes)
        - total: Nombre total de scènes retournées
        - limit: Limite appliquée
        - offset: Offset appliqué

    Example:
        result = await list_scenes(limit=10)
        for scene in result['scenes']:
            print(f"{scene['scene_id']} — {scene['created_at']}")
    """
    if limit < 1 or limit > 1000:
        raise ValueError("limit doit être entre 1 et 1000")

    if offset < 0:
        raise ValueError("offset doit être >= 0")

    async with ExcalidrawClient(database_url=database_url) as client:
        scenes = await client.list_scenes(limit=limit, offset=offset)

    return {
        "scenes": scenes,
        "total": len(scenes),
        "limit": limit,
        "offset": offset
    }


async def delete_scene(
    scene_id: str,
    confirm: bool = False,
    database_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Supprime une scène (RGPD droit à l'oubli)

    Outil MCP : suppression définitive d'une scène.
    Requiert confirmation explicite (confirm=True) pour éviter les accidents.

    ATTENTION : Cette opération est IRRÉVERSIBLE.

    Args:
        scene_id: ID de scène à supprimer
        confirm: Doit être True pour confirmer la suppression
        database_url: URL PostgreSQL optionnelle

    Returns:
        Dict avec:
        - scene_id: ID de la scène supprimée
        - deleted: True si suppression réussie

    Raises:
        ValueError: Si confirm != True
        RuntimeError: Si suppression échoue

    Example:
        # INCORRECT (refusé)
        await delete_scene(scene_id)  # ValueError

        # CORRECT
        result = await delete_scene(scene_id, confirm=True)
        print(f"Scène {result['scene_id']} supprimée")
    """
    if not confirm:
        raise ValueError(
            "Suppression refusée : confirm=True requis pour confirmer. "
            "Cette opération est IRRÉVERSIBLE (RGPD droit à l'oubli)."
        )

    if not scene_id:
        raise ValueError("scene_id requis")

    async with ExcalidrawClient(database_url=database_url) as client:
        # Vérifier que la scène existe
        exists = await client.scene_exists(scene_id)
        if not exists:
            raise Exception(f"Scène {scene_id} introuvable")

        # Supprimer
        deleted = await client.delete_scene(scene_id)

        if not deleted:
            raise RuntimeError(f"Échec suppression scène {scene_id}")

        # Double-check
        still_exists = await client.scene_exists(scene_id)
        if still_exists:
            raise RuntimeError(
                f"Scène {scene_id} toujours présente après suppression"
            )

    return {
        "scene_id": scene_id,
        "deleted": True
    }


async def scene_exists(
    client: ExcalidrawClient,
    scene_id: str
) -> bool:
    """
    Vérifie si une scène existe dans Excalidraw

    Args:
        client: Instance ExcalidrawClient connectée
        scene_id: ID de la scène à vérifier

    Returns:
        True si la scène existe, False sinon

    Example:
        async with ExcalidrawClient() as client:
            exists = await scene_exists(client, "1779030793059")
            print(f"Scène existe : {exists}")
    """
    return await client.scene_exists(scene_id)
