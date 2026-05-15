# OPEPARTNER Stack - Système Excalidraw + MCP Custom

> Infrastructure pour la génération automatisée de schémas stratégiques (BMC, PESTEL, SWOT) pilotée par Claude

## 🎯 Vision

Système self-hosted permettant de générer et maintenir des schémas visuels depuis des prompts Claude, avec stockage pérenne et intégration complète dans l'écosystème OPEPARTNER (AFFiNE + NocoDB).

### Cas d'usage

1. **OPEPARTNER** (prioritaire) : Dossiers clients confidentiels, schémas stratégiques
2. **CaloCalc** (futur) : Documentation technique, schémas d'architecture

## 🏗️ Architecture

```
Claude (Desktop/Web/iOS/iPad)
    ↓ (via MCP custom remote HTTPS)
MCP Excalidraw
    ↓
Excalidraw self-hosted (frontend + storage backend)
    ↓
NocoDB → PostgreSQL `opepartner` (14 tables)
    ↓
AFFiNE (workspace OPEPARTNER)
```

## 📦 Composants

| Composant | Description | URL cible |
|-----------|-------------|-----------|
| **PostgreSQL** | Base `opepartner` dans container `c0408wgcs08kc0w480koowcs` | VPS Hostinger |
| **NocoDB** | Interface base de données | `https://nocodb.agnisolution.fr` |
| **Excalidraw** | Frontend + storage backend self-hosted | `https://excalidraw.opepartner.fr` |
| **MCP Custom** | Serveur MCP remote HTTPS | `https://mcp-excalidraw.agnisolution.fr` |
| **AFFiNE** | Documentation workspace OPEPARTNER | `https://affine.agnisolution.fr` |

## 🗄️ Modèle de données (14 tables MVP)

- `Clients`, `Contacts`, `Missions`, `Ateliers`
- `Livrables`, `Actions`, `Comptes_rendus`
- `Référentiel_modèles`
- **`Schemas_Excalidraw`** ⭐ (table pivot pour le MCP)
- `Business_Model_Canvas`, `SWOT`, `PESTEL`, `Value_Proposition_Canvas`, `Plan_90_jours`

## 🚀 Roadmap

- [x] Phase A-C : Préparation AFFiNE (workspace OPEPARTNER)
- [ ] **Phase 1** : Préparation environnement local (Git, structure)
- [ ] **Phase 2** : Création base PostgreSQL + 14 tables
- [ ] **Phase 3** : Connexion NocoDB
- [ ] **Phase 4** : Déploiement Excalidraw self-hosted
- [ ] **Phase 5** : Développement MCP custom
- [ ] **Phase 6** : Tests bout-en-bout

## 📁 Structure du projet

```
opepartner-stack/
├── CLAUDE.md              # Brief de contexte complet
├── README.md              # Ce fichier
├── .env.example           # Template variables d'environnement
├── infra/                 # Infrastructure et déploiement
│   ├── docker-compose/    # Compositions Docker pour Coolify
│   ├── sql/               # Scripts SQL (init, migrations)
│   └── traefik/           # Exemples de labels Traefik
├── mcp-excalidraw/        # Code du MCP custom
│   ├── src/               # Code source (Python FastMCP ou TypeScript)
│   └── .env.example       # Variables spécifiques au MCP
└── docs/                  # Documentation technique
    ├── architecture.md
    ├── workflows.md
    └── migration-guide.md
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

*Dernière mise à jour : 15 mai 2026*
