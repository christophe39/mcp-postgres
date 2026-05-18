"""
Client NocoDB pour base OPEPARTNER
Phase H.3.3 — API NocoDB

Base: OPEPARTNER (ID: boexlzlohgueed1)
Tables principales:
- Clients
- Missions
- Schemas_Excalidraw
- Business_Model_Canvas
- SWOT, PESTEL, etc.

SÉCURITÉ:
- Token API dans variable d'environnement
- Requêtes HTTPS uniquement
- Timeout sur les requêtes
"""

import httpx
import os
from typing import Optional, List, Dict, Any


class NocoDBClient:
    """
    Client NocoDB asynchrone pour base OPEPARTNER

    Usage:
        async with NocoDBClient() as client:
            clients = await client.list_clients()
            for client_data in clients:
                print(client_data['nom_entreprise'])
    """

    # Table IDs réels base OPEPARTNER (p8qmnd5s0q9mtww)
    # Récupérés via: curl "https://nocodb.../api/v2/meta/bases/p8qmnd5s0q9mtww/tables"
    TABLE_CLIENTS = "m8r3u3f1f60wgdq"
    TABLE_SCHEMAS_EXCALIDRAW = "m6ww89ejz5f3wqk"
    TABLE_MISSIONS = "mq4dx42jmnkmcpo"
    TABLE_BUSINESS_MODEL_CANVAS = "mlwgq2hqva3hq81"
    TABLE_SWOT = "mfhynay6n0eo48h"
    TABLE_PESTEL = "mtdr4j3vyco36k7"

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        base_id: str = "p8qmnd5s0q9mtww"  # Base OPEPARTNER
    ):
        """
        Initialise le client NocoDB

        Args:
            base_url: URL NocoDB (défaut: env NOCODB_URL)
                     Format: https://nocodb.agnisolution.fr
            token: Token API (défaut: env NOCODB_TOKEN)
            base_id: ID de base NocoDB (défaut: OPEPARTNER p8qmnd5s0q9mtww)
        """
        self.base_url = (base_url or os.getenv("NOCODB_URL", "")).rstrip('/')
        self.token = token or os.getenv("NOCODB_TOKEN")
        self.base_id = base_id

        if not self.base_url:
            raise ValueError("NOCODB_URL manquante")
        if not self.token:
            raise ValueError("NOCODB_TOKEN manquante")

        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Initialise le client HTTP"""
        if self.client is not None:
            return

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "xc-token": self.token,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    async def disconnect(self) -> None:
        """Ferme le client HTTP"""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Effectue une requête HTTP vers l'API NocoDB

        Args:
            method: Méthode HTTP (GET, POST, PATCH, DELETE)
            path: Chemin API (ex: /api/v2/tables/Clients/records)
            **kwargs: Arguments httpx (json, params, etc.)

        Returns:
            Réponse JSON

        Raises:
            httpx.HTTPStatusError: Si erreur HTTP
        """
        if self.client is None:
            raise RuntimeError("Client non initialisé — appelez connect() d'abord")

        response = await self.client.request(method, path, **kwargs)
        response.raise_for_status()

        return response.json()

    # =========================================================================
    # TABLE CLIENTS
    # =========================================================================

    async def list_clients(
        self,
        limit: int = 100,
        offset: int = 0,
        where: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Liste les clients de la table Clients

        Args:
            limit: Nombre max de résultats
            offset: Offset pour pagination
            where: Condition WHERE optionnelle (format NocoDB)
                  Exemple: "(nom_entreprise,like,%Dupont%)"

        Returns:
            Liste de clients (dicts)

        Example:
            clients = await nocodb.list_clients(limit=10)
            for client in clients:
                print(f"{client['nom_entreprise']} — {client['statut']}")
        """
        params = {
            "limit": limit,
            "offset": offset
        }

        if where:
            params["where"] = where

        response = await self._request(
            "GET",
            f"/api/v2/tables/{self.TABLE_CLIENTS}/records",
            params=params
        )

        # Format NocoDB v2: {"list": [...], "pageInfo": {...}}
        return response.get("list", [])

    async def get_client(self, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un client par son ID

        Args:
            client_id: ID NocoDB du client

        Returns:
            Client ou None si inexistant

        Example:
            client = await nocodb.get_client(42)
            if client:
                print(client['nom_entreprise'])
        """
        try:
            response = await self._request(
                "GET",
                f"/api/v2/tables/{self.TABLE_CLIENTS}/records/{client_id}"
            )
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un nouveau client

        Args:
            client_data: Données du client
                Champs requis: nom_entreprise, statut
                Champs optionnels: raison_sociale, SIREN, email, etc.

        Returns:
            Client créé avec son ID

        Raises:
            httpx.HTTPStatusError: Si erreur API (champ manquant, etc.)

        Example:
            client = await nocodb.create_client({
                "nom_entreprise": "Dupont SAS",
                "statut": "Prospect",
                "raison_sociale": "Dupont Société par Actions Simplifiée",
                "email": "contact@dupont.fr"
            })
            print(f"Client créé: {client['id']}")
        """
        response = await self._request(
            "POST",
            f"/api/v2/tables/{self.TABLE_CLIENTS}/records",
            json=client_data
        )

        return response

    async def update_client(
        self,
        client_id: int,
        client_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Met à jour un client existant

        Args:
            client_id: ID NocoDB du client
            client_data: Champs à mettre à jour (PATCH)

        Returns:
            Client mis à jour

        Example:
            updated = await nocodb.update_client(42, {"statut": "Client actif"})
        """
        response = await self._request(
            "PATCH",
            f"/api/v2/tables/{self.TABLE_CLIENTS}/records",
            json={
                "Id": client_id,
                **client_data
            }
        )

        return response

    async def delete_client(self, client_id: int) -> bool:
        """
        Supprime un client

        Args:
            client_id: ID NocoDB du client

        Returns:
            True si suppression réussie

        Example:
            deleted = await nocodb.delete_client(42)
            print(f"Client supprimé: {deleted}")
        """
        try:
            response = await self._request(
                "DELETE",
                f"/api/v2/tables/{self.TABLE_CLIENTS}/records",
                json={"id": client_id}
            )
            # Succès si retourne {"id": "..."}
            return response.get("id") == client_id
        except httpx.HTTPStatusError:
            return False

    async def find_client_by_name(self, nom_entreprise: str) -> Optional[Dict[str, Any]]:
        """
        Recherche un client par nom exact

        Args:
            nom_entreprise: Nom du client (exact)

        Returns:
            Premier client trouvé ou None

        Example:
            client = await nocodb.find_client_by_name("Dupont SAS")
            if client:
                print(f"Client trouvé: {client['id']}")
        """
        # WHERE clause: (nom_entreprise,eq,Dupont SAS)
        clients = await self.list_clients(
            limit=1,
            where=f"(nom_entreprise,eq,{nom_entreprise})"
        )

        return clients[0] if clients else None

    # =========================================================================
    # TABLE SCHEMAS_EXCALIDRAW
    # =========================================================================

    async def create_schema_excalidraw(
        self,
        schema_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crée une entrée dans Schemas_Excalidraw

        Args:
            schema_data: Données du schéma
                Champs requis: excalidraw_id, document_type, document_title
                Champs optionnels: client_id, mission_id, edit_url, preview_url,
                                  affine_doc_id, confidentiel, tags, notes_internal

        Returns:
            Schéma créé avec son ID

        Example:
            schema = await nocodb.create_schema_excalidraw({
                "excalidraw_id": "1779030793059",
                "document_type": "BMC_visuel",
                "document_title": "BMC — Dupont SAS",
                "client_id": 42,
                "edit_url": "https://excalidraw...//#json=...",
                "confidentiel": True
            })
        """
        response = await self._request(
            "POST",
            f"/api/v2/tables/{self.TABLE_SCHEMAS_EXCALIDRAW}/records",
            json=schema_data
        )

        return response

    async def list_schemas_excalidraw(
        self,
        client_id: Optional[int] = None,
        mission_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Liste les schémas Excalidraw

        Args:
            client_id: Filtrer par client (optionnel)
            mission_id: Filtrer par mission (optionnel)
            limit: Nombre max de résultats

        Returns:
            Liste de schémas

        Example:
            schemas = await nocodb.list_schemas_excalidraw(client_id=42)
            for schema in schemas:
                print(f"{schema['document_title']} — {schema['document_type']}")
        """
        where_clauses = []

        if client_id is not None:
            where_clauses.append(f"(client_id,eq,{client_id})")

        if mission_id is not None:
            where_clauses.append(f"(mission_id,eq,{mission_id})")

        where = "~and".join(where_clauses) if where_clauses else None

        response = await self._request(
            "GET",
            f"/api/v2/tables/{self.TABLE_SCHEMAS_EXCALIDRAW}/records",
            params={
                "limit": limit,
                "where": where
            } if where else {"limit": limit}
        )

        return response.get("list", [])

    # =========================================================================
    # HELPERS GÉNÉRIQUES
    # =========================================================================

    async def upsert_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée ou retrouve un client (upsert par nom_entreprise)

        Logique:
        1. Cherche client existant par nom_entreprise
        2. Si trouvé, retourne le client existant
        3. Sinon, crée un nouveau client

        Args:
            client_data: Données du client (doit contenir nom_entreprise)

        Returns:
            Client existant ou nouveau client créé

        Example:
            client = await nocodb.upsert_client({
                "nom_entreprise": "Dupont SAS",
                "statut": "Prospect"
            })
            print(f"Client ID: {client['id']}")
        """
        nom_entreprise = client_data.get("nom_entreprise")
        if not nom_entreprise:
            raise ValueError("nom_entreprise requis pour upsert")

        # Chercher client existant
        existing = await self.find_client_by_name(nom_entreprise)

        if existing:
            return existing

        # Créer nouveau client
        return await self.create_client(client_data)

    async def __aenter__(self):
        """Context manager async: connexion automatique"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager async: déconnexion automatique"""
        await self.disconnect()
