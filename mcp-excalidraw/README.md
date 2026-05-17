# MCP Excalidraw OPEPARTNER

> MCP remote pour générer des schémas stratégiques Excalidraw depuis Claude (web, Mac, iPad, iPhone)

## 🎯 Objectif

Permettre de créer des schémas visuels (BMC, PESTEL, SWOT, organigrammes) via prompts Claude, avec :
- Chiffrement E2E (AES-GCM) compatible avec le frontend Excalidraw
- Stockage pérenne dans PostgreSQL
- Traçabilité dans NocoDB (table `schemas_excalidraw`)
- Documentation automatique dans AFFiNE (workspace OPEPARTNER)

## 🏗️ Architecture

```
Claude (web/Mac/iPad/iPhone)
        ↓ HTTPS + auth
MCP Excalidraw (mcp-excalidraw.agnisolution.fr)
        ↓
    ┌───┴─────┬──────────┬───────────┐
    ▼         ▼          ▼           ▼
 Backend  Postgres   NocoDB      AFFiNE
 :8080    10.0.1.23  API         GraphQL
```

## 📦 Stack technique

- **Langage** : Python 3.11+
- **Framework MCP** : FastMCP (transport HTTP/SSE)
- **Base de données** : PostgreSQL 17 (container `pk4s888o4wkc8ogokg0sg840`)
- **Déploiement** : Docker + Coolify + Traefik

## 🔐 Sécurité

- **User PostgreSQL dédié** : `mcp_excalidraw` (droits minimaux, pas de DDL)
- **Chiffrement** : AES-GCM (reproduction exacte du format frontend)
- **Auth** : OAuth 2.1 ou ForwardAuth + bearer token
- **Requêtes SQL** : paramétrées partout (aucune concaténation)
- **Validation** : inputs typés, bornés, whitelist strict

## 🚀 Installation locale

```bash
# Créer un environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -e ".[dev]"

# Copier le fichier .env.example
cp .env.example .env

# Éditer .env avec les vraies valeurs
# (DATABASE_URL, NOCODB_TOKEN, AFFINE_TOKEN, etc.)

# Lancer les tests
pytest
```

## 🛠️ Outils MCP disponibles

### Création depuis templates
- `create_bmc(client_name, mission_name?, ...)`
- `create_pestel(client_name, mission_name?, ...)`
- `create_swot(client_name, mission_name?, ...)`
- `create_from_template(template_name, data, metadata?)`

### Manipulation de scènes
- `get_scene(scene_id)` — déchiffre et retourne le JSON
- `update_scene(scene_id, data)` — modifie, re-chiffre, incrémente version
- `list_scenes(client?, document_type?, status?, limit=10, offset=0)`
- `delete_scene(scene_id, confirm=False)` — purge réelle (RGPD)

### Templates et NocoDB
- `list_templates(categorie?)`
- `get_template_placeholders(template_name)`
- `find_or_create_client(nom, secteur?)`
- `create_mission(client_id, nom, date_debut?, date_fin?)`

### Exports (asynchrones)
- `export_scene_png(scene_id, width?, height?)`
- `export_scene_svg(scene_id)`

## 📁 Structure du projet

```
mcp-excalidraw/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── src/
│   ├── server.py             # entry point FastMCP (transport HTTP)
│   ├── config.py             # chargement + validation des env vars
│   ├── auth.py               # middleware d'authentification
│   ├── crypto.py             # chiffrement AES-GCM compatible frontend
│   ├── clients/
│   │   ├── database.py       # pool Postgres, requêtes paramétrées
│   │   ├── excalidraw.py     # POST/GET backend storage
│   │   ├── nocodb.py         # API NocoDB (traçabilité)
│   │   └── affine.py         # API/GraphQL AFFiNE (doc auto)
│   ├── templates/
│   │   ├── manager.py        # get_template, fill_template
│   │   ├── bmc.json
│   │   ├── pestel.json
│   │   └── ...
│   ├── tools/
│   │   ├── scenes.py         # create/get/update/list/delete_scene
│   │   ├── frameworks.py     # create_bmc/pestel/swot/...
│   │   └── nocodb_tools.py   # find_or_create_client, create_mission
│   ├── orchestration.py      # logique transactionnelle multi-systèmes
│   └── utils.py              # generate_id, validation, sanitization
└── tests/
    ├── test_crypto.py        # round-trip chiffrement vs frontend
    ├── test_templates.py
    └── test_orchestration.py
```

## 🔄 Workflow de développement

**Phase H.1 — Fondations (en cours)**
- [x] Structure projet + pyproject + .gitignore + .env.example
- [ ] Script SQL user `mcp_excalidraw` (droits minimaux)
- [ ] `config.py` : chargement + validation env vars
- [ ] `clients/database.py` : pool Postgres, requêtes paramétrées
- [ ] Validation : connexion Postgres OK avec user restreint

**Phase H.2 — Chiffrement (critique)**
- [ ] Étude code source frontend (format exact AES-GCM)
- [ ] `crypto.py` : encrypt/decrypt compatibles
- [ ] `tests/test_crypto.py` : round-trip bidirectionnel
- [ ] Validation : scène MCP → lisible frontend, et inversement

**Phase H.3 — Clients d'intégration**
- [ ] `clients/excalidraw.py` : POST/GET backend
- [ ] `clients/nocodb.py` : find/create/insert via API
- [ ] `clients/affine.py` : investiguer API/GraphQL
- [ ] Validation : chaque client testé isolément

**Phase H.4 — Outils CRUD + orchestration**
- [ ] `tools/scenes.py` : create/get/update/list/delete_scene
- [ ] `orchestration.py` : séquence complète + gestion d'erreurs
- [ ] Validation : scène simple bout-en-bout (chiffrée, BDD, NocoDB)

**Phase H.5 — Templates frameworks**
- [ ] Créer templates JSON (BMC, PESTEL, SWOT, etc.)
- [ ] `templates/manager.py` : fill_template avec placeholders
- [ ] `tools/frameworks.py` : create_bmc/pestel/swot
- [ ] Validation : BMC complet généré et lisible frontend

**Phase H.6 — Déploiement remote**
- [ ] Dockerfile + healthcheck `/health`
- [ ] Déploiement Coolify + sous-domaine `mcp-excalidraw.agnisolution.fr`
- [ ] Mise en place auth (OAuth 2.1 ou ForwardAuth)
- [ ] Validation : endpoint HTTPS accessible, auth OK

**Phase H.7 — Intégration Claude.ai**
- [ ] Ajout dans Claude.ai Connectors
- [ ] Tests cross-device (web, Mac, iPhone)
- [ ] Validation : workflow complet fonctionnel depuis mobile

## 📚 Documentation

- **Contexte global** : [CLAUDE.md](../CLAUDE.md)
- **Spec technique** : [BRIEF-PROJET-MCP-EXCALIDRAW.md](../docs/BRIEF-PROJET-MCP-EXCALIDRAW.md)
- **Architecture** : [ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Troubleshooting** : [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)

## 📝 Règles de développement

1. **Sécurité d'abord** : user dédié, requêtes paramétrées, validation stricte
2. **Jamais de credentials dans Git** : `.env` en gitignore
3. **Tester chaque phase** avant la suivante (pas de big bang)
4. **Documenter au fil de l'eau** : README + docstrings
5. **Arbitrages respectés** : remote HTTPS + chiffrement E2E + Python/FastMCP

## 📞 Contact

- **Auteur** : Christophe Martin (cmartin@agniconsult.fr)
- **Projet** : OPEPARTNER Stack
- **Repository** : github.com/christophe39/excalidraw

---

*Dernière mise à jour : 16 mai 2026*
