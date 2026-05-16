# MCP Custom Excalidraw — Brief technique complet

> **Document destiné à Claude Desktop pour le développement du MCP custom**  
> **Date** : 16 mai 2026  
> **Auteur** : Christophe Martin + Claude Code  
> **Projet** : OPEPARTNER — Système de génération de schémas stratégiques

---

## 📋 Table des matières

1. [Vision et objectifs](#1-vision-et-objectifs)
2. [Architecture technique globale](#2-architecture-technique-globale)
3. [Base de données PostgreSQL](#3-base-de-données-postgresql)
4. [APIs et endpoints disponibles](#4-apis-et-endpoints-disponibles)
5. [Système de templates Excalidraw](#5-système-de-templates-excalidraw)
6. [MCP existants et configuration](#6-mcp-existants-et-configuration)
7. [Spécifications du MCP custom à développer](#7-spécifications-du-mcp-custom-à-développer)
8. [Workflow cible et cas d'usage](#8-workflow-cible-et-cas-dusage)
9. [Contraintes et bonnes pratiques](#9-contraintes-et-bonnes-pratiques)
10. [Variables d'environnement et credentials](#10-variables-denvironnement-et-credentials)

---

## 1. Vision et objectifs

### 1.1. Contexte métier

**OPEPARTNER** est une activité de conseil stratégique qui produit des livrables documentaires pour ses clients :
- Business Model Canvas (BMC)
- Analyses PESTEL, SWOT
- Organigrammes
- Plans d'action 90 jours
- Chaînes de valeur

**Problème actuel** : Création manuelle de ces schémas dans Excalidraw, puis copy/paste dans des documents.

**Solution cible** : Génération automatique des schémas depuis des prompts Claude, avec :
- Templates pré-définis (BMC, PESTEL, SWOT, etc.)
- Stockage pérenne dans Postgres
- Traçabilité dans NocoDB (client, mission, type de document)
- Documentation automatique dans AFFiNE

### 1.2. Objectifs du MCP custom

Le MCP custom Excalidraw doit permettre de :

1. **Créer des schémas depuis des templates** :
   - `create_bmc(client, data)` → Génère un BMC pré-rempli
   - `create_pestel(client, data)` → Génère une analyse PESTEL
   - `create_swot(client, data)` → Génère un SWOT

2. **Manipuler les schémas existants** :
   - `get_scene(id)` → Récupère le JSON d'une scène
   - `update_scene(id, data)` → Modifie une scène existante
   - `list_scenes(filters)` → Liste les scènes (par client, par type, par date)

3. **Intégrer avec l'écosystème** :
   - Insert automatique dans NocoDB (table `Schemas_Excalidraw`)
   - Création de documents dans AFFiNE (workspace OPEPARTNER)
   - Liaison avec les entités métier (Clients, Missions)

4. **Respecter les contraintes** :
   - Traçabilité : `created_by` (user ID) sur chaque scène
   - Templates : `template_id` pour savoir quel template a été utilisé
   - Métadonnées : `client_id`, `mission_id`, `document_type`, `status`

---

## 2. Architecture technique globale

### 2.1. Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        OPEPARTNER Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Claude Desktop / Claude.ai                                     │
│           ↓                                                     │
│  ┌──────────────────────────────────────────────┐              │
│  │  MCP Custom Excalidraw (À DÉVELOPPER)        │              │
│  │  - create_bmc(), create_pestel(), etc.       │              │
│  │  - Manipulation templates                     │              │
│  │  - Intégration NocoDB + AFFiNE               │              │
│  └──────────────────────────────────────────────┘              │
│           ↓         ↓         ↓                                │
│  ┌────────────┐  ┌──────┐  ┌──────────┐                       │
│  │ Excalidraw │  │ Noco │  │ AFFiNE   │                       │
│  │  Backend   │  │  DB  │  │          │                       │
│  └────────────┘  └──────┘  └──────────┘                       │
│           ↓                                                     │
│  ┌─────────────────────────────────────┐                      │
│  │  PostgreSQL (excalidraw_storage)     │                      │
│  │  - keyv (scènes)                     │                      │
│  │  - utilisateurs                       │                      │
│  │  - templates                          │                      │
│  └─────────────────────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. Services déployés

| Service | URL | Rôle | Stack |
|---------|-----|------|-------|
| **Excalidraw Frontend** | https://excalidraw.agnisolution.fr | Interface utilisateur | React (buildé) |
| **Excalidraw Backend** | http://backend:8080 (interne) | Stockage scènes (API REST) | Node.js Express |
| **Proxy Adaptateur** | https://exca-api.agnisolution.fr | Traduction URLs API | Nginx |
| **Service Auth** | https://exca-auth.agnisolution.fr | ForwardAuth Traefik | Node.js Express |
| **NocoDB** | https://nocodb.agnisolution.fr | Base métier (Clients, Missions, etc.) | Vue.js + Express |
| **AFFiNE** | https://affine.agnisolution.fr | Documentation et notes | Rust + TypeScript |
| **PostgreSQL** | 10.0.1.23:5432 (interne) | Base de données | Postgres 17 Alpine |

### 2.3. Réseau Docker

Tous les services sont sur le réseau Docker **`coolify`** (external).

**Noms de services réseau** :
- `excalidraw-frontend` (container: `frontend-o8wsgoowkcogkgk0g8o4g8s0`)
- `excalidraw-backend` (container: `backend-o8wsgoowkcogkgk0g8o4g8s0`)
- `excalidraw-proxy` (container: `proxy-o8wsgoowkcogkgk0g8o4g8s0`)
- `l400k4gwo0kgw440w4848gc0-094552480011` (service auth, nom Coolify)
- `pk4s888o4wkc8ogokg0sg840` (PostgreSQL)

---

## 3. Base de données PostgreSQL

### 3.1. Connexion

```
Host: 10.0.1.23 (interne Docker) ou 69.62.110.207 (externe, mais port fermé)
Port: 5432
Database: excalidraw_storage
User: excalidraw_backend
Password: ***VOIR_FICHIER_.ENV_DU_SERVICE***
```

### 3.2. Schéma des tables

#### Table `keyv` (scènes Excalidraw)

Stocke les scènes Excalidraw avec leurs métadonnées.

```sql
CREATE TABLE keyv (
  key VARCHAR(255) PRIMARY KEY,           -- ID de la scène (ex: 'abc123def456')
  value JSONB NOT NULL,                   -- JSON complet de la scène Excalidraw
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Colonnes ajoutées pour tracking
  created_by INTEGER REFERENCES utilisateurs(id),
  template_id INTEGER REFERENCES templates(id),
  created_at_tracked TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_keyv_created_by ON keyv(created_by);
CREATE INDEX idx_keyv_template_id ON keyv(template_id);
CREATE INDEX idx_keyv_created_at_tracked ON keyv(created_at_tracked);
```

**Colonnes importantes** :
- `key` : ID unique de la scène (12 caractères alphanumériques)
- `value` : JSON Excalidraw complet (éléments, appState, files)
- `created_by` : ID de l'utilisateur qui a créé la scène
- `template_id` : ID du template utilisé (NULL si création manuelle)
- `metadata` : JSONB libre pour stocker `client_id`, `mission_id`, `document_type`, etc.

**Exemple de métadonnées** :
```json
{
  "client_id": 42,
  "mission_id": 15,
  "document_type": "BMC",
  "document_title": "Business Model Canvas - Dupont SAS",
  "status": "draft",
  "tags": ["strategy", "consulting"]
}
```

---

#### Table `utilisateurs` (authentification)

```sql
CREATE TABLE utilisateurs (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,    -- bcrypt hash
  nom VARCHAR(100),
  actif BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ
);
```

**Utilisateur actuel** :
- ID: `1`
- Email: `cmartin@agniconsult.fr`
- Nom: `Christophe Martin`

---

#### Table `templates` (templates Excalidraw)

```sql
CREATE TABLE templates (
  id SERIAL PRIMARY KEY,
  nom VARCHAR(100) UNIQUE NOT NULL,       -- 'BMC', 'PESTEL', 'SWOT'
  description TEXT,
  excalidraw_json JSONB NOT NULL,         -- JSON complet du template
  thumbnail_url TEXT,
  categorie VARCHAR(50),                   -- 'strategy', 'marketing', 'project'
  tags TEXT[],                             -- Array de tags
  created_by INTEGER REFERENCES utilisateurs(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  version INTEGER DEFAULT 1,
  actif BOOLEAN DEFAULT true
);
```

**Templates à créer** (manuellement pour l'instant) :
- `BMC` : Business Model Canvas (9 cases)
- `PESTEL` : Analyse macro-environnement (6 catégories)
- `SWOT` : Forces, Faiblesses, Opportunités, Menaces (4 quadrants)
- `Organigramme` : Structure hiérarchique
- `Value Proposition Canvas` : Proposition de valeur détaillée
- `Plan_90_jours` : Roadmap avec milestones

---

#### Vue `scenes_with_user` (helper)

```sql
CREATE VIEW scenes_with_user AS
SELECT
  k.key AS scene_id,
  k.value AS scene_data,
  k.created_by,
  u.email AS created_by_email,
  u.nom AS created_by_name,
  k.template_id,
  t.nom AS template_name,
  k.created_at_tracked,
  k.metadata
FROM keyv k
LEFT JOIN utilisateurs u ON k.created_by = u.id
LEFT JOIN templates t ON k.template_id = t.id
ORDER BY k.created_at_tracked DESC;
```

---

### 3.3. Base NocoDB (tables métier OPEPARTNER)

**Important** : NocoDB est connecté à une **autre base PostgreSQL** (probablement `Base_AgniConsult` ou `db_agni` dans le container `c0408wgcs08kc0w480koowcs`).

Le MCP devra utiliser l'**API NocoDB** (pas de connexion SQL directe) pour manipuler ces tables :

**Tables métier** :
- `Clients` (id, nom, secteur, contact_principal, created_at)
- `Missions` (id, client_id, nom, date_debut, date_fin, statut)
- `Schemas_Excalidraw` (id, excalidraw_id, edit_url, client_id, mission_id, document_type, template_id, created_by, status)
- `Business_Model_Canvas` (données structurées BMC)
- `PESTEL` (données structurées PESTEL)
- `SWOT` (données structurées SWOT)

**Schéma table `Schemas_Excalidraw` dans NocoDB** :

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | AutoNumber | ID unique |
| `excalidraw_id` | SingleLineText | ID de la scène dans keyv (ex: 'abc123def456') |
| `edit_url` | URL | Lien vers Excalidraw |
| `preview_url` | URL | Lien vers preview (optionnel) |
| `client_id` | LinkToAnotherRecord | FK vers Clients |
| `mission_id` | LinkToAnotherRecord | FK vers Missions |
| `document_type` | SingleSelect | 'BMC', 'PESTEL', 'SWOT', etc. |
| `document_title` | SingleLineText | Titre du document |
| `template_id` | Number | FK vers templates (Postgres) |
| `created_by` | Number | FK vers utilisateurs (Postgres) |
| `status` | SingleSelect | 'draft', 'review', 'validated' |
| `confidentiel` | Checkbox | true/false |
| `tags` | MultipleSelect | Tags libres |
| `affine_doc_id` | SingleLineText | ID du doc AFFiNE lié |
| `created_at` | DateTime | Date de création |
| `validated_at` | DateTime | Date de validation |
| `notes_internal` | LongText | Notes internes |

---

## 4. APIs et endpoints disponibles

### 4.1. Excalidraw Backend Storage API

**Base URL** : `http://excalidraw-backend:8080` (interne) ou via proxy `https://exca-api.agnisolution.fr`

#### Endpoints

**1. Créer une scène**

```http
POST /api/v2/scenes
Content-Type: application/json

{
  "version": 2,
  "source": "mcp-custom",
  "elements": [...],
  "appState": {...},
  "files": {}
}
```

**Réponse** :
```json
{
  "id": "abc123def456"
}
```

**2. Récupérer une scène**

```http
GET /api/v2/scenes/:id
```

**Réponse** :
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "...",
  "elements": [...],
  "appState": {...}
}
```

**3. Mettre à jour une scène**

```http
PUT /api/v2/scenes/:id
Content-Type: application/json

{
  "version": 2,
  "elements": [...]
}
```

**Note importante** : Le backend stocke le JSON tel quel dans Postgres (table `keyv`, colonne `value`). Les données sont chiffrées côté client avant envoi, le backend ne fait que stocker/retourner le blob.

---

### 4.2. Service d'authentification

**Base URL** : `https://exca-auth.agnisolution.fr`

#### Endpoints

**1. ForwardAuth (utilisé par Traefik)**

```http
GET /auth
Authorization: Basic <base64(email:password)>
```

**Réponse si OK** :
```
200 OK
X-Forwarded-User: 1
X-Forwarded-Email: cmartin@agniconsult.fr
X-Forwarded-Name: Christophe Martin
```

**2. Healthcheck**

```http
GET /health
```

**Réponse** :
```json
{
  "status": "ok",
  "timestamp": "2026-05-16T...",
  "service": "excalidraw-auth-service"
}
```

**3. Créer un utilisateur (admin)**

```http
POST /admin/create-user
Authorization: Bearer <ADMIN_TOKEN>
Content-Type: application/json

{
  "email": "collaborateur@exemple.fr",
  "password": "MotDePasse123",
  "nom": "Jean Dupont"
}
```

**Réponse** :
```json
{
  "success": true,
  "user": {
    "id": 2,
    "email": "collaborateur@exemple.fr",
    "nom": "Jean Dupont",
    "created_at": "2026-05-16T..."
  }
}
```

**Variables d'environnement** :
- `ADMIN_TOKEN=***VOIR_FICHIER_.ENV_DU_SERVICE***`

---

### 4.3. NocoDB API

**Base URL** : `https://nocodb.agnisolution.fr`

**Authentification** : Header `xc-token: <NOCODB_API_TOKEN>`

#### Endpoints principaux

**Documentation complète** : https://docs.nocodb.com/developer-resources/rest-apis

**1. Lister les enregistrements d'une table**

```http
GET /api/v2/tables/{tableId}/records
Headers:
  xc-token: <TOKEN>
```

**2. Créer un enregistrement**

```http
POST /api/v2/tables/{tableId}/records
Headers:
  xc-token: <TOKEN>
  Content-Type: application/json

Body:
{
  "field1": "value1",
  "field2": "value2"
}
```

**3. Chercher/filtrer**

```http
GET /api/v2/tables/{tableId}/records?where=(field,eq,value)
```

**Table IDs importants** (à récupérer via l'API NocoDB) :
- Table `Clients`
- Table `Missions`
- Table `Schemas_Excalidraw`

**Token API NocoDB** : À générer depuis l'UI NocoDB (Account Settings → API Tokens).

---

### 4.4. AFFiNE API (si disponible)

**Base URL** : `https://affine.agnisolution.fr`

**Note** : AFFiNE n'expose pas d'API REST publique standard pour la création de documents. Deux options :

**Option A - Via MCP AFFiNE existant** :
- Utiliser les MCP AFFiNE déjà configurés (`affine-opepartner`, `affine-agni`)
- Le MCP custom Excalidraw peut appeler ces MCP (via subprocess ou communication inter-MCP)

**Option B - Via API GraphQL interne** (si disponible) :
- À investiguer : AFFiNE a peut-être une API GraphQL pour manipuler les docs
- URL potentielle : `https://affine.agnisolution.fr/api/graphql`

**Workspace OPEPARTNER** :
- ID : `3869ae28-9638-4390-a28d-905ff5c563d6`
- Structure des dossiers :
  ```
  03 — Clients / Missions
    ├── [Nom Client]
    │   ├── [Nom Mission]
    │   │   ├── [BMC] Business Model Canvas
    │   │   ├── [PESTEL] Analyse environnement
    │   │   └── [SWOT] Analyse stratégique
  ```

---

## 5. Système de templates Excalidraw

### 5.1. Structure d'un template

Un template Excalidraw est un **JSON standard Excalidraw** avec des **placeholders** dans les éléments texte.

**Exemple simplifié de template BMC** :

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.agnisolution.fr",
  "elements": [
    {
      "id": "rect-partners",
      "type": "rectangle",
      "x": 100,
      "y": 100,
      "width": 300,
      "height": 400,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#ffffff",
      "fillStyle": "solid"
    },
    {
      "id": "title-partners",
      "type": "text",
      "x": 120,
      "y": 120,
      "text": "Partenaires clés",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "left"
    },
    {
      "id": "content-partners",
      "type": "text",
      "x": 120,
      "y": 160,
      "text": "{{PARTNERS}}",
      "fontSize": 16,
      "fontFamily": 1,
      "textAlign": "left"
    }
    // ... répéter pour les 9 cases du BMC
  ],
  "appState": {
    "viewBackgroundColor": "#ffffff"
  }
}
```

### 5.2. Placeholders standards

**Convention** : `{{VARIABLE_NAME}}` en UPPERCASE_SNAKE_CASE.

**Placeholders par type de template** :

#### BMC (Business Model Canvas)
- `{{CLIENT_NAME}}` : Nom du client
- `{{PARTNERS}}` : Liste des partenaires clés
- `{{KEY_ACTIVITIES}}` : Activités clés
- `{{KEY_RESOURCES}}` : Ressources clés
- `{{VALUE_PROPOSITION}}` : Propositions de valeur
- `{{CUSTOMER_RELATIONS}}` : Relations clients
- `{{CHANNELS}}` : Canaux de distribution
- `{{CUSTOMER_SEGMENTS}}` : Segments clients
- `{{COST_STRUCTURE}}` : Structure de coûts
- `{{REVENUE_STREAMS}}` : Flux de revenus

#### PESTEL
- `{{CLIENT_NAME}}` : Nom du client
- `{{POLITICAL}}` : Facteurs politiques
- `{{ECONOMIC}}` : Facteurs économiques
- `{{SOCIAL}}` : Facteurs sociaux
- `{{TECHNOLOGICAL}}` : Facteurs technologiques
- `{{ENVIRONMENTAL}}` : Facteurs environnementaux
- `{{LEGAL}}` : Facteurs légaux

#### SWOT
- `{{CLIENT_NAME}}` : Nom du client
- `{{STRENGTHS}}` : Forces (liste à puces)
- `{{WEAKNESSES}}` : Faiblesses (liste à puces)
- `{{OPPORTUNITIES}}` : Opportunités (liste à puces)
- `{{THREATS}}` : Menaces (liste à puces)

### 5.3. Algorithme de remplissage

```python
def fill_template(template_json, data):
    """
    Remplace les placeholders dans un template Excalidraw.
    
    Args:
        template_json: dict - JSON du template
        data: dict - Données à injecter {placeholder: value}
    
    Returns:
        dict - JSON Excalidraw avec placeholders remplacés
    """
    import copy
    
    # Clone profond pour ne pas modifier le template original
    scene = copy.deepcopy(template_json)
    
    # Parcourir tous les éléments
    for element in scene.get('elements', []):
        if element.get('type') == 'text':
            text = element.get('text', '')
            
            # Remplacer tous les placeholders
            for placeholder, value in data.items():
                # Convertir les listes en bullet points
                if isinstance(value, list):
                    value = '\n'.join([f'• {item}' for item in value])
                
                # Remplacer le placeholder
                text = text.replace(f'{{{{{placeholder}}}}}', str(value))
            
            element['text'] = text
    
    return scene
```

**Exemple d'utilisation** :

```python
# 1. Récupérer le template depuis Postgres
template = get_template('BMC')  # Retourne le JSONB de la colonne excalidraw_json

# 2. Préparer les données
data = {
    'CLIENT_NAME': 'Dupont SAS',
    'PARTNERS': ['Fournisseur A', 'Fournisseur B', 'Partenaire logistique C'],
    'KEY_ACTIVITIES': ['Production', 'Distribution', 'SAV'],
    'VALUE_PROPOSITION': 'Solutions sur mesure pour l\'industrie',
    # ... autres champs
}

# 3. Remplir le template
scene_filled = fill_template(template['excalidraw_json'], data)

# 4. Générer un ID unique
scene_id = generate_unique_id(length=12)  # Ex: 'a1b2c3d4e5f6'

# 5. Sauvegarder dans le backend Excalidraw
response = requests.post(
    'http://excalidraw-backend:8080/api/v2/scenes',
    json=scene_filled
)
# Le backend retourne: {"id": "a1b2c3d4e5f6"}

# 6. Mettre à jour la table keyv avec les métadonnées
db.execute("""
    UPDATE keyv 
    SET created_by = %s,
        template_id = %s,
        metadata = %s
    WHERE key = %s
""", [user_id, template['id'], json.dumps({'client_id': 42, ...}), scene_id])
```

---

## 6. MCP existants et configuration

### 6.1. Configuration Claude Desktop

**Fichier** : `~/Library/Application Support/Claude/claude_desktop_config.json`

**Contenu actuel** :

```json
{
  "mcpServers": {
    "affine-opepartner": {
      "command": "npx",
      "args": [
        "-y",
        "@dawncr0w/affine-mcp",
        "--workspace-id",
        "3869ae28-9638-4390-a28d-905ff5c563d6",
        "--api-url",
        "https://affine.agnisolution.fr"
      ]
    },
    "affine-agni": {
      "command": "npx",
      "args": [
        "-y",
        "@dawncr0w/affine-mcp",
        "--workspace-id",
        "85a5d444-80db-49e6-996d-f2ecda4d66ae",
        "--api-url",
        "https://affine.agnisolution.fr"
      ]
    },
    "nocodb": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-nocodb"
      ],
      "env": {
        "NOCODB_URL": "https://nocodb.agnisolution.fr",
        "NOCODB_TOKEN": "<TOKEN_A_GENERER>"
      }
    }
    // ... autres MCP (n8n, Stripe, Gmail, etc.)
  }
}
```

### 6.2. Ajout du MCP Excalidraw custom

**Ajout à faire** :

```json
{
  "mcpServers": {
    "excalidraw": {
      "command": "python",
      "args": [
        "/Volumes/ZIKE/codage/projet_excalidraw_opepartner/mcp-excalidraw/server.py"
      ],
      "env": {
        "DATABASE_URL": "postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@69.62.110.207:5432/excalidraw_storage",
        "EXCALIDRAW_BACKEND_URL": "https://exca-api.agnisolution.fr",
        "EXCALIDRAW_FRONTEND_URL": "https://excalidraw.agnisolution.fr",
        "NOCODB_URL": "https://nocodb.agnisolution.fr",
        "NOCODB_TOKEN": "<TOKEN>",
        "AFFINE_API_URL": "https://affine.agnisolution.fr",
        "AFFINE_WORKSPACE_OPEPARTNER": "3869ae28-9638-4390-a28d-905ff5c563d6",
        "DEFAULT_USER_ID": "1"
      }
    }
  }
}
```

---

## 7. Spécifications du MCP custom à développer

### 7.1. Stack technique recommandé

**Langage** : Python 3.10+

**Framework MCP** : [FastMCP](https://github.com/jlowin/fastmcp) (le plus simple et rapide)

**Dépendances** :
```
fastmcp>=0.1.0
psycopg2-binary>=2.9.9
requests>=2.31.0
python-dotenv>=1.0.0
```

### 7.2. Structure du projet

```
mcp-excalidraw/
├── server.py               # Point d'entrée MCP
├── requirements.txt        # Dépendances Python
├── .env.example           # Variables d'environnement template
├── README.md              # Documentation
├── lib/
│   ├── __init__.py
│   ├── database.py        # Connexion PostgreSQL
│   ├── excalidraw.py      # Client API Excalidraw backend
│   ├── nocodb.py          # Client API NocoDB
│   ├── affine.py          # Client API AFFiNE (si possible)
│   ├── templates.py       # Gestion des templates
│   └── utils.py           # Utilitaires (generate_id, etc.)
└── tests/
    └── test_*.py          # Tests unitaires
```

### 7.3. Outils MCP à implémenter

#### Catégorie 1 : Création depuis templates

**1. `create_bmc`**

```python
@mcp.tool()
def create_bmc(
    client_name: str,
    mission_name: str = None,
    partners: list[str] = [],
    key_activities: list[str] = [],
    key_resources: list[str] = [],
    value_proposition: str = "",
    customer_relations: str = "",
    channels: list[str] = [],
    customer_segments: list[str] = [],
    cost_structure: str = "",
    revenue_streams: str = "",
    user_id: int = 1
) -> dict:
    """
    Crée un Business Model Canvas depuis le template.
    
    Returns:
        {
            "success": true,
            "scene_id": "abc123def456",
            "excalidraw_url": "https://excalidraw.agnisolution.fr/#json=abc123def456",
            "nocodb_id": 42,
            "affine_doc_id": "xyz789"
        }
    """
    # 1. Récupérer le template BMC
    # 2. Remplir avec les données
    # 3. Sauvegarder dans Excalidraw backend
    # 4. Insert dans NocoDB
    # 5. Créer doc dans AFFiNE
    # 6. Retourner les URLs
```

**2. `create_pestel`**

```python
@mcp.tool()
def create_pestel(
    client_name: str,
    mission_name: str = None,
    political: str = "",
    economic: str = "",
    social: str = "",
    technological: str = "",
    environmental: str = "",
    legal: str = "",
    user_id: int = 1
) -> dict:
    """Crée une analyse PESTEL depuis le template."""
```

**3. `create_swot`**

```python
@mcp.tool()
def create_swot(
    client_name: str,
    mission_name: str = None,
    strengths: list[str] = [],
    weaknesses: list[str] = [],
    opportunities: list[str] = [],
    threats: list[str] = [],
    user_id: int = 1
) -> dict:
    """Crée une analyse SWOT depuis le template."""
```

**4. `create_from_template` (générique)**

```python
@mcp.tool()
def create_from_template(
    template_name: str,
    data: dict,
    user_id: int = 1,
    metadata: dict = {}
) -> dict:
    """
    Crée une scène depuis n'importe quel template.
    
    Args:
        template_name: 'BMC', 'PESTEL', 'SWOT', etc.
        data: Dictionnaire des placeholders à remplacer
        user_id: ID de l'utilisateur créateur
        metadata: Métadonnées additionnelles (client_id, mission_id, etc.)
    """
```

---

#### Catégorie 2 : Manipulation des scènes

**5. `get_scene`**

```python
@mcp.tool()
def get_scene(scene_id: str) -> dict:
    """
    Récupère le JSON complet d'une scène.
    
    Args:
        scene_id: ID de la scène (ex: 'abc123def456')
    
    Returns:
        {
            "scene_id": "abc123def456",
            "json": {...},  # JSON Excalidraw complet
            "metadata": {...},
            "created_by": {...},
            "template": {...}
        }
    """
```

**6. `update_scene`**

```python
@mcp.tool()
def update_scene(
    scene_id: str,
    data: dict,
    user_id: int = 1
) -> dict:
    """
    Met à jour une scène existante en remplaçant des placeholders.
    
    Note: Préserve les modifications manuelles de l'utilisateur.
    """
```

**7. `list_scenes`**

```python
@mcp.tool()
def list_scenes(
    client_id: int = None,
    mission_id: int = None,
    document_type: str = None,
    template_id: int = None,
    created_by: int = None,
    status: str = None,
    limit: int = 10,
    offset: int = 0
) -> list[dict]:
    """
    Liste les scènes avec filtres.
    
    Returns:
        [
            {
                "scene_id": "abc123",
                "url": "https://excalidraw.agnisolution.fr/#json=abc123",
                "document_type": "BMC",
                "client_name": "Dupont SAS",
                "created_at": "2026-05-16T...",
                "created_by": "Christophe Martin"
            },
            ...
        ]
    """
```

---

#### Catégorie 3 : Gestion des templates

**8. `list_templates`**

```python
@mcp.tool()
def list_templates(
    categorie: str = None,
    actif: bool = True
) -> list[dict]:
    """
    Liste les templates disponibles.
    
    Returns:
        [
            {
                "id": 1,
                "nom": "BMC",
                "description": "Business Model Canvas avec 9 cases",
                "categorie": "strategy",
                "tags": ["consulting", "strategy"]
            },
            ...
        ]
    """
```

**9. `get_template_placeholders`**

```python
@mcp.tool()
def get_template_placeholders(template_name: str) -> list[str]:
    """
    Retourne la liste des placeholders d'un template.
    
    Utile pour Claude pour savoir quelles données demander à l'utilisateur.
    
    Returns:
        ["CLIENT_NAME", "PARTNERS", "KEY_ACTIVITIES", ...]
    """
```

---

#### Catégorie 4 : Intégration NocoDB

**10. `create_client`**

```python
@mcp.tool()
def create_client(
    nom: str,
    secteur: str = "",
    contact_principal: str = ""
) -> dict:
    """
    Crée un client dans NocoDB.
    
    Returns:
        {"id": 42, "nom": "Dupont SAS"}
    """
```

**11. `find_or_create_client`**

```python
@mcp.tool()
def find_or_create_client(nom: str) -> dict:
    """
    Cherche un client par nom, le crée s'il n'existe pas.
    """
```

**12. `create_mission`**

```python
@mcp.tool()
def create_mission(
    client_id: int,
    nom: str,
    date_debut: str = None,
    date_fin: str = None
) -> dict:
    """Crée une mission dans NocoDB."""
```

---

#### Catégorie 5 : Export et partage

**13. `export_scene_png`**

```python
@mcp.tool()
def export_scene_png(
    scene_id: str,
    width: int = 1920,
    height: int = 1080
) -> dict:
    """
    Exporte une scène en PNG.
    
    Note: Nécessite un outil de rendering (Playwright, Puppeteer, etc.)
    ou utilisation de l'API Excalidraw si disponible.
    
    Returns:
        {"url": "https://...", "path": "/tmp/scene.png"}
    """
```

**14. `export_scene_svg`**

```python
@mcp.tool()
def export_scene_svg(scene_id: str) -> dict:
    """Exporte une scène en SVG."""
```

---

### 7.4. Architecture du code

**Exemple de structure `server.py`** :

```python
#!/usr/bin/env python3
"""
MCP Custom Excalidraw
Génération de schémas stratégiques depuis des templates.
"""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP

# Charger les variables d'environnement
load_dotenv()

# Importer les modules
from lib.database import Database
from lib.excalidraw import ExcalidrawClient
from lib.nocodb import NocoDBClient
from lib.templates import TemplateManager

# Initialiser le MCP
mcp = FastMCP("excalidraw-opepartner")

# Initialiser les clients
db = Database(os.getenv('DATABASE_URL'))
excalidraw = ExcalidrawClient(os.getenv('EXCALIDRAW_BACKEND_URL'))
nocodb = NocoDBClient(
    url=os.getenv('NOCODB_URL'),
    token=os.getenv('NOCODB_TOKEN')
)
template_mgr = TemplateManager(db)

# ============================================
# OUTILS MCP
# ============================================

@mcp.tool()
def create_bmc(
    client_name: str,
    mission_name: str = None,
    partners: list[str] = [],
    key_activities: list[str] = [],
    # ... autres paramètres
    user_id: int = 1
) -> dict:
    """Crée un Business Model Canvas depuis le template."""
    
    # 1. Récupérer le template
    template = template_mgr.get_template('BMC')
    
    # 2. Préparer les données
    data = {
        'CLIENT_NAME': client_name,
        'PARTNERS': partners,
        'KEY_ACTIVITIES': key_activities,
        # ...
    }
    
    # 3. Remplir le template
    scene_json = template_mgr.fill_template(template, data)
    
    # 4. Générer un ID unique
    scene_id = excalidraw.generate_id()
    
    # 5. Sauvegarder dans Excalidraw
    excalidraw.create_scene(scene_id, scene_json)
    
    # 6. Mettre à jour les métadonnées dans Postgres
    db.update_scene_metadata(
        scene_id=scene_id,
        created_by=user_id,
        template_id=template['id'],
        metadata={
            'document_type': 'BMC',
            'client_name': client_name,
            'mission_name': mission_name
        }
    )
    
    # 7. Créer/récupérer le client dans NocoDB
    client = nocodb.find_or_create('Clients', {'nom': client_name})
    
    # 8. Créer la mission si spécifiée
    mission = None
    if mission_name:
        mission = nocodb.find_or_create('Missions', {
            'client_id': client['id'],
            'nom': mission_name
        })
    
    # 9. Insert dans la table Schemas_Excalidraw
    schema_record = nocodb.insert('Schemas_Excalidraw', {
        'excalidraw_id': scene_id,
        'edit_url': f'{os.getenv("EXCALIDRAW_FRONTEND_URL")}/#json={scene_id}',
        'client_id': client['id'],
        'mission_id': mission['id'] if mission else None,
        'document_type': 'BMC',
        'document_title': f'Business Model Canvas - {client_name}',
        'template_id': template['id'],
        'created_by': user_id,
        'status': 'draft'
    })
    
    # 10. Créer un doc dans AFFiNE (optionnel, si API disponible)
    # affine_doc = affine.create_doc(...)
    
    # 11. Retourner le résultat
    return {
        'success': True,
        'scene_id': scene_id,
        'excalidraw_url': f'{os.getenv("EXCALIDRAW_FRONTEND_URL")}/#json={scene_id}',
        'nocodb_id': schema_record['id'],
        'client': client,
        'mission': mission
    }


@mcp.tool()
def list_scenes(
    client_id: int = None,
    document_type: str = None,
    limit: int = 10
) -> list[dict]:
    """Liste les scènes avec filtres."""
    
    # Requête SQL avec jointures
    query = """
        SELECT 
            k.key AS scene_id,
            k.metadata->>'document_type' AS document_type,
            k.metadata->>'client_name' AS client_name,
            u.nom AS created_by_name,
            t.nom AS template_name,
            k.created_at_tracked
        FROM keyv k
        LEFT JOIN utilisateurs u ON k.created_by = u.id
        LEFT JOIN templates t ON k.template_id = t.id
        WHERE 1=1
    """
    
    params = []
    
    if client_id:
        query += " AND k.metadata->>'client_id' = %s"
        params.append(str(client_id))
    
    if document_type:
        query += " AND k.metadata->>'document_type' = %s"
        params.append(document_type)
    
    query += " ORDER BY k.created_at_tracked DESC LIMIT %s"
    params.append(limit)
    
    results = db.query(query, params)
    
    return [
        {
            'scene_id': r['scene_id'],
            'url': f'{os.getenv("EXCALIDRAW_FRONTEND_URL")}/#json={r["scene_id"]}',
            'document_type': r['document_type'],
            'client_name': r['client_name'],
            'created_by': r['created_by_name'],
            'template': r['template_name'],
            'created_at': r['created_at_tracked'].isoformat()
        }
        for r in results
    ]


# ============================================
# LANCEMENT DU MCP
# ============================================

if __name__ == "__main__":
    mcp.run()
```

---

## 8. Workflow cible et cas d'usage

### 8.1. Cas d'usage 1 : Création d'un BMC pour un nouveau client

**Prompt utilisateur dans Claude Desktop** :

> "Crée un Business Model Canvas pour le client Dupont SAS dans le cadre de la mission Transformation Digitale. Partenaires clés : Fournisseur A, Fournisseur B, Intégrateur Cloud. Activités clés : Production, Distribution, SAV. Proposition de valeur : Solutions industrielles sur mesure avec accompagnement 24/7."

**Actions du MCP** :

1. Appel de `create_bmc()` avec les paramètres extraits
2. Récupération du template BMC depuis Postgres
3. Remplissage des placeholders
4. Sauvegarde dans Excalidraw backend
5. Création du client "Dupont SAS" dans NocoDB (si n'existe pas)
6. Création de la mission "Transformation Digitale"
7. Insert dans `Schemas_Excalidraw`
8. Création d'un doc AFFiNE dans `03 — Clients / Missions / Dupont SAS / [BMC] Business Model Canvas`
9. Retour à Claude avec les URLs

**Réponse de Claude à l'utilisateur** :

> "✅ Business Model Canvas créé avec succès !
>
> 🔗 **Lien Excalidraw** : https://excalidraw.agnisolution.fr/#json=abc123def456
>
> 📊 **Document AFFiNE** : [Ouvrir dans AFFiNE](https://affine.agnisolution.fr/workspace/.../doc/xyz789)
>
> 📋 **Enregistré dans NocoDB** : Schemas_Excalidraw #42
>
> Le BMC a été créé avec les 9 cases pré-remplies selon vos indications. Vous pouvez l'éditer directement dans Excalidraw."

---

### 8.2. Cas d'usage 2 : Lister tous les BMC d'un client

**Prompt utilisateur** :

> "Liste tous les Business Model Canvas créés pour le client Dupont SAS."

**Actions du MCP** :

1. Appel de `list_scenes(document_type='BMC', client_name='Dupont SAS')`
2. Requête SQL avec filtres
3. Retour de la liste des scènes

**Réponse de Claude** :

> "Voici les 3 Business Model Canvas créés pour Dupont SAS :
>
> 1. **Business Model Canvas - Transformation Digitale**
>    - Créé le : 16 mai 2026
>    - Par : Christophe Martin
>    - Statut : Brouillon
>    - [Ouvrir dans Excalidraw](https://excalidraw.agnisolution.fr/#json=abc123)
>
> 2. **Business Model Canvas - Diversification produits**
>    - Créé le : 10 mai 2026
>    - Par : Christophe Martin
>    - Statut : Validé
>    - [Ouvrir dans Excalidraw](https://excalidraw.agnisolution.fr/#json=def456)
>
> ..."

---

### 8.3. Cas d'usage 3 : Créer plusieurs schémas d'un coup

**Prompt utilisateur** :

> "Pour le client Dupont SAS, crée un Business Model Canvas, une analyse PESTEL et un SWOT. Utilise les données suivantes : [...]"

**Actions du MCP** :

1. Appel de `create_bmc(...)` → Retourne URL 1
2. Appel de `create_pestel(...)` → Retourne URL 2
3. Appel de `create_swot(...)` → Retourne URL 3
4. Claude agrège les résultats

**Réponse de Claude** :

> "✅ 3 documents créés pour Dupont SAS :
>
> 1. **Business Model Canvas** : [Ouvrir](https://excalidraw.agnisolution.fr/#json=abc123)
> 2. **Analyse PESTEL** : [Ouvrir](https://excalidraw.agnisolution.fr/#json=def456)
> 3. **Analyse SWOT** : [Ouvrir](https://excalidraw.agnisolution.fr/#json=ghi789)
>
> Tous les documents ont été enregistrés dans NocoDB et AFFiNE."

---

## 9. Contraintes et bonnes pratiques

### 9.1. Sécurité

**Authentification** :
- Le MCP s'exécute en local (Claude Desktop) ou sur le VPS (remote MCP)
- Pas besoin d'authentifier les requêtes vers le backend Excalidraw (réseau interne Docker)
- **IMPORTANT** : Ne jamais exposer les credentials dans les logs ou les retours d'erreur

**Validation des inputs** :
- Valider tous les paramètres avant de les utiliser
- Échapper les caractères spéciaux dans les requêtes SQL (utiliser des paramètres bindés)
- Limiter la taille des données (max 10 MB pour un JSON Excalidraw)

**Permissions** :
- Vérifier que `user_id` existe dans la table `utilisateurs`
- Vérifier que l'utilisateur a le droit de modifier une scène (si update)

---

### 9.2. Performance

**Cache** :
- Mettre en cache les templates (ils changent rarement)
- Réutiliser les connexions PostgreSQL (pool de connexions)

**Pagination** :
- Limiter les résultats de `list_scenes()` (default: 10, max: 100)

**Timeout** :
- Définir des timeouts sur les requêtes HTTP (5 secondes)

---

### 9.3. Résilience

**Gestion des erreurs** :
- Catch toutes les exceptions et retourner des messages clairs
- Logger les erreurs dans un fichier (pas dans stdout pour ne pas polluer Claude)

**Retry** :
- Retry automatique sur les erreurs réseau (max 3 tentatives)
- Exponential backoff entre les tentatives

**Transactions** :
- Utiliser des transactions SQL quand on fait plusieurs opérations (insert client + mission + schema)

---

### 9.4. Migrabilité

**Variables d'environnement** :
- Tout ce qui est URL/credential/config passe par des variables d'env
- Pas de hardcoding

**Logging** :
- Logger les opérations importantes (création de scène, erreurs)
- Format : `[TIMESTAMP] [LEVEL] [MODULE] Message`

**Documentation** :
- Documenter chaque outil MCP (docstring complète)
- Exemples d'utilisation dans le README

---

### 9.5. RGPD

**Données personnelles** :
- Les noms de clients sont considérés comme des données personnelles
- Ne pas logger les noms de clients (ou anonymiser les logs)
- Prévoir un mécanisme de suppression (GDPR Right to be Forgotten)

**Consentement** :
- Les clients OPEPARTNER acceptent implicitement le traitement de leurs données dans le cadre de la prestation de conseil
- Documenter dans les CGV/CGUS d'OPEPARTNER

---

## 10. Variables d'environnement et credentials

### 10.1. Fichier `.env` du MCP

```bash
# PostgreSQL (base excalidraw_storage)
DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@69.62.110.207:5432/excalidraw_storage

# Excalidraw
EXCALIDRAW_BACKEND_URL=https://exca-api.agnisolution.fr
EXCALIDRAW_FRONTEND_URL=https://excalidraw.agnisolution.fr

# NocoDB
NOCODB_URL=https://nocodb.agnisolution.fr
NOCODB_TOKEN=<TOKEN_A_GENERER_DANS_NOCODB>

# AFFiNE
AFFINE_API_URL=https://affine.agnisolution.fr
AFFINE_WORKSPACE_OPEPARTNER=3869ae28-9638-4390-a28d-905ff5c563d6
AFFINE_WORKSPACE_AGNI=85a5d444-80db-49e6-996d-f2ecda4d66ae

# Service Auth (si besoin de créer des users)
AUTH_SERVICE_URL=https://exca-auth.agnisolution.fr
ADMIN_TOKEN=CoIT9+wh1DrhuVPFjzwHtNxBMSVq0afla9Jd95de1dc=

# Configuration
DEFAULT_USER_ID=1
LOG_LEVEL=INFO
LOG_FILE=/tmp/mcp-excalidraw.log
```

### 10.2. Comment générer le token NocoDB

1. Ouvrir NocoDB : https://nocodb.agnisolution.fr
2. Cliquer sur l'avatar en haut à droite → **Account Settings**
3. Onglet **API Tokens**
4. Cliquer sur **Create New Token**
5. Nom : `MCP Excalidraw Custom`
6. Copier le token généré
7. L'ajouter dans `.env` : `NOCODB_TOKEN=nc_xxx...`

---

## 11. Plan de développement recommandé

### Phase 1 : Setup et infrastructure (1-2h)

1. Créer le dossier `mcp-excalidraw/`
2. Initialiser Python :
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install fastmcp psycopg2-binary requests python-dotenv
   ```
3. Créer la structure de fichiers (server.py, lib/, etc.)
4. Créer le fichier `.env`
5. Tester la connexion Postgres

### Phase 2 : Modules de base (2-3h)

1. `lib/database.py` : Classe Database avec méthodes query, execute, etc.
2. `lib/excalidraw.py` : Client API Excalidraw (create_scene, get_scene)
3. `lib/nocodb.py` : Client API NocoDB (find, create, insert)
4. `lib/templates.py` : TemplateManager (get_template, fill_template)
5. `lib/utils.py` : generate_unique_id, format_list, etc.

### Phase 3 : Premiers outils MCP (2-3h)

1. `list_templates()` : Liste les templates disponibles
2. `get_scene()` : Récupère une scène
3. `create_from_template()` : Outil générique de création
4. Tester avec Claude Desktop

### Phase 4 : Outils métier (3-4h)

1. `create_bmc()` : Business Model Canvas
2. `create_pestel()` : Analyse PESTEL
3. `create_swot()` : Analyse SWOT
4. `list_scenes()` : Liste avec filtres
5. Intégration NocoDB (find_or_create_client, create_mission)

### Phase 5 : Intégration AFFiNE (2-3h)

1. Investiguer l'API AFFiNE (GraphQL ? REST ?)
2. Créer `lib/affine.py` si API disponible
3. Sinon, utiliser le MCP AFFiNE existant via subprocess

### Phase 6 : Tests et debugging (2-3h)

1. Tests unitaires pour chaque module
2. Tests d'intégration bout-en-bout
3. Gestion des erreurs
4. Logging

### Phase 7 : Documentation et déploiement (1-2h)

1. README complet avec exemples
2. Dockerfile pour déploiement cloud
3. Guide de configuration Claude Desktop
4. Guide de déploiement Coolify (MCP remote HTTPS)

**Temps total estimé** : 13-20 heures de développement

---

## 12. Ressources et références

### Documentation officielle

- **FastMCP** : https://github.com/jlowin/fastmcp
- **Model Context Protocol** : https://modelcontextprotocol.io/
- **Excalidraw** : https://docs.excalidraw.com/
- **NocoDB API** : https://docs.nocodb.com/developer-resources/rest-apis
- **AFFiNE** : https://docs.affine.pro/

### Exemples de MCP existants

- **NocoDB MCP** : https://github.com/modelcontextprotocol/servers/tree/main/src/nocodb
- **Postgres MCP** : https://github.com/modelcontextprotocol/servers/tree/main/src/postgres
- **AFFiNE MCP** : https://github.com/dawncr0w/affine-mcp

### Outils utiles

- **Psycopg2** (PostgreSQL client) : https://www.psycopg.org/docs/
- **Requests** (HTTP client) : https://requests.readthedocs.io/
- **Python dotenv** : https://github.com/theskumar/python-dotenv

---

## 13. Contact et support

**Développeur principal** : Christophe Martin (cmartin@agniconsult.fr)

**Repo GitHub** : https://github.com/christophe39/excalidraw (privé)

**Documentation projet** :
- `/Volumes/ZIKE/codage/projet_excalidraw_opepartner/CLAUDE.md`
- `/Volumes/ZIKE/codage/projet_excalidraw_opepartner/SESSION-15-MAI-2026.md`
- `/Volumes/ZIKE/codage/projet_excalidraw_opepartner/PHASE-G-FINAL-DEPLOYMENT.md`

---

**Document créé le 16 mai 2026**  
**Version : 1.0**  
**Statut : Prêt pour développement**

---

## Annexe A : Format JSON Excalidraw (exemple complet)

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.agnisolution.fr",
  "elements": [
    {
      "type": "rectangle",
      "version": 1,
      "versionNonce": 123456789,
      "isDeleted": false,
      "id": "rect-1",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "angle": 0,
      "x": 100,
      "y": 100,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "#ffffff",
      "width": 300,
      "height": 200,
      "seed": 123456789,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "boundElements": [],
      "updated": 1715864400000,
      "link": null,
      "locked": false
    },
    {
      "type": "text",
      "version": 1,
      "versionNonce": 987654321,
      "isDeleted": false,
      "id": "text-1",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "angle": 0,
      "x": 120,
      "y": 120,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "width": 260,
      "height": 25,
      "seed": 987654321,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "boundElements": [],
      "updated": 1715864400000,
      "link": null,
      "locked": false,
      "fontSize": 20,
      "fontFamily": 1,
      "text": "{{CLIENT_NAME}}",
      "textAlign": "left",
      "verticalAlign": "top",
      "containerId": null,
      "originalText": "{{CLIENT_NAME}}",
      "lineHeight": 1.25,
      "baseline": 18
    }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

---

## Annexe B : Exemple de requête SQL complexe

```sql
-- Récupérer toutes les scènes d'un client avec leurs informations complètes
SELECT 
  k.key AS scene_id,
  k.metadata->>'document_type' AS document_type,
  k.metadata->>'document_title' AS document_title,
  k.metadata->>'client_id' AS client_id,
  k.metadata->>'mission_id' AS mission_id,
  k.metadata->>'status' AS status,
  u.email AS created_by_email,
  u.nom AS created_by_name,
  t.nom AS template_name,
  t.description AS template_description,
  k.created_at_tracked AS created_at,
  jsonb_array_length(k.value->'elements') AS elements_count
FROM keyv k
LEFT JOIN utilisateurs u ON k.created_by = u.id
LEFT JOIN templates t ON k.template_id = t.id
WHERE k.metadata->>'client_id' = '42'
ORDER BY k.created_at_tracked DESC;
```

---

**FIN DU DOCUMENT**
