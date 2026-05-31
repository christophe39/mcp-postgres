# MCP PostgreSQL - AGNI

MCP custom pour accès direct aux bases PostgreSQL du VPS Hostinger (FastMCP + OIDCProxy).

## 🎯 Objectif

Permettre à Claude (Desktop/Web/iOS/iPad) d'interroger et gérer les bases PostgreSQL de l'écosystème AGNI :
- `opepartner` : données consulting OPEPARTNER
- `calocalc_inscription` : données CaloCalc
- `db_agni` : données AGNI Consult
- `nocodb_db` : métadonnées NocoDB
- `affine` : données AFFiNE

## 🛠️ Outils exposés (MVP)

### Exploration
- `list_databases()` : Liste toutes les bases accessibles
- `list_tables(database)` : Liste les tables d'une base
- `get_schema(database, table?)` : Schéma complet (colonnes, types, FK, index)
- `get_table_stats(database, table)` : Stats (nb lignes, taille, dernière MAJ)

### Requêtes
- `query(database, sql, params?)` : Exécute une requête SELECT (lecture seule par défaut)
- `execute(database, sql, params?)` : Exécute INSERT/UPDATE/DELETE (nécessite confirmation)

### Gestion
- `backup_database(database)` : pg_dump vers Cloudflare R2
- `restore_database(database, backup_id)` : pg_restore depuis R2
- `create_database(name, owner?)` : Créer une nouvelle base
- `drop_database(name)` : Supprimer une base (confirmation explicite requise)

### Templates
- `create_opepartner_tables()` : Créer les 14 tables OPEPARTNER (si base vide)
- `migrate_database(database, migration_script)` : Appliquer une migration SQL

## 🔐 Sécurité

- **Auth OIDC/Keycloak** via OIDCProxy (realm `mcp`, client `mcp-postgres`)
- **Lecture seule par défaut** : `query()` ne peut que SELECT
- **Confirmation explicite** pour actions destructives (DROP, DELETE sans WHERE, etc.)
- **Isolation par base** : chaque connexion PostgreSQL est scopée à une database
- **Logs d'audit** : toutes les requêtes sont loggées avec utilisateur OIDC

## 📦 Variables d'environnement

```bash
# PostgreSQL - Container principal
POSTGRES_HOST=69.62.110.207
POSTGRES_PORT=5432
POSTGRES_USER=agni_admin
POSTGRES_PASSWORD=<secret>
POSTGRES_DATABASES=opepartner,calocalc_inscription,db_agni,nocodb_db

# PostgreSQL - AFFiNE (container séparé)
AFFINE_POSTGRES_HOST=69.62.110.207
AFFINE_POSTGRES_PORT=5433  # Port différent si nécessaire
AFFINE_POSTGRES_USER=affine_admin
AFFINE_POSTGRES_PASSWORD=<secret>
AFFINE_POSTGRES_DATABASE=affine

# Auth OIDC
OIDC_CONFIG_URL=https://keycloak.agnisolution.fr/realms/mcp/.well-known/openid-configuration
OIDC_CLIENT_ID=mcp-postgres
OIDC_CLIENT_SECRET=<secret>
MCP_BASE_URL=https://mcp-postgres.agnisolution.fr

# Redis (sessions)
REDIS_URL=<Redis URL interne>

# Encryption
JWT_SIGNING_KEY=<généré>
FERNET_SECRET=<généré>

# Cloudflare R2 (backups)
R2_ENDPOINT_URL=<endpoint>
R2_ACCESS_KEY_ID=<access_key>
R2_SECRET_ACCESS_KEY=<secret_key>
R2_BUCKET_NAME=agni-postgres-backups
```

## 🚀 Déploiement Coolify

1. Créer une nouvelle application "MCP PostgreSQL"
2. Type : Dockerfile
3. Variables d'environnement : toutes celles ci-dessus
4. Healthcheck :
   - Path : `/.well-known/oauth-protected-resource/mcp`
   - Port : 8080
   - Start period : 30s
5. Domaine : `mcp-postgres.agnisolution.fr`
6. Activer Traefik HTTPS

## 🧪 Tests locaux

```bash
# Installation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Remplir les credentials dans .env

# Lancement
python server.py

# Test dans un autre terminal
curl http://localhost:8080/.well-known/oauth-protected-resource/mcp
```

## 📋 Roadmap

- [ ] **Phase 1** : Outils de base (list_databases, query, list_tables, get_schema)
- [ ] **Phase 2** : Outils de gestion (backup, restore, create_database)
- [ ] **Phase 3** : Templates et migrations (create_opepartner_tables, migrate_database)
- [ ] **Phase 4** : Déploiement Coolify + auth OIDC
- [ ] **Phase 5** : Tests cross-device (Desktop, Web, iOS)
- [ ] **Phase 6** : Optimisations (cache, pool de connexions, query timeout)

## 🔗 Liens

- **Documentation FastMCP** : https://github.com/anthropics/fast-mcp
- **Documentation OIDCProxy** : Intégrée dans FastMCP 3.3+
- **VPS SSH** : `ssh root@69.62.110.207`
- **Container PostgreSQL principal** : `c0408wgcs08kc0w480koowcs`

---

*Créé le 31 mai 2026*
