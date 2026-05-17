# BRIEF PROJET — MCP custom Excalidraw OPEPARTNER

> Document de référence pour Claude Code. Cadre l'intégralité de la phase H : développement et déploiement du MCP remote Excalidraw. À lire après `CLAUDE.md`.
>
> **Décisions structurantes déjà arbitrées (ne pas remettre en question) :**
> - Mode : **MCP remote HTTPS** déployé sur le VPS (PAS local stdio)
> - Chiffrement : le MCP **reproduit le chiffrement E2E AES-GCM** des scènes (option A)
> - Langage : **Python + FastMCP**

---

## 1. Contexte et objectif

Le système Excalidraw self-hosted (frontend + proxy + backend storage + auth) est **déployé et fonctionnel** sur le VPS. La base PostgreSQL `excalidraw_storage` existe (tables `keyv`, `utilisateurs`, `templates`, vue `scenes_with_user`).

Objectif de la phase H : développer un **MCP remote** qui permet, depuis n'importe quel device (web, Mac, iPad, iPhone), de générer des schémas stratégiques (BMC, PESTEL, SWOT, organigrammes) via prompts Claude, avec stockage chiffré, traçabilité NocoDB, et documentation AFFiNE.

**Workflow cible :**

> *"Crée un BMC pour Client Dupont SAS, mission Transformation Digitale"*
> → le MCP : crée/retrouve le client, génère la scène depuis le template BMC, **chiffre la scène (AES-GCM)**, la stocke dans `keyv`, enregistre la traçabilité dans NocoDB (`schemas_excalidraw`), crée le doc AFFiNE, et retourne l'URL éditable (avec la clé de déchiffrement) + le lien AFFiNE.

## 2. Architecture cible

```
Claude (web / Mac / iPad / iPhone)
        │  HTTPS + auth
        ▼
┌─────────────────────────────────────────────┐
│ VPS Hostinger — Coolify + Traefik           │
│                                             │
│  mcp-excalidraw.agnisolution.fr             │
│  ┌────────────────────────────────────┐    │
│  │ MCP remote (Python FastMCP, HTTP)  │    │
│  │ - auth (ForwardAuth exca-auth +    │    │
│  │   bearer token, ou OAuth 2.1)      │    │
│  │ - chiffrement AES-GCM côté MCP     │    │
│  │ - user Postgres dédié mcp_excalidraw│   │
│  └───┬─────────┬──────────┬───────────┘    │
│      │         │          │                 │
│      ▼         ▼          ▼                 │
│  ┌────────┐ ┌──────┐ ┌─────────┐           │
│  │backend │ │Postgres│ │ AFFiNE │           │
│  │ :8080  │ │10.0.1.23│ │GraphQL │           │
│  │(interne)│ │ :5432  │ │ API    │           │
│  └────────┘ └──────┘ └─────────┘           │
│      │                                       │
│  réseau Docker interne (port 5432 fermé      │
│  au monde extérieur — accès interne only)   │
└─────────────────────────────────────────────┘
```

**Sous-domaine** : `mcp-excalidraw.agnisolution.fr` (cohérent avec l'existant `exca-api`, `exca-auth`). Migration future vers `opepartner.fr` possible via variable d'env, sans refactor.

## 3. Modèle de sécurité (NON négociable)

### 3.1. Authentification de l'endpoint

Le MCP est un endpoint HTTPS public. Sans auth, quiconque trouve l'URL peut lire/créer/supprimer des schémas clients et toucher la BDD.

**Approche retenue (à valider techniquement par Claude Code) :**

- **Voie 1 (préférée si compatible Claude.ai Connectors)** : OAuth 2.1 — c'est le standard MCP remote moderne supporté par Claude.ai. Claude Code doit vérifier la compatibilité FastMCP ↔ OAuth 2.1 ↔ Connectors Claude.ai.
- **Voie 2 (fallback)** : derrière le ForwardAuth Traefik existant (`exca-auth.agnisolution.fr`) + un bearer token statique long en header. Plus simple, déjà déployé, mais vérifier que Claude.ai Connectors accepte un header d'auth custom.

Claude Code doit **investiguer la compatibilité réelle** avant de coder, et proposer la voie viable. Ne pas supposer — tester.

### 3.2. Moindre privilège PostgreSQL

**Créer un user Postgres dédié `mcp_excalidraw`** — surtout PAS réutiliser `excalidraw_backend`.

Droits accordés strictement nécessaires :
- `SELECT, INSERT, UPDATE` sur `keyv` (création/lecture/maj de scènes)
- `SELECT` sur `templates` (lecture des templates)
- `SELECT` sur `utilisateurs` (résolution created_by)
- `DELETE` sur `keyv` uniquement (pour l'outil delete_scene / droit à l'oubli RGPD)
- Aucun droit DDL, aucun accès aux autres bases

Script de création du user à versionner dans `infra/sql/03_mcp_user.sql`.

### 3.3. Chiffrement E2E (option A — reproduit côté MCP)

**Le MCP doit reproduire exactement le schéma de chiffrement du frontend Excalidraw** pour que les scènes générées par MCP soient lisibles par le frontend (et inversement), et confidentielles en BDD.

Chaîne à reproduire (référence : ARCHITECTURE.md, scénarios 1 et 2) :

1. Sérialiser le JSON de la scène
2. Compresser avec pako/zlib (format compatible avec ce que le frontend attend)
3. Chiffrer en **AES-GCM** avec une clé générée aléatoirement
4. Encoder en base64
5. Stocker le blob `{version, compression, encryption, data, iv, tag}` dans `keyv.value`
6. Retourner l'URL au format `https://excalidraw.agnisolution.fr/#json={id},{clé_base64}`

**Point critique à valider par Claude Code** : analyser le code source exact du frontend Excalidraw (repo `github.com/christophe39/excalidraw`) pour reproduire **à l'identique** le format de chiffrement/compression (longueur de clé, mode GCM, format de l'IV, ordre compression/chiffrement). Une incompatibilité = scènes illisibles. Écrire un test de round-trip : scène créée par MCP → ouverte dans le frontend → identique.

### 3.4. Protections contre les attaques

- **Requêtes SQL paramétrées partout** — jamais de f-string/concaténation dans une requête SQL. Audit systématique.
- **Validation et bornage des inputs** :
  - Taille max du JSON de scène : 10 MB, rejet au-delà
  - `document_type` : whitelist stricte (`BMC`, `PESTEL`, `SWOT`, `VPC`, `ORGANIGRAMME`, `PLAN_90J`) — rejet de tout le reste
  - Nom de client : longueur max, caractères autorisés, pas d'injection
  - Tous les paramètres typés et validés avant usage
- **Prompt injection** : tout input (nom de client, contenu de champ, données template) est traité comme **donnée**, jamais comme instruction. Sanitization avant insertion BDD et avant injection dans les templates. Ne jamais évaluer/exécuter dynamiquement du contenu issu d'un input.
- **Rate limiting** : configuré au niveau Traefik (X requêtes/minute par source). Valeur à définir, démarrer conservateur (ex. 30/min).
- **Isolation réseau** : le MCP accède à Postgres via `10.0.1.23:5432` (réseau Docker interne). Le port 5432 reste fermé au monde extérieur. ✓ topologie déjà en place.
- **Pas de fuite dans les erreurs** : les messages d'erreur retournés à Claude ne contiennent jamais de credentials, chemins internes, ou stack traces complètes. Erreurs génériques côté client, détails dans les logs serveur uniquement.
- **Audit logging** : chaque opération sensible (create/update/delete scène) loggée avec timestamp, type d'opération, `created_by`, ID de scène — **sans** noms de clients en clair (RGPD) ni credentials.

### 3.5. RGPD

- Les noms de clients sont des données personnelles. Logs anonymisés (ID interne, pas le nom en clair).
- L'outil `delete_scene` doit purger **réellement** la ligne `keyv` (droit à l'oubli effectif, pas un soft-delete).
- Backups `pg_dump` de `excalidraw_storage` chiffrés au repos.

## 4. Stack technique

- **Langage** : Python 3.11+
- **Framework MCP** : FastMCP (transport HTTP/SSE pour le remote)
- **Dépendances principales** :
  - `fastmcp` (serveur MCP remote)
  - `psycopg2-binary` ou `asyncpg` (Postgres)
  - `httpx` (clients HTTP : backend Excalidraw, NocoDB, AFFiNE)
  - `cryptography` (AES-GCM)
  - `python-dotenv` (config)
- **Déploiement** : Dockerfile + service Coolify, sous-domaine Traefik
- **Repo** : intégré au projet existant `github.com/christophe39/excalidraw` (dossier `mcp-excalidraw/`) ou repo dédié — à arbitrer par Claude Code selon la propreté Git

## 5. Structure du projet

```
mcp-excalidraw/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml        # service Coolify + labels Traefik
├── .env.example              # toutes les variables, AUCUNE valeur réelle
├── .gitignore                # .env, __pycache__, etc.
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
│   │   ├── swot.json
│   │   ├── vpc.json
│   │   ├── organigramme.json
│   │   └── plan_90j.json
│   ├── tools/
│   │   ├── scenes.py         # create/get/update/list/delete_scene
│   │   ├── frameworks.py     # create_bmc/pestel/swot/...
│   │   ├── nocodb_tools.py   # find_or_create_client, create_mission
│   │   └── exports.py        # export_png/svg (async — voir §7)
│   ├── orchestration.py      # logique transactionnelle multi-systèmes
│   └── utils.py              # generate_id, validation, sanitization
└── tests/
    ├── test_crypto.py        # round-trip chiffrement vs frontend
    ├── test_templates.py
    ├── test_tools.py
    └── test_orchestration.py
```

## 6. Outils MCP à implémenter

### Synchrones — création depuis templates

- `create_bmc(client_name, mission_name?, partners?, key_activities?, key_resources?, value_proposition?, customer_relations?, channels?, customer_segments?, cost_structure?, revenue_streams?)`
- `create_pestel(client_name, mission_name?, political?, economic?, social?, technological?, environmental?, legal?)`
- `create_swot(client_name, mission_name?, strengths?, weaknesses?, opportunities?, threats?)`
- `create_from_template(template_name, data, metadata?)` — générique

### Synchrones — manipulation de scènes

- `get_scene(scene_id)` — déchiffre et retourne le JSON + métadonnées
- `update_scene(scene_id, data)` — modifie, re-chiffre, incrémente version
- `list_scenes(client?, document_type?, status?, limit=10, offset=0)`
- `delete_scene(scene_id, confirm=False)` — purge réelle, confirmation requise

### Synchrones — templates et NocoDB

- `list_templates(categorie?)`
- `get_template_placeholders(template_name)` — aide Claude à savoir quoi demander
- `find_or_create_client(nom, secteur?)`
- `create_mission(client_id, nom, date_debut?, date_fin?)`

### Asynchrones — exports lourds (voir §7)

- `export_scene_png(scene_id, width?, height?)` — rendering headless
- `export_scene_svg(scene_id)`

## 7. Traitement asynchrone des exports

Les exports PNG/SVG nécessitent un rendering headless (Playwright/Puppeteer) qui peut prendre 5-15 s. Pattern :

1. `export_scene_png(scene_id)` lance un job en arrière-plan, retourne immédiatement `{job_id, status: "processing"}`
2. Un worker effectue le rendering
3. `get_export_status(job_id)` permet de récupérer `{status, url}` quand prêt

Démarrer simple : si le rendering tient en < 10 s de façon fiable, un appel synchrone avec timeout généreux peut suffire pour le MVP. L'async est une optimisation, pas un bloqueur. Claude Code arbitre selon les tests réels.

## 8. Logique d'orchestration (cœur du MCP)

Chaque `create_*` orchestre plusieurs systèmes. Séquence et gestion d'erreurs :

```
1. Validation/sanitization de tous les inputs
2. find_or_create_client(client_name) → client_id (via NocoDB)
3. SI mission_name : find_or_create_mission → mission_id
4. Charger le template, remplir les placeholders (fill_template)
5. generate_id() → scene_id
6. crypto.encrypt(scene_json) → blob chiffré + clé
7. excalidraw.create_scene(scene_id, blob)  # POST backend
8. db.update_metadata(scene_id, created_by, template_id, metadata)
9. nocodb.insert('schemas_excalidraw', {...})
10. affine.create_doc(workspace=OPEPARTNER, folder=client, ...)
11. nocodb.update(schema_record, {affine_doc_id})
12. return {scene_id, edit_url (avec clé), affine_url, nocodb_id, warnings}
```

**Gestion d'erreurs / cohérence :**
- Étape 7 échoue → rien créé, retour erreur claire
- Étape 9/10 échoue après 7 réussi → marquer la scène `status=orphan` dans metadata, ne pas laisser de scène fantôme silencieuse ; retourner un warning explicite
- Tous les appels HTTP : timeout 10 s, retry exponentiel 3 tentatives max
- Opérations Postgres multiples : transaction SQL

## 9. Variables d'environnement (`.env.example`)

```bash
# --- PostgreSQL (user DÉDIÉ mcp_excalidraw, pas excalidraw_backend) ---
DATABASE_URL=postgresql://mcp_excalidraw:<PASSWORD>@10.0.1.23:5432/excalidraw_storage

# --- Excalidraw ---
EXCALIDRAW_BACKEND_URL=http://excalidraw-backend:8080   # interne Docker
EXCALIDRAW_FRONTEND_URL=https://excalidraw.agnisolution.fr

# --- NocoDB ---
NOCODB_URL=https://nocodb.agnisolution.fr
NOCODB_TOKEN=<TOKEN>
NOCODB_BASE_OPEPARTNER=boexlzlohgueed1

# --- AFFiNE ---
AFFINE_API_URL=https://affine.agnisolution.fr
AFFINE_WORKSPACE_OPEPARTNER=3869ae28-9638-4390-a28d-905ff5c563d6
AFFINE_TOKEN=<TOKEN>

# --- Auth du MCP ---
MCP_AUTH_MODE=<oauth|forwardauth_bearer>
MCP_BEARER_TOKEN=<TOKEN>            # si mode bearer
AUTH_SERVICE_URL=https://exca-auth.agnisolution.fr

# --- Config ---
DEFAULT_USER_ID=1
LOG_LEVEL=INFO
LOG_FILE=/var/log/mcp-excalidraw/app.log
RATE_LIMIT_PER_MIN=30
```

**Aucune valeur réelle dans le repo.** `.env` en gitignore. Valeurs réelles dans Coolify (variables d'environnement du service).

## 10. Plan de développement par phases

**Ne pas tout faire d'un coup. Valider chaque phase avant la suivante.**

### Phase H.1 — Fondations (sécurité d'abord)
1. Structure projet + pyproject + Dockerfile + .gitignore + .env.example
2. `infra/sql/03_mcp_user.sql` : création user `mcp_excalidraw` à droits minimaux + exécution sur le VPS
3. `config.py` : chargement + validation stricte des env vars
4. `clients/database.py` : pool Postgres, requêtes paramétrées, test de connexion avec le user dédié
5. **Validation** : connexion Postgres OK avec le user restreint, droits vérifiés (ne peut PAS faire de DDL)

### Phase H.2 — Chiffrement (point le plus risqué)
1. Étudier le code source frontend Excalidraw (repo GitHub) : format exact compression + AES-GCM
2. `crypto.py` : implémenter encrypt/decrypt compatibles
3. `tests/test_crypto.py` : round-trip — créer une scène chiffrée par le MCP, vérifier qu'elle s'ouvre **à l'identique** dans le frontend, et qu'une scène créée par le frontend se déchiffre côté MCP
4. **Validation** : compatibilité bidirectionnelle prouvée par test. Ne PAS avancer tant que ce n'est pas vert.

### Phase H.3 — Clients d'intégration
1. `clients/excalidraw.py` : POST/GET backend (interne :8080)
2. `clients/nocodb.py` : find/create/insert via API NocoDB
3. `clients/affine.py` : investiguer API/GraphQL AFFiNE, créer un doc test
4. **Validation** : chaque client testé isolément

### Phase H.4 — Outils CRUD + orchestration
1. `tools/scenes.py` : create/get/update/list/delete_scene
2. `orchestration.py` : séquence complète + gestion d'erreurs
3. `tests/test_orchestration.py`
4. **Validation** : créer une scène simple bout-en-bout (chiffrée, en BDD, traçée NocoDB)

### Phase H.5 — Templates frameworks
1. Créer les templates JSON (BMC, PESTEL, SWOT, VPC, organigramme, plan 90j) — manuellement via le frontend Excalidraw puis export, ou programmatiquement
2. `templates/manager.py` : fill_template avec placeholders `{{VARIABLE}}`
3. `tools/frameworks.py` : create_bmc/pestel/swot/...
4. **Validation** : un BMC complet généré, ouvert dans le frontend, lisible et correct

### Phase H.6 — Déploiement remote
1. Dockerfile finalisé + healthcheck `/health`
2. Déploiement Coolify + sous-domaine `mcp-excalidraw.agnisolution.fr` + Traefik (SSL, rate limit)
3. Mise en place de l'auth (selon voie retenue en H.1)
4. **Validation** : endpoint accessible en HTTPS, auth fonctionnelle, healthcheck vert

### Phase H.7 — Intégration Claude.ai + tests cross-device
1. Ajout dans Claude.ai Connectors (URL du MCP)
2. Test depuis web, puis Mac, puis iPhone : `"Crée un BMC pour Client TestSAS"`
3. Vérifier : scène chiffrée en BDD, lisible dans le frontend, ligne NocoDB, doc AFFiNE
4. Test `list_scenes`, `update_scene`, `delete_scene`
5. **Validation** : workflow complet fonctionnel depuis un mobile

## 11. Règles pour Claude Code

- **Sécurité d'abord** : phases H.1 (user dédié) et H.2 (chiffrement) sont des préalables. Ne pas les contourner pour "aller plus vite".
- **Jamais de credentials dans Git** : `.env.example` avec placeholders versionné, `.env` jamais. Vérifier `.gitignore` avant chaque commit.
- **Demander validation** avant tout déploiement Coolify qui expose un service public.
- **Tester chaque phase** avant la suivante. Pas de big bang.
- **Requêtes SQL paramétrées** : audit à chaque écriture de requête.
- **Documenter au fil de l'eau** : README + docstrings, pas "à la fin".
- **Pas de remise en cause des arbitrages** : remote HTTPS + chiffrement option A + Python/FastMCP sont décidés.
- Si un point technique bloque (compat OAuth, format chiffrement), **investiguer et proposer**, ne pas supposer silencieusement.

## 12. Références

- Architecture déployée : `docs/ARCHITECTURE.md`
- Spec technique détaillée : `MCP-EXCALIDRAW-TECHNICAL-BRIEF.md` (⚠️ vérifier que les credentials y sont en placeholders)
- Repo frontend Excalidraw (pour le format de chiffrement) : `github.com/christophe39/excalidraw`
- FastMCP : https://github.com/jlowin/fastmcp
- MCP spec (remote, auth) : https://modelcontextprotocol.io/
- Workspace AFFiNE OPEPARTNER : `3869ae28-9638-4390-a28d-905ff5c563d6`
- Container Postgres : `pk4s888o4wkc8ogokg0sg840`, base `excalidraw_storage`

---

*Brief généré le 16 mai 2026. Arbitrages : MCP remote HTTPS, chiffrement E2E option A, Python/FastMCP. À tenir à jour au fil du projet.*
