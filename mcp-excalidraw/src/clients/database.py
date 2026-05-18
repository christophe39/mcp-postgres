"""
Client PostgreSQL pour Excalidraw Storage Backend
Phase H.3 — Clients d'intégration

User PostgreSQL: mcp_excalidraw (moindre privilège)
Tables accessibles:
- keyv (SELECT, INSERT, UPDATE, DELETE)
- templates (SELECT only)
- utilisateurs (SELECT only)
- scenes_with_user (VIEW, SELECT only)

SÉCURITÉ:
- Pool de connexion avec limite
- Requêtes paramétrées OBLIGATOIRES (jamais f-string)
- Timeout sur les requêtes
- Gestion des erreurs explicite
"""

import asyncpg
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager


class DatabaseClient:
    """
    Client PostgreSQL asynchrone pour Excalidraw storage

    Usage:
        async with DatabaseClient() as db:
            result = await db.query("SELECT * FROM keyv WHERE key = $1", "SCENES:123")
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialise le client PostgreSQL

        Args:
            database_url: URL de connexion PostgreSQL (défaut: env DATABASE_URL)
                         Format: postgresql://user:pass@host:port/dbname
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL manquante (variable d'environnement ou paramètre)")

        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """
        Crée le pool de connexions PostgreSQL

        Pool config:
        - min_size: 2 (connexions toujours ouvertes)
        - max_size: 10 (limite de mcp_excalidraw user)
        - command_timeout: 30s
        """
        if self.pool is not None:
            return  # Déjà connecté

        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30.0,  # Timeout 30s par requête
        )

    async def disconnect(self) -> None:
        """Ferme le pool de connexions"""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def query(
        self,
        sql: str,
        *args: Any,
        timeout: Optional[float] = None
    ) -> List[asyncpg.Record]:
        """
        Exécute une requête SELECT

        Args:
            sql: Requête SQL avec placeholders $1, $2, etc. (JAMAIS f-string)
            *args: Valeurs pour les placeholders
            timeout: Timeout optionnel en secondes

        Returns:
            Liste de records (dictionnaires accessibles par clé ou index)

        Raises:
            RuntimeError: Si pool non initialisé
            asyncpg.PostgresError: Erreur PostgreSQL

        Example:
            rows = await db.query("SELECT * FROM keyv WHERE key = $1", "SCENES:123")
            for row in rows:
                print(row['key'], row['value'])
        """
        if self.pool is None:
            raise RuntimeError("Pool non initialisé — appelez connect() d'abord")

        async with self.pool.acquire() as conn:
            return await conn.fetch(sql, *args, timeout=timeout)

    async def execute(
        self,
        sql: str,
        *args: Any,
        timeout: Optional[float] = None
    ) -> str:
        """
        Exécute une requête INSERT/UPDATE/DELETE

        Args:
            sql: Requête SQL avec placeholders $1, $2, etc.
            *args: Valeurs pour les placeholders
            timeout: Timeout optionnel en secondes

        Returns:
            Status PostgreSQL (ex: "INSERT 0 1", "DELETE 1")

        Raises:
            RuntimeError: Si pool non initialisé
            asyncpg.PostgresError: Erreur PostgreSQL

        Example:
            status = await db.execute(
                "INSERT INTO keyv (key, value) VALUES ($1, $2)",
                "TEST:123",
                '{"data": "test"}'
            )
            print(status)  # "INSERT 0 1"
        """
        if self.pool is None:
            raise RuntimeError("Pool non initialisé — appelez connect() d'abord")

        async with self.pool.acquire() as conn:
            return await conn.execute(sql, *args, timeout=timeout)

    async def query_one(
        self,
        sql: str,
        *args: Any,
        timeout: Optional[float] = None
    ) -> Optional[asyncpg.Record]:
        """
        Exécute une requête qui retourne 0 ou 1 résultat

        Args:
            sql: Requête SQL
            *args: Valeurs pour les placeholders
            timeout: Timeout optionnel

        Returns:
            Record ou None si aucun résultat

        Example:
            row = await db.query_one("SELECT * FROM keyv WHERE key = $1", "SCENES:123")
            if row:
                print(row['value'])
        """
        if self.pool is None:
            raise RuntimeError("Pool non initialisé — appelez connect() d'abord")

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(sql, *args, timeout=timeout)

    async def query_value(
        self,
        sql: str,
        *args: Any,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Exécute une requête qui retourne une seule valeur

        Args:
            sql: Requête SQL
            *args: Valeurs pour les placeholders
            timeout: Timeout optionnel

        Returns:
            Valeur unique ou None

        Example:
            count = await db.query_value("SELECT count(*) FROM keyv")
            print(f"Total scènes: {count}")
        """
        if self.pool is None:
            raise RuntimeError("Pool non initialisé — appelez connect() d'abord")

        async with self.pool.acquire() as conn:
            return await conn.fetchval(sql, *args, timeout=timeout)

    async def __aenter__(self):
        """Context manager async: connexion automatique"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager async: déconnexion automatique"""
        await self.disconnect()


# =============================================================================
# HELPERS SPÉCIFIQUES KEYV
# =============================================================================

async def get_scene_from_keyv(
    db: DatabaseClient,
    scene_id: str
) -> Optional[Dict[str, Any]]:
    """
    Récupère une scène depuis keyv

    Args:
        db: Client database connecté
        scene_id: ID de scène (sans préfixe SCENES:)

    Returns:
        Dict avec 'key', 'value', 'created_at_tracked' ou None

    Example:
        scene = await get_scene_from_keyv(db, "2878434095682463")
        if scene:
            keyv_wrapper = scene['value']  # JSON {"value":":base64:..."}
    """
    key = f"SCENES:{scene_id}"
    row = await db.query_one(
        "SELECT key, value, created_at_tracked FROM keyv WHERE key = $1",
        key
    )

    if row is None:
        return None

    return {
        'key': row['key'],
        'value': row['value'],  # JSONB
        'created_at_tracked': row['created_at_tracked']
    }


async def insert_scene_to_keyv(
    db: DatabaseClient,
    scene_id: str,
    keyv_wrapper: str
) -> bool:
    """
    Insert une scène dans keyv

    Args:
        db: Client database connecté
        scene_id: ID de scène (sans préfixe SCENES:)
        keyv_wrapper: JSON wrapper {"value":":base64:...","expires":null}

    Returns:
        True si insertion réussie

    Raises:
        asyncpg.UniqueViolationError: Si clé existe déjà

    Example:
        success = await insert_scene_to_keyv(
            db,
            "1779030793059",
            '{"value":":base64:AQAAA...","expires":null}'
        )
    """
    key = f"SCENES:{scene_id}"

    status = await db.execute(
        """
        INSERT INTO keyv (key, value, created_at_tracked)
        VALUES ($1, $2::jsonb, NOW())
        """,
        key,
        keyv_wrapper
    )

    # Status format: "INSERT 0 1" (0 = OID, 1 = nb rows)
    return "INSERT" in status


async def delete_scene_from_keyv(
    db: DatabaseClient,
    scene_id: str
) -> bool:
    """
    Supprime une scène de keyv

    Args:
        db: Client database connecté
        scene_id: ID de scène (sans préfixe SCENES:)

    Returns:
        True si suppression réussie (1 ligne supprimée)

    Example:
        deleted = await delete_scene_from_keyv(db, "TEST-123")
        print(f"Scène supprimée: {deleted}")
    """
    key = f"SCENES:{scene_id}"

    status = await db.execute(
        "DELETE FROM keyv WHERE key = $1",
        key
    )

    # Status format: "DELETE 1" ou "DELETE 0"
    return "DELETE 1" in status
