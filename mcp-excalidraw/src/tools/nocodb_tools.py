"""
Outils NocoDB pour schémas Excalidraw OPEPARTNER
Phase H.4.2 — MVP SIMPLE (sans missions)

Pattern de création validé par curl :
1. POST /records pour créer le schéma (mission_id reste NULL)
2. POST /links/{column_id}/records/{schema_id} pour lier au client
3. Rollback si l'étape 2 échoue (pas de schéma orphelin)
"""

import httpx
from typing import Optional, Dict, Any, List

# Import avec fallback pour exécution standalone
try:
    from ..clients.nocodb import NocoDBClient
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from clients.nocodb import NocoDBClient


# ID de la colonne relation "clients" dans schemas_excalidraw
# Récupéré via : curl ".../meta/tables/m7sm9k8fq50ugxe" | jq '.columns[] | select(.title == "clients")'
COLUMN_CLIENTS_RELATION = "cwihjc92fexrzfh"


async def find_or_create_client(
    nocodb: NocoDBClient,
    nom_entreprise: str,
    secteur_activite: Optional[str] = None,
    statut: str = "prospect"
) -> str:
    """
    Trouve ou crée un client (anti-doublon sur nom_entreprise)

    Réutilise la logique validée en H.3.3 (nocodb.py::upsert_client)

    Args:
        nocodb: Instance NocoDBClient connectée
        nom_entreprise: Nom du client (clé anti-doublon)
        secteur_activite: Secteur d'activité optionnel
        statut: Statut du client (défaut: "prospect")

    Returns:
        ID du client (UUID string)

    Example:
        async with NocoDBClient() as nocodb:
            client_id = await find_or_create_client(
                nocodb,
                nom_entreprise="Dupont SAS",
                secteur_activite="Industrie"
            )
            print(f"Client ID: {client_id}")
    """
    client_data = {
        "nom_entreprise": nom_entreprise,
        "statut": statut
    }

    if secteur_activite:
        client_data["secteur_activite"] = secteur_activite

    # Réutilise upsert_client de nocodb.py (anti-doublon validé H.3)
    client = await nocodb.upsert_client(client_data)

    return client["id"]


async def create_schema_linked_to_client(
    nocodb: NocoDBClient,
    client_id: str,
    excalidraw_id: str,
    document_title: str,
    document_type: str = "Schéma",
    edit_url: Optional[str] = None,
    preview_url: Optional[str] = None,
    confidentiel: bool = True,
    tags: Optional[List[str]] = None,
    notes_internal: Optional[str] = None
) -> str:
    """
    Crée un schéma Excalidraw lié à un client (SANS mission)

    Pattern validé par curl (2 étapes atomiques) :
    1. POST /records pour créer le schéma (mission_id reste NULL)
    2. POST /links/{column_id}/records/{schema_id} pour lier au client
    3. Si étape 2 échoue : supprime le schéma (rollback)

    Args:
        nocodb: Instance NocoDBClient connectée
        client_id: ID du client (UUID)
        excalidraw_id: ID unique Excalidraw (doit être unique)
        document_title: Titre du document
        document_type: Type de document (défaut: "Schéma")
        edit_url: URL d'édition Excalidraw
        preview_url: URL de preview Excalidraw
        confidentiel: Marquer comme confidentiel (défaut: True)
        tags: Tags optionnels (liste de strings)
        notes_internal: Notes internes

    Returns:
        ID du schéma créé (UUID string)

    Raises:
        httpx.HTTPStatusError: Si erreur API NocoDB
        RuntimeError: Si échec de liaison (avec rollback automatique)

    Example:
        async with NocoDBClient() as nocodb:
            schema_id = await create_schema_linked_to_client(
                nocodb,
                client_id="99bb995b-290b-45d3-b09d-0289ee2f3378",
                excalidraw_id="1779030793059",
                document_title="BMC — Dupont SAS",
                document_type="BMC_visuel",
                edit_url="https://excalidraw.opepartner.fr/#json=...",
                tags=["BMC", "stratégie"]
            )
            print(f"Schéma créé: {schema_id}")
    """
    # =========================================================================
    # ÉTAPE 1 : Créer le schéma (sans mission_id — reste NULL)
    # =========================================================================
    schema_data = {
        "excalidraw_id": excalidraw_id,
        "document_title": document_title,
        "document_type": document_type,
        "confidentiel": confidentiel
    }

    if edit_url:
        schema_data["edit_url"] = edit_url

    if preview_url:
        schema_data["preview_url"] = preview_url

    if tags:
        schema_data["tags"] = tags

    if notes_internal:
        schema_data["notes_internal"] = notes_internal

    try:
        # POST /api/v2/tables/{table_id}/records
        response = await nocodb._request(
            "POST",
            f"/api/v2/tables/{nocodb.TABLE_SCHEMAS_EXCALIDRAW}/records",
            json=schema_data
        )

        schema_id = response.get("id")
        if not schema_id:
            raise RuntimeError("API NocoDB n'a pas retourné d'ID pour le schéma créé")

    except httpx.HTTPStatusError as e:
        # Erreur création schéma (ex: excalidraw_id non unique, champ manquant)
        raise RuntimeError(
            f"Échec création schéma (étape 1/2): {e.response.status_code} — {e.response.text}"
        ) from e

    # =========================================================================
    # ÉTAPE 2 : Lier le schéma au client via l'endpoint de liaison
    # =========================================================================
    try:
        # POST /api/v2/tables/{table_id}/links/{column_id}/records/{record_id}
        # Body: ["client_uuid"]
        link_response = await nocodb._request(
            "POST",
            f"/api/v2/tables/{nocodb.TABLE_SCHEMAS_EXCALIDRAW}/links/{COLUMN_CLIENTS_RELATION}/records/{schema_id}",
            json=[client_id]
        )

        # Vérifier que la liaison a réussi (API retourne true ou l'objet lié)
        if link_response is not True and not isinstance(link_response, dict):
            raise RuntimeError(f"Liaison client échouée : API a retourné {link_response}")

    except (httpx.HTTPStatusError, RuntimeError) as e:
        # =====================================================================
        # ROLLBACK : Supprimer le schéma orphelin créé à l'étape 1
        # =====================================================================
        try:
            # Suppression via API NocoDB (format validé H.3 : delete_client)
            # DELETE /api/v2/tables/{table_id}/records body {"id": "..."}
            await nocodb._request(
                "DELETE",
                f"/api/v2/tables/{nocodb.TABLE_SCHEMAS_EXCALIDRAW}/records",
                json={"id": schema_id}
            )
        except Exception as cleanup_error:
            # Log l'erreur de cleanup mais remonte l'erreur principale
            print(f"⚠️  Erreur rollback schéma {schema_id}: {cleanup_error}")

        # Remonter l'erreur de liaison avec contexte
        raise RuntimeError(
            f"Échec liaison client (étape 2/2) — schéma {schema_id} supprimé (rollback) : {e}"
        ) from e

    return schema_id


async def get_schema_with_client(
    nocodb: NocoDBClient,
    schema_id: str
) -> Dict[str, Any]:
    """
    Récupère un schéma avec les infos du client lié

    Args:
        nocodb: Instance NocoDBClient connectée
        schema_id: ID du schéma (UUID)

    Returns:
        Dict avec les données du schéma (incluant client_id, mission_id)

    Example:
        schema = await get_schema_with_client(nocodb, schema_id)
        print(f"Client lié: {schema['client_id']}")
        print(f"Mission: {schema['mission_id']}")  # None pour MVP sans missions
    """
    response = await nocodb._request(
        "GET",
        f"/api/v2/tables/{nocodb.TABLE_SCHEMAS_EXCALIDRAW}/records/{schema_id}"
    )

    return response
