"""
Orchestration Excalidraw + NocoDB OPEPARTNER
Phase H.4.3 — MVP SIMPLE (sans missions, sans AFFiNE)

SCOPE STRICT : Relie Excalidraw + NocoDB UNIQUEMENT.
AFFiNE est géré séparément par MCP externe (affine-opepartner).

Séquence transactionnelle :
1. find_or_create_client → client_id
2. create_scene (chiffrée) → scene_id, jwk_k, url
3. create_schema_linked_to_client → schema_id
4. Retourner dict + affine_snippet (markdown pour AFFiNE)

Rollback :
- Si étape 2 échoue : rien à nettoyer (pas de scène créée)
- Si étape 3 échoue : supprimer scène Excalidraw orpheline
"""

import json
from typing import Optional, Dict, Any, List
import httpx

# Import avec fallback pour exécution standalone
try:
    from ..clients.nocodb import NocoDBClient
    from ..clients.excalidraw import ExcalidrawClient
    from .nocodb_tools import find_or_create_client, create_schema_linked_to_client
    from .scenes import scene_exists
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from clients.nocodb import NocoDBClient
    from clients.excalidraw import ExcalidrawClient
    from tools.nocodb_tools import find_or_create_client, create_schema_linked_to_client
    from tools.scenes import scene_exists


async def create_scene_orchestrated(
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

    Orchestration transactionnelle Excalidraw + NocoDB OPEPARTNER.
    AFFiNE n'est PAS géré ici (MCP externe affine-opepartner).

    Séquence :
    1. find_or_create_client(client_name) → client_id (anti-doublon)
    2. create_scene(scene_json) → scene_id, jwk_k, url (chiffrée E2E)
    3. create_schema_linked_to_client(...) → schema_id

    Rollback :
    - Si étape 2 échoue : rien à nettoyer (pas de scène créée)
    - Si étape 3 échoue : supprimer scène Excalidraw orpheline (delete_scene)

    Args:
        scene_json: JSON Excalidraw (elements, appState, files)
        client_name: Nom du client (clé anti-doublon)
        document_type: Type de document (ex: "BMC_visuel", "PESTEL")
        document_title: Titre du document
        secteur_activite: Secteur d'activité optionnel
        confidentiel: Marquer comme confidentiel (défaut: True)
        tags: Tags optionnels (liste de strings)
        notes_internal: Notes internes optionnelles

    Returns:
        Dict avec :
        - client_id: UUID du client
        - client_name: Nom du client
        - scene_id: ID Excalidraw
        - jwk_k: Clé de chiffrement JWK (base64url)
        - url: URL Excalidraw complète (edit)
        - preview_url: URL preview (sans clé)
        - schema_id: UUID de l'entrée Schemas_Excalidraw
        - affine_snippet: Markdown prêt à coller dans AFFiNE

    Raises:
        ValueError: Si paramètres invalides
        RuntimeError: Si erreur orchestration (avec rollback si nécessaire)

    Example:
        scene_json = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": [...],
            "appState": {...},
            "files": {}
        }

        result = await create_scene_orchestrated(
            scene_json=scene_json,
            client_name="Dupont SAS",
            document_type="BMC_visuel",
            document_title="BMC — Dupont SAS",
            secteur_activite="Industrie",
            tags=["BMC", "stratégie"]
        )

        print(f"Client: {result['client_id']}")
        print(f"Scène: {result['url']}")
        print(f"Schéma NocoDB: {result['schema_id']}")
        print(f"Snippet AFFiNE:\n{result['affine_snippet']}")
    """
    # Validation paramètres
    if not client_name or not client_name.strip():
        raise ValueError("client_name requis et non vide")

    if not document_type or not document_type.strip():
        raise ValueError("document_type requis et non vide")

    if not document_title or not document_title.strip():
        raise ValueError("document_title requis et non vide")

    if not scene_json or not isinstance(scene_json, dict):
        raise ValueError("scene_json doit être un dict non vide")

    client_name = client_name.strip()
    document_type = document_type.strip()
    document_title = document_title.strip()

    # Variables pour rollback
    scene_id = None
    client_id = None

    # Initialiser clients
    nocodb = NocoDBClient()
    excalidraw = ExcalidrawClient()

    await nocodb.connect()
    await excalidraw.connect()

    try:
        # =====================================================================
        # ÉTAPE 1 : Trouver ou créer client (anti-doublon)
        # =====================================================================
        client_id = await find_or_create_client(
            nocodb,
            nom_entreprise=client_name,
            secteur_activite=secteur_activite,
            statut="prospect"
        )

        # =====================================================================
        # ÉTAPE 2 : Créer scène Excalidraw chiffrée
        # =====================================================================
        try:
            # Convertir dict en JSON string et appeler directement le client
            scene_json_str = json.dumps(scene_json)
            scene_id, jwk_k, edit_url = await excalidraw.create_scene(scene_json_str)

            # Construire preview_url (sans clé)
            base_url = edit_url.split("#json=")[0] if "#json=" in edit_url else edit_url
            preview_url = f"{base_url}#json={scene_id}"

        except Exception as e:
            # Échec étape 2 : pas de scène créée, rien à rollback côté Excalidraw
            # Le client créé à l'étape 1 reste (légitime)
            raise RuntimeError(
                f"Échec création scène Excalidraw (étape 2/3) : {e}"
            ) from e

        # =====================================================================
        # ÉTAPE 3 : Créer entrée Schemas_Excalidraw liée au client
        # =====================================================================
        try:
            schema_id = await create_schema_linked_to_client(
                nocodb,
                client_id=client_id,
                excalidraw_id=scene_id,
                document_title=document_title,
                document_type=document_type,
                edit_url=edit_url,
                preview_url=preview_url,
                confidentiel=confidentiel,
                tags=tags,
                notes_internal=notes_internal
            )

        except Exception as e:
            # =====================================================================
            # ROLLBACK : Supprimer scène Excalidraw orpheline
            # =====================================================================
            if scene_id:
                try:
                    await excalidraw.delete_scene(scene_id)
                    print(f"⚠️  Rollback : scène Excalidraw {scene_id} supprimée après échec étape 3")
                except Exception as cleanup_error:
                    print(f"⚠️  Erreur rollback scène {scene_id} : {cleanup_error}")

            # Remonter l'erreur principale
            raise RuntimeError(
                f"Échec création schéma NocoDB (étape 3/3) — scène Excalidraw {scene_id} supprimée (rollback) : {e}"
            ) from e

        # =====================================================================
        # ÉTAPE 4 : Générer snippet AFFiNE (markdown)
        # =====================================================================
        affine_snippet = _generate_affine_snippet(
            document_title=document_title,
            document_type=document_type,
            edit_url=edit_url,
            preview_url=preview_url,
            confidentiel=confidentiel,
            tags=tags
        )

        # =====================================================================
        # RETOUR : Dict complet
        # =====================================================================
        return {
            "client_id": client_id,
            "client_name": client_name,
            "scene_id": scene_id,
            "jwk_k": jwk_k,
            "url": edit_url,
            "preview_url": preview_url,
            "schema_id": schema_id,
            "affine_snippet": affine_snippet
        }

    finally:
        # Déconnexion clients
        await nocodb.disconnect()
        await excalidraw.disconnect()


def _generate_affine_snippet(
    document_title: str,
    document_type: str,
    edit_url: str,
    preview_url: Optional[str] = None,
    confidentiel: bool = True,
    tags: Optional[List[str]] = None
) -> str:
    """
    Génère un snippet markdown prêt à coller dans AFFiNE

    Args:
        document_title: Titre du document
        document_type: Type de document
        edit_url: URL Excalidraw éditable
        preview_url: URL preview optionnelle
        confidentiel: Si confidentiel
        tags: Tags optionnels

    Returns:
        String markdown formaté

    Example:
        snippet = _generate_affine_snippet(
            document_title="BMC — Dupont SAS",
            document_type="BMC_visuel",
            edit_url="https://excalidraw.opepartner.fr/#json=...",
            confidentiel=True,
            tags=["BMC", "stratégie"]
        )
        # Résultat :
        # ## BMC — Dupont SAS
        # **Type** : BMC_visuel | **Confidentiel** : Oui
        # [🖊️ Éditer dans Excalidraw](https://excalidraw.opepartner.fr/#json=...)
        # _Tags : BMC, stratégie_
    """
    lines = []

    # Titre
    lines.append(f"## {document_title}")

    # Métadonnées
    conf_str = "Oui" if confidentiel else "Non"
    lines.append(f"**Type** : {document_type} | **Confidentiel** : {conf_str}")

    # Lien éditable
    lines.append(f"[🖊️ Éditer dans Excalidraw]({edit_url})")

    # Preview (optionnel)
    if preview_url:
        lines.append(f"[👁️ Voir preview]({preview_url})")

    # Tags (optionnel)
    if tags:
        tags_str = ", ".join(tags)
        lines.append(f"_Tags : {tags_str}_")

    return "\n".join(lines)
