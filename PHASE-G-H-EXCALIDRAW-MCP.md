# PHASE G + H — Excalidraw self-hosted + MCP custom

> Brief de contexte pour Claude Code, à lire après le `CLAUDE.md` principal. Couvre le déploiement Excalidraw sur le VPS et le développement du MCP custom qui le pilotera.

## 📍 Où on en est

**Phases A à F : terminées.** En particulier :

- Workspace AFFiNE `OPEPARTNER` créé et structuré (`3869ae28-9638-4390-a28d-905ff5c563d6`)
- Base PostgreSQL `opepartner` créée dans le container `pk4s888o4wkc8ogokg0sg840` avec :
  - 14 tables MVP + 2 vues SQL
  - User dédié `nocodb_opepartner`
  - UUID en clés primaires
  - Toutes les FK avec stratégies `ON DELETE CASCADE / SET NULL`
  - Index sur FK + colonnes business
  - Triggers `updated_at` automatiques
  - CHECK constraints sur énumérations
- Base visible et lisible dans NocoDB (Base ID `boexlzlohgueed1`)
- Table `schemas_excalidraw` prête à recevoir les schémas générés

**À faire : G (déploiement Excalidraw) + H (MCP custom).**

## 🎯 Objectif des phases G + H

Mettre en place un **pipeline complet** où un prompt dans Claude (sur n'importe quel device) génère un schéma Excalidraw, le stocke sous un domaine sous notre contrôle, l'enregistre dans la BDD `opepartner`, et l'embed dans un doc AFFiNE — le tout en une seule action automatique.

Exemple de workflow cible :

> **Christophe** (dans une conversation Claude) : *"Crée un BMC pour Client Dupont SAS"*
>
> **Claude** appelle le MCP custom :
> 1. Vérifie/crée la ligne `clients` (Dupont SAS) dans Postgres
> 2. Génère la scène Excalidraw (JSON) selon un template BMC
> 3. Push la scène dans le storage backend Excalidraw → obtient un ID + URL persistante
> 4. Insère une ligne dans `schemas_excalidraw` avec tous les liens
> 5. Crée un doc AFFiNE dans le bon folder client avec l'image preview + lien d'édition
> 6. Retourne dans le chat : le lien éditable + le lien du doc AFFiNE

## 🏗️ Architecture cible globale

```
┌─────────────────────────────────────────────────────────────────┐
│ VPS Hostinger 69.62.110.207 — Coolify + Traefik + Cloudflare   │
│                                                                  │
│  ┌──────────────────────────────┐                               │
│  │ Excalidraw frontend (React)  │  ← excalidraw.opepartner.fr   │
│  │ Container Docker statique    │                               │
│  └────────────┬─────────────────┘                               │
│               │                                                  │
│               │ POST /scenes, GET /scenes/{id}                  │
│               ▼                                                  │
│  ┌──────────────────────────────┐                               │
│  │ excalidraw-storage-backend   │  ← exca-api.opepartner.fr     │
│  │ (Node.js, stockage JSON)     │  (interne, pas public)        │
│  │ Base : Redis ou Postgres     │                               │
│  └──────────────────────────────┘                               │
│                                                                  │
│  ┌──────────────────────────────┐                               │
│  │ MCP custom Excalidraw        │  ← mcp-excalidraw.opepartner.fr│
│  │ (Python FastMCP ou TS SDK)   │  (HTTPS pour Claude.ai cross- │
│  │ Container Docker             │   device)                     │
│  └──────┬───────────────────┬───┘                               │
│         │                   │                                    │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌─────────────────┐  ┌──────────────────┐                      │
│  │ Postgres        │  │ AFFiNE API       │                      │
│  │ opepartner db   │  │ workspace        │                      │
│  │ (pk4s888...)    │  │ OPEPARTNER       │                      │
│  └─────────────────┘  └──────────────────┘                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
        ▲
        │ HTTPS
        │
   ┌────┴─────────────────────────────────────┐
   │ Claude Desktop / Claude.ai web / iOS     │
   │ → utilise mcp-excalidraw.opepartner.fr  │
   │   ajouté dans Connectors Claude.ai       │
   └──────────────────────────────────────────┘
```

## 🔧 Phase G — Déploiement Excalidraw self-hosted

### G.1 — Décision : domaine et sous-domaines

**Choix de domaine** : utiliser **`opepartner.fr`** (sous-domaines `excalidraw.opepartner.fr`, `mcp-excalidraw.opepartner.fr`, etc.).

Raison : cohérence avec la stratégie de migrabilité — quand viendra le moment de migrer OPEPARTNER sur un VPS dédié, on changera juste les DNS de `opepartner.fr` sans toucher au domaine principal `agnisolution.fr`.

Si `opepartner.fr` n'est pas encore actif chez Cloudflare, alternative : commencer avec `excalidraw.agnisolution.fr` puis migrer le DNS plus tard.

**À vérifier en première étape** : 

```bash
ssh root@69.62.110.207 "nslookup opepartner.fr"
```

### G.2 — Stack Excalidraw

Deux services Docker à déployer :

**Service 1 : Excalidraw frontend**

- Image : `excalidraw/excalidraw:latest`
- Statique (HTML/JS servi par nginx)
- Port interne : 80
- Variables d'environnement clés :
  - `VITE_APP_BACKEND_V2_GET_URL=https://exca-api.opepartner.fr/api/v2/scenes/`
  - `VITE_APP_BACKEND_V2_POST_URL=https://exca-api.opepartner.fr/api/v2/scenes`
  - `VITE_APP_DISABLE_TRACKING=true`
- Pas d'auth Excalidraw native (on protège via Traefik au niveau du sous-domaine si nécessaire)
- Ressources estimées : 50 MB RAM, CPU négligeable

**Service 2 : excalidraw-storage-backend**

- Repo recommandé : `https://github.com/kitsteam/excalidraw-storage-backend` (Docker image disponible)
- Service Node.js qui stocke les scènes
- Storage backend : Redis OU Postgres
  - **Recommandation : utiliser Postgres existant** (notre base `opepartner` peut accueillir une table `excalidraw_storage` dédiée, OU on crée une base distincte `excalidraw_data`)
- Port interne : 8080 (à confirmer dans la doc du repo)
- Variables d'environnement :
  - `STORAGE_URI=postgresql://nocodb_opepartner:***@host:5432/opepartner` (si on partage la base)
  - Ou config Redis si on choisit Redis
- Ressources estimées : 100-150 MB RAM

**Décision à prendre** : Redis vs Postgres pour le storage backend ?
- **Redis** : plus rapide, mais nouveau container à monitorer + backup
- **Postgres** : on réutilise l'existant, backup centralisé, mais une table de stockage opaque dans `opepartner` peut être moins propre

**Recommandation** : Postgres dans une base dédiée `excalidraw_storage` du même container (`pk4s888o4wkc8ogokg0sg840`). Cloisonnement propre, backup unifié, pas de container supplémentaire.

### G.3 — Configuration Traefik / Coolify

Labels Traefik à prévoir pour chaque service. Coolify gère normalement ça via son UI, mais il faut s'assurer :

- Certificat SSL automatique Let's Encrypt sur les sous-domaines
- Route public pour `excalidraw.opepartner.fr` → frontend
- Route public pour `exca-api.opepartner.fr` → storage backend
- **Auth basic Traefik** sur les deux sous-domaines pour la confidentialité OPEPARTNER (clients sensibles). User/password à stocker en variable d'environnement Coolify.

Alternative à l'auth basic : **Authentik** ou **Cloudflare Access** si déjà déployé.

### G.4 — Sécurité

Mesures à appliquer :

1. **IDs de scènes longs et cryptographiquement aléatoires** (paramètre du storage backend) — pas devinables par énumération
2. **Auth Traefik basic** sur les sous-domaines (au moins le temps de finaliser)
3. **Pas de listing** : pas d'endpoint qui liste toutes les scènes publiquement
4. **CORS configuré** strictement : seuls les sous-domaines de confiance peuvent appeler l'API
5. **Logs** : log tous les accès dans Coolify pour audit

### G.5 — Tests Phase G

À la fin de la phase G, tester manuellement :

1. Ouvrir `https://excalidraw.opepartner.fr` dans un navigateur
2. Auth basic accepte les credentials configurés
3. Créer une scène simple (quelques formes)
4. Cliquer "Share to link" → vérifier que l'URL générée est sous `excalidraw.opepartner.fr/#json=...`
5. Copier le lien, fermer le navigateur, le rouvrir dans un autre navigateur (incognito) → la scène se charge
6. Vérifier en base : la scène est bien stockée dans la base/table de storage

### G.6 — Livrables Phase G

- `infra/docker-compose/excalidraw/docker-compose.yml` versionné Git
- `infra/docker-compose/excalidraw/.env.example` avec toutes les variables (sans valeurs sensibles)
- `infra/sql/02_init_excalidraw_storage.sql` si on utilise Postgres dédié
- Documentation `docs/excalidraw-deployment.md` : procédure de déploiement et restauration

## 🤖 Phase H — MCP custom Excalidraw

### H.1 — Choix techniques

**Langage** : **Python avec FastMCP** (recommandation principale)

Justification :
- FastMCP est mature, syntaxe très concise
- Excellent écosystème pour JSON manipulation, SQL (psycopg2 / asyncpg), HTTP client
- Christophe est confortable avec Python en lecture (et apprendra vite)
- TypeScript reste possible si préférence affichée

**Type de MCP** : **Remote HTTPS** (PAS stdio local)

Justification : c'est précisément ce qui permet l'usage cross-device. Une fois ajouté dans les Connectors Claude.ai, le MCP est accessible depuis web, Desktop Mac, iOS, iPad.

### H.2 — Structure du projet MCP

```
mcp-excalidraw/
├── pyproject.toml          # dépendances (fastmcp, psycopg2, httpx, etc.)
├── Dockerfile
├── docker-compose.yml      # pour déploiement Coolify
├── .env.example
├── README.md
├── src/
│   ├── __init__.py
│   ├── server.py           # entry point FastMCP
│   ├── config.py           # chargement env vars
│   ├── clients/
│   │   ├── excalidraw.py   # client storage backend
│   │   ├── postgres.py     # client BDD opepartner
│   │   └── affine.py       # client API AFFiNE
│   ├── tools/
│   │   ├── scenes.py       # create/get/update/list/delete_scene
│   │   ├── templates.py    # create_bmc, create_pestel, create_swot
│   │   └── exports.py      # export_png, export_svg
│   ├── templates/
│   │   ├── bmc_template.json     # template JSON Excalidraw BMC vierge
│   │   ├── pestel_template.json
│   │   └── swot_template.json
│   └── utils/
│       └── orchestration.py  # logique upsert client/mission + lien AFFiNE
└── tests/
    └── test_tools.py
```

### H.3 — Variables d'environnement du MCP

```bash
# Postgres opepartner
POSTGRES_URL=postgresql://nocodb_opepartner:***@host:5432/opepartner

# Excalidraw storage backend
EXCALIDRAW_BACKEND_URL=https://exca-api.opepartner.fr
EXCALIDRAW_FRONTEND_URL=https://excalidraw.opepartner.fr
EXCALIDRAW_AUTH_USER=***  # si auth basic Traefik
EXCALIDRAW_AUTH_PASS=***

# AFFiNE
AFFINE_API_URL=https://affine.agnisolution.fr
AFFINE_TOKEN=***
AFFINE_WORKSPACE_OPEPARTNER=3869ae28-9638-4390-a28d-905ff5c563d6

# n8n (pour notifications éventuelles)
N8N_WEBHOOK_BASE_URL=https://n8n.agnisolution.fr/webhook
```

**Aucun hardcoding** dans le code. Tout doit pouvoir être modifié via `.env` ou variables Coolify.

### H.4 — Outils MCP à implémenter

**Outils CRUD de base :**

```python
@mcp.tool()
def create_scene(
    json_data: dict,
    title: str,
    contexte: Literal["OPEPARTNER", "CaloCalc-Doc"],
    document_type: str,  # "BMC_visuel", "PESTEL_visuel", "Organigramme", etc.
    client_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    tags: List[str] = None,
    confidentiel: bool = True
) -> dict:
    """
    Crée une scène Excalidraw, l'enregistre dans la BDD, et crée le doc AFFiNE associé.
    Retourne edit_url, preview_url, affine_doc_id.
    """
```

```python
@mcp.tool()
def get_scene(excalidraw_id: str) -> dict:
    """Récupère le JSON actuel d'une scène."""

@mcp.tool()
def update_scene(excalidraw_id: str, json_data: dict) -> dict:
    """Met à jour une scène existante. Incrémente la version. Garde le même ID."""

@mcp.tool()
def list_scenes(
    contexte: Optional[str] = None,
    client_id: Optional[str] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20
) -> List[dict]:
    """Liste les scènes avec filtres multi-critères."""

@mcp.tool()
def delete_scene(excalidraw_id: str, confirm: bool = False) -> dict:
    """Supprime une scène. Demande confirmation explicite."""
```

**Outils export :**

```python
@mcp.tool()
def export_scene_png(excalidraw_id: str, scale: int = 2) -> str:
    """Génère un PNG haute résolution. Retourne URL ou base64."""

@mcp.tool()
def export_scene_svg(excalidraw_id: str) -> str:
    """Génère un SVG vectoriel."""
```

**Outils templates consulting (forte valeur ajoutée OPEPARTNER) :**

```python
@mcp.tool()
def create_bmc(
    client_nom: str,
    mission_id: Optional[str] = None,
    contenus_cases: Optional[dict] = None  # dict avec 9 clés : segments, proposition_valeur, etc.
) -> dict:
    """
    Crée un Business Model Canvas pré-structuré. Si contenus_cases est fourni,
    pré-remplit les cases. Sinon, génère un BMC vierge à compléter.
    Upsert automatiquement le client dans la table clients si nécessaire.
    """

@mcp.tool()
def create_pestel(client_nom: str, mission_id: Optional[str] = None,
                  donnees: Optional[dict] = None) -> dict:
    """Crée une analyse PESTEL pré-structurée."""

@mcp.tool()
def create_swot(client_nom: str, mission_id: Optional[str] = None,
                donnees: Optional[dict] = None) -> dict:
    """Crée un SWOT pré-structuré."""

@mcp.tool()
def create_organigramme(
    client_nom: str,
    structure: dict  # arbre hiérarchique : {nom, role, enfants: [...]}
) -> dict:
    """Génère un organigramme Excalidraw depuis un arbre JSON."""

@mcp.tool()
def create_chaine_valeur(client_nom: str, donnees: dict) -> dict:
    """Génère une chaîne de valeur Porter."""
```

### H.5 — Logique d'orchestration interne (clé)

Chaque appel `create_scene` (ou ses dérivés templates) doit **orchestrer plusieurs systèmes en une transaction logique** :

```
1. SI contexte == "OPEPARTNER" ET client_nom fourni :
   - SELECT id FROM clients WHERE nom_entreprise = $client_nom
   - SI introuvable :
       → log un warning "Nouveau client à créer"
       → INSERT INTO clients (nom_entreprise) VALUES ($client_nom) RETURNING id
       → retourne le nouvel UUID
   - Récupère client_id

2. POST sur EXCALIDRAW_BACKEND_URL/api/v2/scenes avec json_data
   → récupère excalidraw_id

3. INSERT INTO schemas_excalidraw (
       excalidraw_id, client_id, mission_id, document_type, document_title,
       status, version, edit_url, preview_url, confidentiel, tags
   )
   → récupère l'UUID du nouvel enregistrement schemas_excalidraw

4. Appel API AFFiNE :
   - Crée un doc dans le workspace OPEPARTNER
   - Folder cible : 03 — Clients / Missions / [client_nom]
   - Contenu du doc : 
     * Heading "[document_type] — [client_nom]"
     * Image embed pointant sur preview_url
     * Lien éditable vers edit_url
     * Métadonnée HTML invisible : <!-- excalidraw-id: $excalidraw_id -->
   → récupère affine_doc_id

5. UPDATE schemas_excalidraw SET affine_doc_id = $affine_doc_id WHERE id = ...

6. Retour :
   {
     "excalidraw_id": "...",
     "edit_url": "https://excalidraw.opepartner.fr/#json=...",
     "preview_url": "https://exca-api.opepartner.fr/api/v2/scenes/{id}/preview.png",
     "affine_doc_id": "...",
     "affine_url": "https://affine.agnisolution.fr/...",
     "warnings": ["Nouveau client Dupont SAS créé en base"]
   }
```

**Gestion erreurs** :

- Si une étape échoue après une étape précédente réussie, **rollback** logique : 
  - Si AFFiNE échoue après insert SQL : marquer la ligne `schemas_excalidraw` avec `status=orphan` (pas de doc AFFiNE)
  - Si SQL échoue après push Excalidraw : supprimer la scène Excalidraw pour ne pas laisser de scène orpheline
- Tous les appels HTTP avec retry exponentiel (3 tentatives max)
- Timeouts raisonnables (10 s par appel)

### H.6 — Templates JSON Excalidraw

Pré-définir dans `src/templates/` les structures JSON Excalidraw pour chaque framework.

**Exemple `bmc_template.json`** : un canvas avec 9 rectangles disposés en grille selon le standard Osterwalder, chacun avec un titre coloré et une zone de texte vide ou pré-remplie.

Pour générer ces templates initiaux, deux approches :
1. **Manuelle** : créer chaque template dans Excalidraw une fois (UI), exporter en JSON, sauver dans `src/templates/`
2. **Programmatique** : générer le JSON directement depuis du code Python en construisant la structure d'éléments Excalidraw

La voie 1 est plus rapide pour démarrer. Voie 2 est plus robuste pour évolutions.

**Référence** : le doc AFFiNE `📋 BMC · Contenu type des 9 cases` (dans le workspace OPEPARTNER, folder Templates BMC) contient les questions pédagogiques de chaque case — utile pour pré-remplir les zones de texte d'aide dans le template.

### H.7 — Déploiement du MCP

- Dockerfile basé sur `python:3.12-slim`
- Service Coolify avec sous-domaine `mcp-excalidraw.opepartner.fr`
- Variables d'environnement gérées dans Coolify (jamais dans le repo Git)
- Healthcheck endpoint `/health` que Coolify peut monitorer
- Logs structurés JSON pour debug

### H.8 — Configuration côté Claude.ai (Étape I)

Une fois le MCP déployé :

1. Aller dans Claude.ai > Settings > Connectors
2. Add custom connector → URL `https://mcp-excalidraw.opepartner.fr/mcp`
3. Token d'authentification si configuré côté MCP
4. Test : vérifier que les outils apparaissent dans une conversation

À partir de là, **tous les devices** (web, Desktop Mac, iOS, iPad, iPhone) ont accès au MCP. Magique.

### H.9 — Tests Phase H

À la fin de la phase H, tester :

1. **Test outil create_scene basique** : créer une scène simple avec quelques formes, vérifier qu'elle apparaît dans Excalidraw et dans la table `schemas_excalidraw`

2. **Test orchestration complète create_bmc** :
   - Prompt : *"Crée un BMC pour Client TestSAS"*
   - Vérifier : client créé dans `clients`, scène créée dans Excalidraw, ligne dans `schemas_excalidraw`, doc créé dans AFFiNE sous le bon folder

3. **Test update_scene** :
   - Modifier la scène créée
   - Vérifier que `version` est incrémentée et que `updated_at` est mis à jour

4. **Test cross-device** :
   - Ouvrir Claude.ai sur iPhone
   - Faire un prompt qui appelle le MCP
   - Vérifier que la scène se crée bien

5. **Test list_scenes avec filtres** :
   - Lister les scènes du client TestSAS
   - Lister par document_type
   - Lister les confidentielles

### H.10 — Livrables Phase H

- Code complet du MCP dans `mcp-excalidraw/` (versionné Git)
- Tests automatisés couvrant les outils principaux
- Documentation `mcp-excalidraw/README.md` :
  - Installation locale dev
  - Configuration des variables d'env
  - Lancement
  - Liste des outils exposés avec exemples
- Documentation `docs/mcp-deployment.md` : procédure de déploiement Coolify

## 🔗 Liens et données critiques

### Infrastructure

- **VPS SSH** : `ssh root@69.62.110.207`
- **Postgres OPEPARTNER** : 
  - Container : `pk4s888o4wkc8ogokg0sg840`
  - DB : `opepartner`
  - User : `nocodb_opepartner`
  - Schema : `public`
  - Host interne : `10.0.1.23:5432` (depuis autres containers)
- **AFFiNE** : `https://affine.agnisolution.fr`
- **Workspace OPEPARTNER** : `3869ae28-9638-4390-a28d-905ff5c563d6`
- **NocoDB** : `https://nocodb.agnisolution.fr`
- **NocoDB Base OPEPARTNER** : `boexlzlohgueed1`

### Tables clés de la BDD

- `clients` (id UUID, nom_entreprise, secteur_activite, statut, ...)
- `missions` (id UUID, client_id FK, titre_mission, statut, ...)
- `schemas_excalidraw` (excalidraw_id, client_id FK, mission_id FK, document_type, edit_url, preview_url, affine_doc_id, version, status, ...)

### Stratégie de migrabilité — règles d'or à respecter

1. **Sous-domaines logiques** sous `opepartner.fr` (pas `agnisolution.fr` pour les composants OPEPARTNER)
2. **Variables d'environnement** : zéro hardcoding
3. **Pas de logique métier dans NocoDB UI** : tout en SQL ou dans le MCP
4. **Documentation systématique** : chaque service a son README
5. **Versioning Git complet** : code, configs, scripts SQL, docker-compose

## ⚠️ Points d'attention pour Claude Code

- **Ne JAMAIS commit de credentials** dans le repo Git. Utiliser `.env.example` versionné + `.env` ignoré.
- **Toujours demander validation** avant un déploiement Coolify qui crée un service public
- **Tester localement d'abord** quand possible (docker-compose up local, postgres local)
- **Logger abondamment** dans le MCP, surtout pour le debugging cross-device
- **Documenter au fur et à mesure** : pas de "on documentera à la fin"
- Le password Postgres `nocodb_opepartner` actuel doit être **changé** avant tout déploiement public — utiliser un mot de passe fort généré (`openssl rand -base64 32`)

## 🗺️ Plan de progression suggéré

Découper en sessions courtes pour ne pas surcharger :

**Session 1 (G.1 → G.5)** — Déploiement Excalidraw frontend + storage backend
1. Vérifier DNS opepartner.fr
2. Préparer docker-compose Excalidraw
3. Décider stockage backend (Postgres recommandé)
4. Créer base/table de storage si nécessaire
5. Déployer via Coolify
6. Tester manuellement

**Session 2 (H.1 → H.3)** — Bootstrap MCP
1. Setup pyproject.toml + structure de dossiers
2. Implementer config.py et clients (Postgres, Excalidraw, AFFiNE)
3. Tester chaque client individuellement

**Session 3 (H.4 → H.5)** — Outils CRUD + orchestration
1. `create_scene`, `get_scene`, `update_scene`, `list_scenes`
2. Logique d'orchestration upsert + AFFiNE
3. Tests unitaires

**Session 4 (H.6)** — Templates consulting
1. Templates JSON BMC, PESTEL, SWOT
2. Outils `create_bmc`, `create_pestel`, `create_swot`

**Session 5 (H.7 → H.9)** — Déploiement et tests cross-device
1. Dockerfile + déploiement Coolify
2. Ajout dans Connectors Claude.ai
3. Tests bout-en-bout depuis iPhone

---

*Document généré pour Claude Code. À tenir à jour au fil du projet.*
