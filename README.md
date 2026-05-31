# MCP Postgres OPEPARTNER

MCP pour accès **lecture seule** aux bases PostgreSQL du VPS Hostinger, protégé par OIDCProxy (FastMCP) → Keycloak.

**Phase actuelle** : C2-C5 — Lecture seule complète avec introspection + requêtes paramétrées.

## 🎯 Objectif

Permettre à Claude (Desktop/Web/iOS/iPad) d'interroger les bases PostgreSQL de l'écosystème AGNI :
- `opepartner` : données consulting OPEPARTNER
- `calocalc_inscription` : données CaloCalc
- `db_agni` : données AGNI Consult
- `nocodb_db` : métadonnées NocoDB

## 🛠️ Outils exposés (lecture seule)

### Identité
- `whoami()` : Identité de l'utilisateur authentifié (remplace hello_world)

### Introspection
- `list_databases()` : Liste des bases autorisées (DB_WHITELIST)
- `list_schemas(database)` : Schémas d'une base (hors schémas système)
- `list_tables(database, schema="public")` : Tables/vues d'un schéma
- `describe_table(database, schema, table)` : Structure complète (colonnes, types, clés primaires)

### Requêtes
- `query_readonly(database, sql, params?, max_rows?)` : Exécute une requête SELECT
  - Transaction READ ONLY
  - Paramètres via `$1`, `$2`, etc. (jamais de concaténation SQL)
  - Limitation de lignes forcée (défaut 100, max 1000)
  - Détection de troncature automatique
  - Sérialisation JSON (dates → ISO, Decimal → string)

## 🔐 Sécurité

### Auth & Autorisation
- **Auth OIDC/Keycloak** via OIDCProxy (realm `mcp`, client `mcp-postgres`)
- **Rôle PostgreSQL** : `mcp_ro` (lecture seule stricte, créé par l'infra)
- **Whitelist de bases** : seules les bases listées dans `DB_WHITELIST` sont accessibles

### Garde-fous SQL
- **server_settings PostgreSQL** :
  - `statement_timeout` : timeout requis par requête (5000ms par défaut)
  - `default_transaction_read_only` : "on" (lecture seule forcée)
- **Identifiants SQL** : toujours via paramètres (`$1`, `$2`) ou `quote_ident`, jamais de f-string
- **Limite de lignes** : forcée côté serveur (fetch limité), pas via `LIMIT` SQL injectable

### Logs d'audit
Chaque appel d'outil logue :
- Identité utilisateur (Keycloak `sub` claim)
- Outil appelé
- Base ciblée
- Extrait SQL (pour `query_readonly`)

## 📦 Variables d'environnement

Voir [.env.example](.env.example) pour la liste complète.

**Critiques** :
```bash
# PostgreSQL - Accès lecture seule (rôle mcp_ro)
DB_HOST=<IP VPS>
DB_PORT=5432
DB_USER=mcp_ro
DB_PASSWORD=<secret par Desktop>
DB_WHITELIST=opepartner,calocalc_inscription,db_agni,nocodb_db
DB_DEFAULT=db_agni

# Limites de sécurité
QUERY_MAX_ROWS_DEFAULT=100
QUERY_MAX_ROWS_HARD=1000
STATEMENT_TIMEOUT_MS=5000

# Auth OIDC/Keycloak
OIDC_CONFIG_URL=https://keycloak.agnisolution.fr/realms/mcp/.well-known/openid-configuration
OIDC_CLIENT_ID=mcp-postgres
OIDC_CLIENT_SECRET=<secret par Desktop>
MCP_BASE_URL=https://mcp-postgres.agnisolution.fr

# Redis + Encryption
REDIS_URL=<Redis URL interne>
JWT_SIGNING_KEY=<généré par Desktop>
FERNET_SECRET=<généré par Desktop>
```

⚠️ **Tous les secrets sont posés par Desktop dans Coolify** — ne RIEN hardcoder dans le code.

## 🚀 Déploiement Coolify (par Desktop)

1. Créer l'application "MCP PostgreSQL"
2. Type : Dockerfile
3. Poser toutes les variables d'environnement
4. Healthcheck :
   - Path : `/.well-known/oauth-protected-resource/mcp`
   - Port : 8080
   - Start period : 30s
5. Domaine : `mcp-postgres.agnisolution.fr`
6. Traefik HTTPS activé

## 📋 Roadmap

- [x] **C1** : Squelette auth-only déployable
- [x] **C2** : asyncpg + pools multi-base
- [x] **C3** : Outils d'introspection (list_databases, list_schemas, list_tables, describe_table)
- [x] **C4** : query_readonly avec paramètres + limite de lignes
- [x] **C5** : Garde-fous (whitelist, quote_ident, logs audit, erreurs claires)
- [ ] **Futur** : Outils écriture (INSERT/UPDATE/DELETE avec confirmation), backups R2, templates

## 🔗 Liens

- **Repo GitHub** : https://github.com/christophe39/mcp-postgres
- **Documentation FastMCP** : https://github.com/anthropics/fast-mcp
- **VPS SSH** : `ssh root@69.62.110.207`

---

*Créé le 31 mai 2026 · Mis à jour après C2-C5*
