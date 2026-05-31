"""
MCP PostgreSQL - AGNI
Serveur MCP pour accès direct aux bases PostgreSQL du VPS Hostinger
"""

import os
import asyncio
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastmcp import FastMCP, Context
from fastmcp.auth import OIDCProxy


# Configuration depuis environnement
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "69.62.110.207")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "agni_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DATABASES = os.getenv("POSTGRES_DATABASES", "opepartner,calocalc_inscription,db_agni,nocodb_db").split(",")

# Configuration OIDC
OIDC_CONFIG_URL = os.getenv("OIDC_CONFIG_URL", "https://keycloak.agnisolution.fr/realms/mcp/.well-known/openid-configuration")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "mcp-postgres")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "https://mcp-postgres.agnisolution.fr")
REDIS_URL = os.getenv("REDIS_URL", "")
JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY", "")
FERNET_SECRET = os.getenv("FERNET_SECRET", "")

# Pool de connexions PostgreSQL (un pool par database)
connection_pools: Dict[str, asyncpg.Pool] = {}


# Initialisation FastMCP avec OIDCProxy
mcp = FastMCP(
    "MCP PostgreSQL - AGNI",
    version="0.1.0",
    dependencies=["asyncpg>=0.30.0", "fastmcp>=3.3.1"]
)


async def get_pool(database: str) -> asyncpg.Pool:
    """Obtient ou crée un pool de connexions pour une database."""
    if database not in connection_pools:
        if database not in POSTGRES_DATABASES:
            raise ValueError(f"Database '{database}' non autorisée. Bases disponibles : {', '.join(POSTGRES_DATABASES)}")

        connection_pools[database] = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=database,
            min_size=1,
            max_size=5,
            command_timeout=30.0
        )

    return connection_pools[database]


@mcp.tool()
async def list_databases() -> List[str]:
    """
    Liste toutes les bases de données PostgreSQL accessibles.

    Returns:
        Liste des noms de bases de données
    """
    return POSTGRES_DATABASES


@mcp.tool()
async def list_tables(database: str) -> List[Dict[str, Any]]:
    """
    Liste toutes les tables d'une base de données.

    Args:
        database: Nom de la base de données

    Returns:
        Liste des tables avec leur schéma, nom et type
    """
    pool = await get_pool(database)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                schemaname AS schema,
                tablename AS name,
                'table' AS type
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')

            UNION ALL

            SELECT
                schemaname AS schema,
                viewname AS name,
                'view' AS type
            FROM pg_views
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')

            ORDER BY schema, name;
        """)

        return [dict(row) for row in rows]


@mcp.tool()
async def get_schema(database: str, table: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtient le schéma complet d'une table (colonnes, types, contraintes, index).
    Si table est None, retourne le schéma de toutes les tables.

    Args:
        database: Nom de la base de données
        table: Nom de la table (optionnel)

    Returns:
        Liste des colonnes avec leurs propriétés
    """
    pool = await get_pool(database)

    async with pool.acquire() as conn:
        if table:
            where_clause = "AND c.table_name = $1"
            params = [table]
        else:
            where_clause = ""
            params = []

        rows = await conn.fetch(f"""
            SELECT
                c.table_schema AS schema,
                c.table_name AS table,
                c.column_name AS column,
                c.data_type AS type,
                c.is_nullable AS nullable,
                c.column_default AS default_value,
                c.character_maximum_length AS max_length
            FROM information_schema.columns c
            WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
                {where_clause}
            ORDER BY c.table_name, c.ordinal_position;
        """, *params)

        return [dict(row) for row in rows]


@mcp.tool()
async def query(database: str, sql: str) -> List[Dict[str, Any]]:
    """
    Exécute une requête SELECT en lecture seule.

    Args:
        database: Nom de la base de données
        sql: Requête SQL (SELECT uniquement)

    Returns:
        Résultats de la requête
    """
    # Validation : uniquement SELECT
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Seules les requêtes SELECT sont autorisées avec cet outil. Utilisez 'execute' pour les autres opérations.")

    pool = await get_pool(database)

    async with pool.acquire() as conn:
        # Exécute en transaction read-only
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(sql)
            return [dict(row) for row in rows]


@mcp.tool()
async def get_table_stats(database: str, table: str) -> Dict[str, Any]:
    """
    Obtient les statistiques d'une table (nombre de lignes, taille, dernière modification).

    Args:
        database: Nom de la base de données
        table: Nom de la table

    Returns:
        Statistiques de la table
    """
    pool = await get_pool(database)

    async with pool.acquire() as conn:
        # Nombre de lignes
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table};")

        # Taille de la table
        size_query = """
            SELECT
                pg_size_pretty(pg_total_relation_size($1)) AS total_size,
                pg_size_pretty(pg_relation_size($1)) AS data_size,
                pg_size_pretty(pg_indexes_size($1)) AS indexes_size
        """
        sizes = await conn.fetchrow(size_query, table)

        return {
            "table": table,
            "row_count": count,
            "total_size": sizes["total_size"],
            "data_size": sizes["data_size"],
            "indexes_size": sizes["indexes_size"],
            "timestamp": datetime.utcnow().isoformat()
        }


# TODO Phase 2 : execute(), backup_database(), restore_database(), create_database(), drop_database()
# TODO Phase 3 : create_opepartner_tables(), migrate_database()


async def cleanup():
    """Ferme tous les pools de connexions."""
    for pool in connection_pools.values():
        await pool.close()


if __name__ == "__main__":
    import uvicorn

    # Configuration OIDCProxy si credentials présents
    if all([OIDC_CLIENT_SECRET, REDIS_URL, JWT_SIGNING_KEY, FERNET_SECRET]):
        print("🔐 Démarrage avec OIDCProxy (auth OIDC)")
        app = OIDCProxy(
            mcp,
            oidc_config_url=OIDC_CONFIG_URL,
            client_id=OIDC_CLIENT_ID,
            client_secret=OIDC_CLIENT_SECRET,
            base_url=MCP_BASE_URL,
            redis_url=REDIS_URL,
            jwt_signing_key=JWT_SIGNING_KEY,
            fernet_secret=FERNET_SECRET
        )
    else:
        print("⚠️  Démarrage SANS auth (mode dev local)")
        app = mcp

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info"
        )
    finally:
        asyncio.run(cleanup())
