"""
MCP PostgreSQL OPEPARTNER - Accès lecture/écriture aux bases du VPS Hostinger
Écriture protégée par rôle Keycloak 'mcp_write'
"""
import os
import sys
import re
import hashlib
import base64
import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from contextlib import asynccontextmanager

import asyncpg
from fastmcp import FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp-postgres")

# ========== Configuration depuis environnement ==========

# Auth OIDC
CONFIG_URL    = os.environ["OIDC_CONFIG_URL"]
CLIENT_ID     = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
BASE_URL      = os.environ["MCP_BASE_URL"]
REDIS_URL     = os.environ["REDIS_URL"]
JWT_KEY       = os.environ["JWT_SIGNING_KEY"]
FERNET_SECRET = os.environ["FERNET_SECRET"]

# PostgreSQL - Lecture seule (rôle mcp_ro)
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_WHITELIST = [db.strip() for db in os.environ["DB_WHITELIST"].split(",")]
DB_DEFAULT = os.environ.get("DB_DEFAULT", "db_agni")

# PostgreSQL - Écriture (rôle mcp_rw)
DB_RW_USER = os.environ.get("DB_RW_USER", "")
DB_RW_PASSWORD = os.environ.get("DB_RW_PASSWORD", "")

# Limites de sécurité
QUERY_MAX_ROWS_DEFAULT = int(os.environ.get("QUERY_MAX_ROWS_DEFAULT", "100"))
QUERY_MAX_ROWS_HARD = int(os.environ.get("QUERY_MAX_ROWS_HARD", "1000"))
STATEMENT_TIMEOUT_MS = int(os.environ.get("STATEMENT_TIMEOUT_MS", "5000"))

logger.info(f"Configuration chargée : {len(DB_WHITELIST)} bases autorisées, timeout {STATEMENT_TIMEOUT_MS}ms")

# ========== Setup Auth OIDCProxy ==========

def derive_fernet_key(s: str) -> bytes:
    """Dérive une clé Fernet 32-byte URL-safe depuis une string."""
    return base64.urlsafe_b64encode(hashlib.sha256(s.encode()).digest())

fernet = Fernet(derive_fernet_key(FERNET_SECRET))
store = RedisStore(url=REDIS_URL)
encrypted_store = FernetEncryptionWrapper(
    key_value=store,
    fernet=fernet,
    raise_on_decryption_error=False,
)

auth = OIDCProxy(
    config_url=CONFIG_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    audience=BASE_URL,
    base_url=BASE_URL,
    redirect_path="/auth/callback",
    required_scopes=["openid", "mcp:execute"],
    jwt_signing_key=JWT_KEY,
    client_storage=encrypted_store,
)

# ========== Connection Pools PostgreSQL ==========

# Dictionnaire de pools lecture seule : {database: asyncpg.Pool}
_pools: Dict[str, asyncpg.Pool] = {}

# Dictionnaire de pools lecture-écriture : {database: asyncpg.Pool}
_rw_pools: Dict[str, asyncpg.Pool] = {}

async def get_pool(database: str) -> asyncpg.Pool:
    """
    Obtient ou crée un pool de connexions LECTURE SEULE pour une base de données.
    Refuse si la base n'est pas dans la whitelist.
    """
    if database not in DB_WHITELIST:
        raise ValueError(
            f"Base de données '{database}' non autorisée. "
            f"Bases disponibles : {', '.join(DB_WHITELIST)}"
        )

    if database not in _pools:
        logger.info(f"Création du pool RO pour la base '{database}'")
        _pools[database] = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=database,
            min_size=1,
            max_size=5,
            command_timeout=30.0,
            server_settings={
                "statement_timeout": str(STATEMENT_TIMEOUT_MS),
                "default_transaction_read_only": "on"
            }
        )

    return _pools[database]

async def get_rw_pool(database: str) -> asyncpg.Pool:
    """
    Obtient ou crée un pool de connexions LECTURE-ÉCRITURE pour une base de données.
    Refuse si la base n'est pas dans la whitelist.
    """
    if database not in DB_WHITELIST:
        raise ValueError(
            f"Base de données '{database}' non autorisée. "
            f"Bases disponibles : {', '.join(DB_WHITELIST)}"
        )

    if not DB_RW_USER or not DB_RW_PASSWORD:
        raise RuntimeError(
            "Credentials d'écriture non configurés (DB_RW_USER/DB_RW_PASSWORD manquants)"
        )

    if database not in _rw_pools:
        logger.info(f"Création du pool RW pour la base '{database}'")
        _rw_pools[database] = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_RW_USER,
            password=DB_RW_PASSWORD,
            database=database,
            min_size=1,
            max_size=5,
            command_timeout=30.0,
            server_settings={
                "statement_timeout": str(STATEMENT_TIMEOUT_MS)
                # PAS de default_transaction_read_only (c'est le pool d'écriture)
            }
        )

    return _rw_pools[database]

async def cleanup_pools():
    """Ferme tous les pools de connexions (lecture + écriture)."""
    logger.info("Fermeture des pools de connexions...")

    # Pools lecture seule
    for db, pool in _pools.items():
        await pool.close()
        logger.info(f"Pool RO fermé pour '{db}'")
    _pools.clear()

    # Pools lecture-écriture
    for db, pool in _rw_pools.items():
        await pool.close()
        logger.info(f"Pool RW fermé pour '{db}'")
    _rw_pools.clear()

# ========== Lifespan FastMCP ==========

@asynccontextmanager
async def lifespan(app):
    """Gère le cycle de vie de l'application (startup/shutdown)."""
    logger.info("Démarrage du MCP PostgreSQL")
    yield
    await cleanup_pools()
    logger.info("Arrêt du MCP PostgreSQL")

# ========== FastMCP Instance ==========

mcp = FastMCP("MCP Postgres OPEPARTNER", auth=auth, lifespan=lifespan)

# ========== Helpers ==========

def get_user_id() -> str:
    """Récupère l'identité de l'utilisateur depuis le token OIDC."""
    try:
        token = get_access_token()
        return token.claims.get("sub", "anonyme")
    except:
        return "anonyme"

def has_write_access() -> bool:
    """
    Vérifie si l'utilisateur possède le rôle Keycloak 'mcp_write'.

    Returns:
        True si le rôle est présent, False sinon
    """
    try:
        token = get_access_token()
        realm_access = token.claims.get("realm_access", {})
        roles = realm_access.get("roles", [])
        return "mcp_write" in roles
    except:
        return False

def serialize_value(val: Any) -> Any:
    """Convertit une valeur PostgreSQL en type JSON-sérialisable."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    elif isinstance(val, Decimal):
        return str(val)
    elif isinstance(val, bytes):
        return val.hex()
    return val

def serialize_row(row: asyncpg.Record) -> Dict[str, Any]:
    """Convertit une ligne asyncpg en dictionnaire JSON-sérialisable."""
    return {key: serialize_value(val) for key, val in row.items()}

# ========== Outils MCP ==========

@mcp.tool
async def whoami() -> Dict[str, Any]:
    """Renvoie l'identité de l'utilisateur authentifié et ses permissions."""
    user_id = get_user_id()
    write_access = has_write_access()
    logger.info(f"[whoami] Utilisateur: {user_id}, écriture: {write_access}")
    return {
        "user_id": user_id,
        "write_access": write_access,
        "message": f"MCP Postgres OPEPARTNER - {'Lecture/Écriture' if write_access else 'Lecture seule'}"
    }

@mcp.tool
async def list_databases() -> List[str]:
    """
    Liste les bases de données PostgreSQL accessibles.

    Returns:
        Liste des noms de bases autorisées
    """
    user_id = get_user_id()
    logger.info(f"[list_databases] Utilisateur: {user_id}")
    return DB_WHITELIST

@mcp.tool
async def list_schemas(database: str) -> List[str]:
    """
    Liste les schémas d'une base de données (hors schémas système).

    Args:
        database: Nom de la base de données

    Returns:
        Liste des noms de schémas
    """
    user_id = get_user_id()
    logger.info(f"[list_schemas] Utilisateur: {user_id}, base: {database}")

    pool = await get_pool(database)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
              AND schema_name NOT LIKE 'pg_%'
            ORDER BY schema_name;
        """)

    return [row['schema_name'] for row in rows]

@mcp.tool
async def list_tables(database: str, schema: str = "public") -> List[Dict[str, str]]:
    """
    Liste les tables et vues d'un schéma.

    Args:
        database: Nom de la base de données
        schema: Nom du schéma (défaut: "public")

    Returns:
        Liste des tables/vues avec leur type
    """
    user_id = get_user_id()
    logger.info(f"[list_tables] Utilisateur: {user_id}, base: {database}, schéma: {schema}")

    pool = await get_pool(database)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = $1
            ORDER BY table_name;
        """, schema)

    return [{"name": row['table_name'], "type": row['table_type']} for row in rows]

@mcp.tool
async def describe_table(
    database: str,
    schema: str,
    table: str
) -> Dict[str, Any]:
    """
    Décrit la structure d'une table (colonnes, types, contraintes).

    Args:
        database: Nom de la base de données
        schema: Nom du schéma
        table: Nom de la table

    Returns:
        Dictionnaire avec colonnes et clés primaires
    """
    user_id = get_user_id()
    logger.info(f"[describe_table] Utilisateur: {user_id}, base: {database}, table: {schema}.{table}")

    pool = await get_pool(database)

    async with pool.acquire() as conn:
        # Colonnes
        cols = await conn.fetch("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position;
        """, schema, table)

        if not cols:
            raise ValueError(f"Table '{schema}.{table}' introuvable dans '{database}'")

        # Clés primaires
        pks = await conn.fetch("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary;
        """, f"{schema}.{table}")

        return {
            "database": database,
            "schema": schema,
            "table": table,
            "columns": [serialize_row(c) for c in cols],
            "primary_keys": [pk['attname'] for pk in pks]
        }

@mcp.tool
async def query_readonly(
    database: str,
    sql: str,
    params: Optional[List[Any]] = None,
    max_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Exécute une requête SQL en lecture seule.

    Args:
        database: Nom de la base de données
        sql: Requête SQL (paramètres avec $1, $2, etc.)
        params: Valeurs des paramètres (optionnel)
        max_rows: Limite de lignes (défaut: QUERY_MAX_ROWS_DEFAULT, max: QUERY_MAX_ROWS_HARD)

    Returns:
        Dictionnaire avec colonnes, lignes, et indicateur de troncature
    """
    user_id = get_user_id()
    sql_excerpt = sql[:100].replace("\n", " ")
    logger.info(f"[query_readonly] Utilisateur: {user_id}, base: {database}, SQL: {sql_excerpt}...")

    # Limite de lignes
    if max_rows is None:
        max_rows = QUERY_MAX_ROWS_DEFAULT
    max_rows = min(max_rows, QUERY_MAX_ROWS_HARD)

    pool = await get_pool(database)
    params = params or []

    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            # Récupère max_rows + 1 pour détecter la troncature
            cur = await conn.cursor(sql, *params)
            rows = await cur.fetch(max_rows + 1)

    truncated = len(rows) > max_rows
    rows = rows[:max_rows]

    # Extraction des colonnes
    columns = list(rows[0].keys()) if rows else []

    return {
        "database": database,
        "columns": columns,
        "rows": [serialize_row(r) for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
        "max_rows": max_rows
    }

# ========== Outils MCP - Écriture (protégés par rôle mcp_write) ==========

@mcp.tool
async def execute_write(
    database: str,
    sql: str,
    params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Exécute une requête SQL d'écriture (INSERT/UPDATE/DELETE/CREATE/ALTER/DROP).

    IMPORTANT : Requiert le rôle Keycloak 'mcp_write'.

    Args:
        database: Nom de la base de données
        sql: Requête SQL (paramètres avec $1, $2, etc.)
        params: Valeurs des paramètres (optionnel)

    Returns:
        Dictionnaire avec statut et lignes retournées (si RETURNING)
    """
    user_id = get_user_id()
    sql_excerpt = sql[:100].replace("\n", " ")

    # Gate d'accès écriture
    if not has_write_access():
        logger.warning(f"[execute_write] REFUSÉ - Utilisateur: {user_id}, base: {database}")
        raise PermissionError(
            "Écriture non autorisée (rôle Keycloak 'mcp_write' requis). "
            "Contactez l'administrateur pour obtenir ce rôle."
        )

    logger.info(f"[execute_write] Utilisateur: {user_id}, base: {database}, SQL: {sql_excerpt}...")

    # Filet anti-tables NocoDB (nc_*) - détecte nc_ en début d'identifiant uniquement
    if re.search(r'\bnc_', sql, re.IGNORECASE):
        raise ValueError(
            "Accès aux tables NocoDB (nc_*) interdit. "
            "Le rôle mcp_rw n'a aucun droit sur ces tables."
        )

    # Filet anti-schémas système
    sql_lower = sql.lower()
    for schema in ("pg_catalog", "information_schema", "pg_toast", "pg_temp"):
        if re.search(r'\b' + schema + r'\b', sql_lower):
            raise ValueError(
                f"Accès au schéma système '{schema}' interdit."
            )

    pool = await get_rw_pool(database)
    params = params or []
    sql_upper = sql.upper()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Exécute la requête UNE SEULE fois
            if "RETURNING" in sql_upper:
                rows = await conn.fetch(sql, *params)
                return {
                    "database": database,
                    "status": f"RETURNING {len(rows)} ligne(s)",
                    "rows": [serialize_row(r) for r in rows],
                    "row_count": len(rows),
                }
            else:
                status = await conn.execute(sql, *params)
                return {
                    "database": database,
                    "status": status,
                    "message": f"Exécution réussie : {status}",
                }

@mcp.tool
async def create_table(
    database: str,
    schema: str,
    table: str,
    columns: List[Dict[str, str]]
) -> Dict[str, str]:
    """
    Crée une nouvelle table dans la base de données.

    IMPORTANT : Requiert le rôle Keycloak 'mcp_write'.

    Args:
        database: Nom de la base de données
        schema: Nom du schéma
        table: Nom de la table
        columns: Liste de colonnes [{name, type, constraints?}, ...]
                 Ex: [{"name": "id", "type": "SERIAL", "constraints": "PRIMARY KEY"},
                      {"name": "name", "type": "TEXT", "constraints": "NOT NULL"}]

    Returns:
        Statut de la création
    """
    user_id = get_user_id()

    # Gate d'accès écriture
    if not has_write_access():
        logger.warning(f"[create_table] REFUSÉ - Utilisateur: {user_id}, table: {schema}.{table}")
        raise PermissionError(
            "Écriture non autorisée (rôle Keycloak 'mcp_write' requis). "
            "Contactez l'administrateur pour obtenir ce rôle."
        )

    logger.info(f"[create_table] Utilisateur: {user_id}, base: {database}, table: {schema}.{table}")

    pool = await get_rw_pool(database)

    # Construction sécurisée de la requête CREATE TABLE
    async with pool.acquire() as conn:
        # quote_ident pour sécuriser les identifiants
        schema_quoted = await conn.fetchval("SELECT quote_ident($1)", schema)
        table_quoted = await conn.fetchval("SELECT quote_ident($1)", table)

        # Construction des colonnes
        col_defs = []
        for col in columns:
            col_name = await conn.fetchval("SELECT quote_ident($1)", col["name"])
            col_type = col["type"]  # Les types SQL sont des mots-clés, pas besoin de quote
            col_constraints = col.get("constraints", "")
            col_defs.append(f"{col_name} {col_type} {col_constraints}".strip())

        columns_sql = ",\n    ".join(col_defs)
        create_sql = f"CREATE TABLE {schema_quoted}.{table_quoted} (\n    {columns_sql}\n);"

        logger.info(f"[create_table] SQL généré: {create_sql[:200]}...")

        async with conn.transaction():
            await conn.execute(create_sql)

        return {
            "database": database,
            "schema": schema,
            "table": table,
            "message": f"Table {schema}.{table} créée avec succès",
            "sql": create_sql
        }

# ========== Main ==========

if __name__ == "__main__":
    logger.info(f"Lancement du serveur MCP PostgreSQL sur 0.0.0.0:8080")
    mcp.run(transport="http", host="0.0.0.0", port=8080)
