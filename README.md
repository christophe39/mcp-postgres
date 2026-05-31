# AGNI MCP Stack

> Suite de MCPs custom self-hosted pour l'écosystème AGNI (OPEPARTNER, CaloCalc, AGNI Consult)

## 🎯 Vision

Infrastructure multi-MCP permettant d'intégrer Claude (Desktop/Web/iOS/iPad) avec l'ensemble des services AGNI : génération de schémas visuels (Excalidraw), accès bases de données (PostgreSQL), gestion documentaire (AFFiNE), et futurs services.

### Cas d'usage

1. **OPEPARTNER** : Dossiers clients confidentiels, schémas stratégiques (BMC, PESTEL, SWOT), accès bases
2. **CaloCalc** : Documentation technique, schémas d'architecture, données inscription
3. **AGNI Consult** : Documentation interne, données métier

## 🏗️ Architecture

```
Claude (Desktop/Web/iOS/iPad)
    ↓ (via MCPs custom remote HTTPS)
    ├─── MCP Excalidraw ──→ Excalidraw self-hosted ──→ NocoDB ──→ PostgreSQL
    ├─── MCP PostgreSQL ──→ PostgreSQL (accès direct multi-bases)
    └─── (futurs MCPs...)
                              ↓
                    AFFiNE (workspaces OPEPARTNER, AGNI Consult)
```

## 📦 MCPs Custom

| MCP | Description | URL | Statut |
|-----|-------------|-----|--------|
| **mcp-excalidraw** | Génération schémas visuels (BMC, PESTEL, SWOT, organigrammes) | `https://mcp-excalidraw.agnisolution.fr` | ✅ Production |
| **mcp-postgres** | Accès direct bases PostgreSQL (opepartner, calocalc_inscription, db_agni, etc.) | `https://mcp-postgres.agnisolution.fr` | 🚧 À développer |
| **mcp-jouet** | Validation auth OIDC/Keycloak | `https://mcp-jouet.agnisolution.fr` | ✅ Test |

## 🗄️ Services backend

| Service | Description | URL |
|---------|-------------|-----|
| **PostgreSQL** | 5 containers PostgreSQL sur VPS Hostinger | `c0408wgcs08kc0w480koowcs` (principal) |
| **NocoDB** | Interface bases de données | `https://nocodb.agnisolution.fr` |
| **Excalidraw** | Frontend + storage backend self-hosted | `https://excalidraw.opepartner.fr` |
| **AFFiNE** | Documentation (2 workspaces) | `https://affine.agnisolution.fr` |
| **Keycloak** | Auth OIDC pour MCPs | `https://keycloak.agnisolution.fr` |

## 🗄️ Bases de données PostgreSQL

### Container principal (`c0408wgcs08kc0w480koowcs`)

| Base | Description | Tables principales |
|------|-------------|--------------------|
| `opepartner` | Données OPEPARTNER consulting | 14 tables (Clients, Missions, Schemas_Excalidraw, BMC, SWOT, PESTEL...) |
| `calocalc_inscription` | Données CaloCalc | Utilisateurs, profils, données métier |
| `db_agni` | Données AGNI Consult | Documentation, projets |
| `nocodb_db` | Métadonnées NocoDB | Bases, tables, vues |

## 🚀 Roadmap

### MCP Excalidraw (✅ terminé)
- [x] Phase A-C : Préparation AFFiNE (workspace OPEPARTNER)
- [x] Phase E : Création base PostgreSQL + 14 tables
- [x] Phase F : Connexion NocoDB
- [x] Phase G : Déploiement Excalidraw self-hosted
- [x] Phase H : Développement MCP custom Excalidraw
- [x] Auth OIDC/Keycloak via OIDCProxy

### MCP PostgreSQL (🚧 en cours)
- [ ] **Phase 1** : Structure projet et spécifications
- [ ] **Phase 2** : Développement outils de base (list_databases, query, list_tables, get_schema)
- [ ] **Phase 3** : Outils avancés (backup, restore, migrations)
- [ ] **Phase 4** : Déploiement Coolify + auth OIDC
- [ ] **Phase 5** : Tests cross-device (Desktop, Web, iOS)

## 📁 Structure du projet

```
agni-mcp-stack/
├── CLAUDE.md                  # Brief de contexte complet
├── README.md                  # Ce fichier
├── .env.example               # Template variables d'environnement
├── infra/                     # Infrastructure et déploiement
│   ├── docker-compose/        # Compositions Docker pour Coolify
│   ├── sql/                   # Scripts SQL (init, migrations)
│   └── traefik/               # Exemples de labels Traefik
├── mcp-excalidraw/            # MCP Excalidraw (✅ production)
│   ├── server.py              # Serveur FastMCP
│   ├── requirements.txt       # Dépendances Python
│   ├── Dockerfile             # Image Docker
│   └── .env.example           # Variables d'environnement
├── mcp-postgres/              # MCP PostgreSQL (🚧 à développer)
│   ├── server.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── mcp-jouet/                 # MCP test auth OIDC
│   └── server.py
├── auth-service/              # Service d'authentification
├── frontend-custom/           # Frontend Excalidraw custom
└── docs/                      # Documentation technique
    ├── ARCHITECTURE.md
    ├── MCP-EXCALIDRAW-TECHNICAL-BRIEF.md
    └── (autres docs de session)
```

## 🔐 Configuration

1. Copier `.env.example` en `.env`
2. Remplir les credentials PostgreSQL, NocoDB, AFFiNE
3. Générer un token MCP secret
4. Configurer les sous-domaines DNS dans Cloudflare

## 🎯 Règles d'or de migrabilité

1. **Sous-domaines logiques** : `excalidraw.opepartner.fr` (pas générique)
2. **Variables d'environnement** : zéro hardcoding
3. **Workflows n8n préfixés** : `OPEPARTNER_*`
4. **Backup automatisé** : `pg_dump opepartner` quotidien
5. **Documentation des dépendances** : chaque composant documente ses liens

## 🔗 Liens rapides

- **VPS SSH** : `ssh root@69.62.110.207`
- **AFFiNE OPEPARTNER** : https://affine.agnisolution.fr/workspace/3869ae28-9638-4390-a28d-905ff5c563d6
- **Coolify** : https://coolify.agnisolution.fr
- **CLAUDE.md** : Brief complet du projet

## 👤 Contact

**Christophe Martin**  
AGNI Consult / OPEPARTNER  
cmartin@agniconsult.fr

---

*Dernière mise à jour : 31 mai 2026*
