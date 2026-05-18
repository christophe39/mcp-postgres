"""
Client Excalidraw Storage Backend
Phase H.3.2 — CRUD scènes avec chiffrement E2E

Réutilise:
- crypto.py (Phase H.2) : chiffrement/déchiffrement AES-128-GCM
- database.py (Phase H.3.1) : pool PostgreSQL avec mcp_excalidraw

Workflow:
1. create_scene() : JSON → chiffre → keyv → retourne (scene_id, jwk_k, url)
2. get_scene() : keyv → buffer → déchiffre → JSON
3. delete_scene() : supprime de keyv
4. list_scenes() : liste des IDs disponibles
"""

import sys
import os
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

# Import crypto.py (Phase H.2)
sys.path.insert(0, str(Path(__file__).parent.parent))
import crypto

# Import database client
from .database import (
    DatabaseClient,
    get_scene_from_keyv,
    insert_scene_to_keyv,
    delete_scene_from_keyv
)


class ExcalidrawClient:
    """
    Client Excalidraw Storage Backend

    Gère le cycle de vie complet des scènes:
    - Création avec chiffrement E2E
    - Lecture avec déchiffrement
    - Suppression
    - Listing

    Usage:
        async with ExcalidrawClient() as client:
            scene_id, jwk_k, url = await client.create_scene(scene_json)
            print(f"Scène créée: {url}")
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        frontend_base_url: Optional[str] = None
    ):
        """
        Initialise le client Excalidraw

        Args:
            database_url: URL PostgreSQL (défaut: env DATABASE_URL)
            frontend_base_url: URL frontend Excalidraw (défaut: env EXCALIDRAW_FRONTEND_URL)
                              Format: https://excalidraw.agnisolution.fr
        """
        self.db = DatabaseClient(database_url)

        self.frontend_base_url = frontend_base_url or os.getenv(
            "EXCALIDRAW_FRONTEND_URL",
            "https://excalidraw.agnisolution.fr"
        )

    async def connect(self) -> None:
        """Initialise la connexion database"""
        await self.db.connect()

    async def disconnect(self) -> None:
        """Ferme la connexion database"""
        await self.db.disconnect()

    async def create_scene(
        self,
        scene_json: str,
        scene_id: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Crée une scène Excalidraw chiffrée dans keyv

        Workflow:
        1. Génère encryption key (16 bytes)
        2. Compresse + chiffre le JSON (crypto.py)
        3. Crée wrapper keyv
        4. Insert dans PostgreSQL
        5. Retourne (scene_id, jwk_k, url)

        Args:
            scene_json: JSON Excalidraw (complet avec type, version, elements, appState, files)
            scene_id: ID optionnel (défaut: génération auto numérique pur)

        Returns:
            Tuple (scene_id, jwk_k, url_frontend)
            - scene_id: ID numérique pur (ex: "1779030793059")
            - jwk_k: Clé JWK base64url 22 chars (ex: "R0dHIsECVzcIVDztmUTNyw")
            - url_frontend: URL complète (ex: "https://excalidraw...//#json=ID,KEY")

        Raises:
            ValueError: Si scene_json invalide
            asyncpg.UniqueViolationError: Si scene_id existe déjà

        Example:
            scene = {"type": "excalidraw", "version": 2, ...}
            scene_id, jwk_k, url = await client.create_scene(json.dumps(scene))
            print(f"Scène créée: {url}")
        """
        # 1. Générer ID si non fourni
        if scene_id is None:
            scene_id = crypto.generate_scene_id()

        # 2. Générer clé et chiffrer
        encryption_key = crypto.generate_encryption_key()
        final_buffer, iv, jwk_k = crypto.compress_and_encrypt_scene(
            scene_json,
            encryption_key
        )

        # 3. Créer wrapper keyv
        keyv_wrapper = crypto.create_keyv_wrapper(final_buffer)

        # 4. Insert dans PostgreSQL
        success = await insert_scene_to_keyv(self.db, scene_id, keyv_wrapper)

        if not success:
            raise RuntimeError(f"Échec insertion scène {scene_id}")

        # 5. Construire URL frontend
        url = f"{self.frontend_base_url}/#json={scene_id},{jwk_k}"

        return scene_id, jwk_k, url

    async def get_scene(
        self,
        scene_id: str,
        jwk_k: str
    ) -> Optional[str]:
        """
        Récupère et déchiffre une scène depuis keyv

        Workflow:
        1. SELECT dans keyv
        2. Parse wrapper keyv
        3. Déchiffre + décompresse (crypto.py)
        4. Retourne JSON original

        Args:
            scene_id: ID de scène (sans préfixe SCENES:)
            jwk_k: Clé JWK base64url 22 chars

        Returns:
            JSON Excalidraw déchiffré ou None si scène inexistante

        Raises:
            ValueError: Si jwk_k invalide (longueur != 22)
            Exception: Si déchiffrement échoue (clé incorrecte, corruption)

        Example:
            scene_json = await client.get_scene("1779030793059", "R0dHIsECVzcIVDztmUTNyw")
            scene = json.loads(scene_json)
            print(f"Éléments: {len(scene['elements'])}")
        """
        # 1. Récupérer depuis keyv
        scene_data = await get_scene_from_keyv(self.db, scene_id)

        if scene_data is None:
            return None

        # 2. Parse wrapper keyv (JSONB → dict)
        # Note: asyncpg retourne déjà un dict pour les colonnes JSONB
        if isinstance(scene_data['value'], str):
            import json
            keyv_json = scene_data['value']
        else:
            # Déjà un dict
            import json
            keyv_json = json.dumps(scene_data['value'])

        # 3. Extraire buffer binaire
        final_buffer = crypto.parse_keyv_wrapper(keyv_json)

        # 4. Déchiffrer + décompresser
        scene_json = crypto.decrypt_and_decompress_scene(final_buffer, jwk_k)

        return scene_json

    async def delete_scene(self, scene_id: str) -> bool:
        """
        Supprime une scène de keyv

        Args:
            scene_id: ID de scène (sans préfixe SCENES:)

        Returns:
            True si suppression réussie

        Example:
            deleted = await client.delete_scene("1779030793059")
            print(f"Scène supprimée: {deleted}")
        """
        return await delete_scene_from_keyv(self.db, scene_id)

    async def list_scenes(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Liste les scènes disponibles dans keyv

        Note: Ne retourne QUE les métadonnées (pas le contenu déchiffré)
        car on n'a pas les clés JWK.

        Args:
            limit: Nombre max de scènes à retourner
            offset: Offset pour pagination

        Returns:
            Liste de dicts avec:
            - scene_id: ID sans préfixe SCENES:
            - key: Clé complète (avec SCENES:)
            - created_at: Timestamp création
            - size_bytes: Taille du buffer chiffré

        Example:
            scenes = await client.list_scenes(limit=10)
            for scene in scenes:
                print(f"{scene['scene_id']} — {scene['created_at']}")
        """
        rows = await self.db.query(
            """
            SELECT
                key,
                created_at_tracked,
                length(value::text) as size_bytes
            FROM keyv
            WHERE key LIKE 'SCENES:%'
            ORDER BY created_at_tracked DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset
        )

        scenes = []
        for row in rows:
            scene_id = row['key'].replace('SCENES:', '')
            scenes.append({
                'scene_id': scene_id,
                'key': row['key'],
                'created_at': row['created_at_tracked'],
                'size_bytes': row['size_bytes']
            })

        return scenes

    async def scene_exists(self, scene_id: str) -> bool:
        """
        Vérifie si une scène existe dans keyv

        Args:
            scene_id: ID de scène (sans préfixe SCENES:)

        Returns:
            True si scène existe

        Example:
            if await client.scene_exists("1779030793059"):
                print("Scène trouvée")
        """
        scene = await get_scene_from_keyv(self.db, scene_id)
        return scene is not None

    async def __aenter__(self):
        """Context manager async: connexion automatique"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager async: déconnexion automatique"""
        await self.disconnect()
