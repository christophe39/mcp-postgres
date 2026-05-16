# Architecture Excalidraw OPEPARTNER

> Documentation complète de l'architecture, du fonctionnement et des capacités du système

**Dernière mise à jour :** 16 mai 2026  
**Version :** 1.0.0  
**Auteur :** Christophe Martin + Claude Sonnet 4.5

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture technique](#architecture-technique)
3. [Composants du système](#composants-du-système)
4. [Flux de données](#flux-de-données)
5. [Base de données PostgreSQL](#base-de-données-postgresql)
6. [Intégration NocoDB](#intégration-nocodb)
7. [Structure du projet](#structure-du-projet)
8. [Fonctionnalités](#fonctionnalités)
9. [Déploiement](#déploiement)
10. [Cas d'usage](#cas-dusage)

---

## 🎯 Vue d'ensemble

### Objectif du projet

**OPEPARTNER Stack** est un système self-hosted permettant de :
- Créer et éditer des schémas visuels (diagrammes, organigrammes, Business Model Canvas, etc.)
- Sauvegarder de manière pérenne les schémas dans une base PostgreSQL
- Partager les schémas via des liens persistants
- Intégrer les données avec NocoDB pour analyse et gestion
- Préparer l'intégration future avec AFFiNE et un MCP custom

### Contexte métier

**Public cible :** OPEPARTNER (cabinet de conseil stratégique)

**Cas d'usage principaux :**
1. **Ateliers clients :** Création de Business Model Canvas, SWOT, PESTEL en temps réel
2. **Documentation :** Schémas d'organisation, organigrammes, chaînes de valeur
3. **Livrables :** Plans 90 jours, feuilles de route, schémas stratégiques
4. **Collaboration :** Partage de schémas avec les clients via liens sécurisés

**Contraintes :**
- ✅ Self-hosted (souveraineté des données)
- ✅ Confidentialité RGPD
- ✅ Pas de dépendance cloud public
- ✅ Intégration avec l'écosystème AGNI (NocoDB, AFFiNE, n8n)

---

## 🏗️ Architecture technique

### Vue globale du système

```
┌────────────────────────────────────────────────────────────────┐
│                         INTERNET                                │
│                    (HTTPS / Cloudflare)                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    VPS Hostinger (69.62.110.207)               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Traefik (Reverse Proxy)                      │ │
│  │  - Routing HTTPS                                          │ │
│  │  - Certificats Let's Encrypt                              │ │
│  │  - Labels Docker discovery                                │ │
│  │  Container: coolify-proxy                                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                  │
│           ┌──────────────────┴──────────────────┐              │
│           │                                      │              │
│           ▼                                      ▼              │
│  ┌─────────────────────┐           ┌─────────────────────────┐│
│  │   FRONTEND          │           │   API (via Proxy)       ││
│  │   React/Excalidraw  │           │                         ││
│  │   Port: 80          │───────────▶   excalidraw-proxy      ││
│  │   excalidraw.agni...│           │   Nginx adaptateur      ││
│  │                     │           │   Port: 80              ││
│  │   Container:        │           │   exca-api.agni...      ││
│  │   frontend-*        │           │                         ││
│  └─────────────────────┘           │   Container: proxy-*    ││
│                                     └─────────────────────────┘│
│                                                 │               │
│                                                 ▼               │
│                                     ┌─────────────────────────┐│
│                                     │   BACKEND               ││
│                                     │   Node.js / NestJS      ││
│                                     │   Port: 8080            ││
│                                     │   (interne uniquement)  ││
│                                     │                         ││
│                                     │   Container: backend-*  ││
│                                     └─────────────────────────┘│
│                                                 │               │
│                                                 ▼               │
│                              ┌─────────────────────────────────┐
│                              │   PostgreSQL 17                 │
│                              │   IP: 10.0.1.23:5432           │
│                              │   Base: excalidraw_storage     │
│                              │   User: excalidraw_backend     │
│                              │                                │
│                              │   Container: pk4s888o4...      │
│                              └─────────────────────────────────┘
│                                                 │               │
└─────────────────────────────────────────────────│───────────────┘
                                                  │
                                                  ▼
                              ┌─────────────────────────────────┐
                              │   NocoDB (Externe)              │
                              │   Interface base de données     │
                              │   https://nocodb.agnisolution.fr│
                              └─────────────────────────────────┘
```

### Pile technologique

| Couche | Technologie | Version | Rôle |
|--------|-------------|---------|------|
| **Frontend** | React + Excalidraw | Latest | Interface utilisateur de dessin |
| **Reverse Proxy** | Traefik | 2.x | Routing HTTPS + SSL |
| **Proxy Adaptateur** | Nginx Alpine | Latest | Traduction URLs API |
| **Backend** | Node.js + NestJS | Latest | API REST + Logique métier |
| **Base de données** | PostgreSQL | 17 | Stockage pérenne des schémas |
| **Orchestration** | Docker + Coolify | 4.0.0-beta | Gestion containers |
| **Interface DB** | NocoDB | Latest | Vue métier sur PostgreSQL |

### Réseau Docker

**Réseau principal :** `o8wsgoowkcogkgk0g8o4g8s0` (créé par Coolify)

**Containers et IPs :**

| Container | Nom | IP interne | Ports |
|-----------|-----|------------|-------|
| Frontend | `frontend-o8wsgoowkcogkgk0g8o4g8s0` | Variable | 80 |
| Proxy | `proxy-o8wsgoowkcogkgk0g8o4g8s0` | Variable | 80 |
| Backend | `backend-o8wsgoowkcogkgk0g8o4g8s0` | Variable | 8080 |
| PostgreSQL | `pk4s888o4wkc8ogokg0sg840` | 10.0.1.23 | 5432 |

**DNS interne :** Les containers se résolvent par leur nom de service (`backend`, `frontend`, `proxy`).

---

## 🧩 Composants du système

### 1. Frontend (Excalidraw)

**Rôle :** Interface utilisateur pour créer et éditer des schémas.

**Technologie :** React + Excalidraw (bibliothèque open-source de whiteboard)

**Image Docker :** `excalidraw-opepartner:latest` (buildée localement)

**Variables d'environnement :**
```bash
VITE_APP_BACKEND_V2_GET_URL=https://exca-api.agnisolution.fr/api/v2/
VITE_APP_BACKEND_V2_POST_URL=https://exca-api.agnisolution.fr/api/v2/post/
VITE_APP_DISABLE_TRACKING=true
```

⚠️ **Important :** Ces variables sont compilées au **build-time**, pas au runtime. Si tu changes les URLs, il faut rebuilder l'image.

**Fonctionnalités :**
- Dessin libre (formes, textes, flèches)
- Bibliothèque de formes
- Collaboration temps réel (désactivée actuellement)
- Export PNG, SVG, JSON
- **Sauvegarde serveur** → génère un lien partageable

**URL publique :** https://excalidraw.agnisolution.fr

---

### 2. Proxy Nginx (Adaptateur)

**Rôle :** Traduire les URLs entre le format Excalidraw et le format backend.

**Pourquoi nécessaire ?**

Excalidraw envoie :
- `POST /api/v2/post/` → Sauvegarder un schéma
- `GET /api/v2/{id}` → Récupérer un schéma

Le backend attend :
- `POST /api/v2/scenes` → Créer une scène
- `GET /api/v2/scenes/{id}` → Lire une scène

Le proxy **traduit** automatiquement :
```
POST /api/v2/post/     →  POST /api/v2/scenes
GET  /api/v2/{id}      →  GET  /api/v2/scenes/{id}
```

**Image Docker :** `excalidraw-proxy:latest` (buildée localement pour AMD64)

**Configuration Nginx :** [`infra/docker-compose/excalidraw-proxy/nginx.conf`](../infra/docker-compose/excalidraw-proxy/nginx.conf)

**Fichier clé :**
```nginx
# Traduction POST
location = /api/v2/post/ {
    proxy_pass http://backend:8080/api/v2/scenes;
    # Headers proxy...
}

# Traduction GET avec regex
location ~ ^/api/v2/([^/]+)$ {
    proxy_pass http://backend:8080/api/v2/scenes/$1;
    # Headers proxy...
}
```

**URL publique :** https://exca-api.agnisolution.fr

⚠️ **Point critique :** Le proxy met en cache la résolution DNS de "backend". Si le backend redémarre et change d'IP, il faut redémarrer le proxy.

---

### 3. Backend (Storage API)

**Rôle :** API REST pour stocker et récupérer les schémas dans PostgreSQL.

**Technologie :** Node.js + NestJS + TypeORM

**Image Docker :** `kiliandeca/excalidraw-storage-backend:latest` (Docker Hub)

**Endpoints principaux :**

| Méthode | Endpoint | Description | Réponse |
|---------|----------|-------------|---------|
| POST | `/api/v2/scenes` | Créer un schéma | `{"id": "1234567890"}` |
| GET | `/api/v2/scenes/:id` | Récupérer un schéma | Données binaires compressées |
| GET | `/api/v2/rooms/:id` | Récupérer une room collaborative | JSON |
| PUT | `/api/v2/rooms/:id` | Mettre à jour une room | JSON |

**Variables d'environnement :**
```bash
STORAGE_URI=postgresql://excalidraw_backend:PASSWORD@10.0.1.23:5432/excalidraw_storage
PORT=8080
NODE_ENV=production
CORS_ALLOWED_ORIGINS=https://excalidraw.agnisolution.fr,https://mcp-excalidraw.agnisolution.fr
ID_LENGTH=12
```

**Accès :** Interne uniquement (pas de domaine public configuré)

**Stockage :** Utilise la bibliothèque `keyv` pour stocker les schémas dans PostgreSQL de manière key-value.

---

### 4. PostgreSQL

**Rôle :** Base de données pérenne pour stocker les schémas Excalidraw.

**Version :** PostgreSQL 17 Alpine

**Container :** `pk4s888o4wkc8ogokg0sg840`

**Connexion :**
```
Host: 10.0.1.23
Port: 5432
User: excalidraw_backend
Password: ***VOIR_FICHIER_.ENV_DU_SERVICE***
Database: excalidraw_storage
```

**Tables :** Voir section [Base de données PostgreSQL](#base-de-données-postgresql)

---

### 5. Traefik

**Rôle :** Reverse proxy gérant le routing HTTPS et les certificats SSL.

**Container :** `coolify-proxy`

**Dashboard :** http://localhost:8080 (accessible uniquement sur le VPS)

**Configuration :** Labels Docker sur les containers (discovery automatique)

**Certificats :** Let's Encrypt (renouvellement automatique)

**Routes configurées :**

| Domaine | Service cible | Protocole |
|---------|---------------|-----------|
| `excalidraw.agnisolution.fr` | frontend-* | HTTPS |
| `exca-api.agnisolution.fr` | proxy-* | HTTPS |

⚠️ **Point critique :** Si le backend a un domaine configuré dans Coolify, Traefik créera automatiquement des routes qui court-circuitent le proxy. **Le backend ne doit JAMAIS avoir de domaine public.**

---

### 6. Coolify

**Rôle :** Plateforme d'orchestration Docker (self-hosted Heroku-like).

**Version :** 4.0.0-beta.462

**URL :** https://coolify.agnisolution.fr

**Fonctionnalités utilisées :**
- Gestion des services Docker Compose
- Configuration des domaines et certificats SSL
- Logs et monitoring des containers
- Déploiement via UI

**Configuration du service Excalidraw :**
- **Type :** Service Stack (Docker Compose)
- **3 services :** Frontend, Proxy, Backend
- **Réseau :** o8wsgoowkcogkgk0g8o4g8s0 (externe)

---

### 7. NocoDB

**Rôle :** Interface métier pour visualiser et gérer les données PostgreSQL.

**URL :** https://nocodb.agnisolution.fr

**Connexion à la base :** Via connexion externe PostgreSQL (voir section [Intégration NocoDB](#intégration-nocodb))

---

## 🔄 Flux de données

### Scénario 1 : Création d'un schéma

```
1. Utilisateur dessine dans Excalidraw
   │
   ▼
2. Utilisateur clique sur "Share"
   │
   ▼
3. Frontend Excalidraw
   POST https://exca-api.agnisolution.fr/api/v2/post/
   Body: { "elements": [...], "appState": {...} }
   │
   ▼
4. Traefik
   Route vers proxy-o8wsgoowkcogkgk0g8o4g8s0
   │
   ▼
5. Proxy Nginx
   Traduit l'URL : /api/v2/post/ → /api/v2/scenes
   Proxy vers http://backend:8080/api/v2/scenes
   │
   ▼
6. Backend NestJS
   - Génère un ID unique (12 chiffres)
   - Compresse les données (pako)
   - Chiffre les données (AES-GCM)
   - Stocke dans PostgreSQL via keyv
   │
   ▼
7. PostgreSQL
   INSERT INTO keyv (key, value)
   VALUES ('SCENES:1234567890', '<données compressées>')
   │
   ▼
8. Réponse au Frontend
   HTTP 201 Created
   Body: { "id": "1234567890" }
   │
   ▼
9. Frontend affiche le lien
   https://excalidraw.agnisolution.fr/#json=1234567890,<clé-chiffrement>
```

### Scénario 2 : Ouverture d'un lien partagé

```
1. Utilisateur ouvre le lien
   https://excalidraw.agnisolution.fr/#json=1234567890,abc123
   │
   ▼
2. Frontend Excalidraw (JavaScript)
   Parse l'URL : ID = 1234567890, clé = abc123
   │
   ▼
3. Frontend fait une requête
   GET https://exca-api.agnisolution.fr/api/v2/1234567890
   │
   ▼
4. Traefik → Proxy Nginx
   Traduit l'URL : /api/v2/1234567890 → /api/v2/scenes/1234567890
   │
   ▼
5. Backend NestJS
   SELECT value FROM keyv WHERE key = 'SCENES:1234567890'
   │
   ▼
6. PostgreSQL
   Retourne les données compressées et chiffrées
   │
   ▼
7. Backend renvoie les données
   HTTP 200 OK
   Body: <données binaires compressées>
   │
   ▼
8. Frontend Excalidraw
   - Décompresse (pako)
   - Déchiffre (AES-GCM avec la clé de l'URL)
   - Affiche le schéma
```

### Scénario 3 : Analyse dans NocoDB

```
1. Admin ouvre NocoDB
   https://nocodb.agnisolution.fr
   │
   ▼
2. Connexion à PostgreSQL
   Base "excalidraw_storage" via connexion externe
   │
   ▼
3. NocoDB affiche les tables
   - keyv (schémas stockés)
   - templates
   - utilisateurs
   - excalidraw_scenes
   │
   ▼
4. Requêtes SQL via NocoDB UI
   SELECT key, LENGTH(value), created_at
   FROM keyv
   WHERE key LIKE 'SCENES:%'
   ORDER BY created_at DESC
   │
   ▼
5. Visualisation des données
   - Nombre total de schémas
   - Date de création
   - Taille des schémas
   - (optionnel) Analyse des métadonnées
```

---

## 🗄️ Base de données PostgreSQL

### Vue d'ensemble

**Base :** `excalidraw_storage`  
**User :** `excalidraw_backend`  
**Accès :** 10.0.1.23:5432

### Structure des tables

```sql
-- Table principale de stockage (key-value)
CREATE TABLE keyv (
    key TEXT PRIMARY KEY,              -- Format: "SCENES:1234567890"
    value TEXT NOT NULL,               -- Données JSON compressées
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour recherche rapide
CREATE INDEX idx_keyv_key_prefix ON keyv(key) WHERE key LIKE 'SCENES:%';

-- Table des scènes (peu utilisée actuellement)
CREATE TABLE excalidraw_scenes (
    id VARCHAR(50) PRIMARY KEY,        -- ID unique du schéma
    json_data JSONB NOT NULL,          -- Données du schéma
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour tri par date
CREATE INDEX idx_excalidraw_scenes_created_at 
    ON excalidraw_scenes (created_at DESC);

-- Table des templates (future utilisation)
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(50),              -- "BMC", "SWOT", "PESTEL", etc.
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table des utilisateurs (future utilisation)
CREATE TABLE utilisateurs (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    nom VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table `keyv` (principale)

**Format de stockage :**

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `key` | TEXT | Identifiant unique | `SCENES:1604400859544720` |
| `value` | TEXT | Données JSON compressées | `{"version":2,"compression":"pako@1",...}` |
| `created_at` | TIMESTAMP | Date de création | `2026-05-16 10:30:45` |

**Requêtes utiles :**

```sql
-- Compter le nombre total de schémas
SELECT COUNT(*) FROM keyv WHERE key LIKE 'SCENES:%';

-- Lister les 10 derniers schémas créés
SELECT key, LENGTH(value) as size_bytes, created_at
FROM keyv
WHERE key LIKE 'SCENES:%'
ORDER BY created_at DESC
LIMIT 10;

-- Calculer la taille totale des schémas
SELECT 
    COUNT(*) as total_schemas,
    SUM(LENGTH(value)) as total_bytes,
    AVG(LENGTH(value)) as avg_bytes,
    MIN(created_at) as first_schema,
    MAX(created_at) as last_schema
FROM keyv
WHERE key LIKE 'SCENES:%';

-- Extraire un ID depuis la clé
SELECT 
    SUBSTRING(key FROM 8) as schema_id,  -- Enlève "SCENES:"
    created_at
FROM keyv
WHERE key LIKE 'SCENES:%'
ORDER BY created_at DESC;
```

### Format des données dans `value`

**Structure JSON compressée :**

```json
{
  "version": 2,
  "compression": "pako@1",
  "encryption": "AES-GCM",
  "data": "<données binaires base64>",
  "iv": "<vecteur d'initialisation>",
  "tag": "<tag d'authentification>"
}
```

Les données sont :
1. **Sérialisées** en JSON
2. **Compressées** avec pako (gzip)
3. **Chiffrées** avec AES-GCM
4. **Encodées** en base64

⚠️ **Les données ne sont PAS lisibles directement** dans PostgreSQL. Pour les décoder, il faut :
- La clé de chiffrement (présente dans l'URL)
- Déchiffrer avec AES-GCM
- Décompresser avec pako
- Parser le JSON

### Connexion en ligne de commande

```bash
# Depuis le VPS
ssh root@69.62.110.207

# Connexion psql
docker exec -it pk4s888o4wkc8ogokg0sg840 \
  psql -U excalidraw_backend -d excalidraw_storage

# Commandes psql utiles
\dt                    # Lister les tables
\d keyv                # Décrire la table keyv
\d+ excalidraw_scenes  # Décrire la table avec détails
\x                     # Activer l'affichage étendu
\q                     # Quitter
```

---

## 📊 Intégration NocoDB

### Connexion à la base

**Dans NocoDB, créer une nouvelle connexion "External Database" :**

```
Connection name:    excalidraw_storage
Host address:       10.0.1.23
Port number:        5432
Username:           excalidraw_backend
Password:           aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=
Database:           excalidraw_storage
Schema name:        public
Use SSL:            Non
```

**Capture d'écran de la config (pour référence) :**

![Configuration PostgreSQL NocoDB](../assets/nocodb-postgres-config.png)

### Vues recommandées dans NocoDB

#### Vue 1 : Dashboard des schémas

**Base :** `excalidraw_storage`  
**Table :** `keyv`

**Colonnes à afficher :**

| Colonne | Type NocoDB | Formule/Config |
|---------|-------------|----------------|
| ID Schéma | Formula | `SUBSTRING({key}, 8)` |
| Date création | DateTime | `{created_at}` |
| Taille (KB) | Formula | `ROUND(LENGTH({value}) / 1024, 2)` |
| Lien Excalidraw | Formula | `CONCATENATE("https://excalidraw.agnisolution.fr/#json=", SUBSTRING({key}, 8))` |

**Filtres :**
- `key` LIKE `SCENES:%`

**Tri :**
- Par `created_at` DESC (plus récents en premier)

#### Vue 2 : Statistiques globales

**Vue personnalisée avec agrégations :**

```sql
-- Requête SQL à utiliser dans NocoDB "SQL View"
SELECT 
    COUNT(*) as "Nombre total de schémas",
    ROUND(SUM(LENGTH(value)) / 1024 / 1024, 2) as "Taille totale (MB)",
    ROUND(AVG(LENGTH(value)) / 1024, 2) as "Taille moyenne (KB)",
    MIN(created_at) as "Premier schéma",
    MAX(created_at) as "Dernier schéma",
    DATE_PART('day', MAX(created_at) - MIN(created_at)) as "Jours d'utilisation"
FROM keyv
WHERE key LIKE 'SCENES:%';
```

#### Vue 3 : Activité par jour

```sql
-- Nombre de schémas créés par jour
SELECT 
    DATE(created_at) as "Date",
    COUNT(*) as "Schémas créés",
    ROUND(SUM(LENGTH(value)) / 1024 / 1024, 2) as "Données (MB)"
FROM keyv
WHERE key LIKE 'SCENES:%'
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC;
```

### Limitations NocoDB

⚠️ **NocoDB ne peut PAS :**
- Déchiffrer les données des schémas (besoin de la clé)
- Afficher le contenu des schémas (données binaires)
- Éditer les schémas (format propriétaire Excalidraw)

✅ **NocoDB PEUT :**
- Compter les schémas
- Voir les dates de création
- Calculer les tailles
- Générer des statistiques
- Exporter les métadonnées (CSV, Excel)
- Créer des dashboards de suivi

---

## 📁 Structure du projet

### Arborescence

```
opepartner-stack/
├── CLAUDE.md                        # Brief de contexte complet
├── README.md                        # Vue d'ensemble du projet
├── .env.example                     # Template variables d'environnement
├── .gitignore                       # Fichiers à ignorer par Git
│
├── docs/                            # 📚 Documentation
│   ├── ARCHITECTURE.md              # Ce fichier
│   ├── TROUBLESHOOTING.md           # Guide de dépannage
│   ├── DIAGNOSTIC-RAPIDE.md         # Aide-mémoire
│   ├── workflows.md                 # Workflows métier (TODO)
│   └── migration-guide.md           # Guide de migration (TODO)
│
├── infra/                           # 🏗️ Infrastructure et déploiement
│   ├── docker-compose/              # Compositions Docker
│   │   ├── excalidraw-proxy/        # Proxy Nginx
│   │   │   ├── Dockerfile           # Build proxy
│   │   │   ├── nginx.conf           # Config Nginx
│   │   │   └── traefik-*.yml        # Labels Traefik (exemples)
│   │   ├── excalidraw-frontend/     # Frontend custom (si besoin)
│   │   └── excalidraw-backend/      # Backend custom (futur)
│   │
│   ├── sql/                         # Scripts SQL
│   │   ├── 01_init_opepartner.sql   # Création base OPEPARTNER (futur)
│   │   └── migrations/              # Migrations SQL
│   │
│   └── traefik/                     # Config Traefik (exemples)
│       └── dynamic/                 # Configurations dynamiques
│
├── mcp-excalidraw/                  # 🤖 MCP custom (futur)
│   ├── src/                         # Code source Python/TypeScript
│   ├── .env.example                 # Variables MCP
│   └── README.md                    # Doc MCP
│
├── frontend-custom/                 # ⚛️ Frontend personnalisé (si modifié)
│   ├── src/                         # Code source React
│   ├── Dockerfile                   # Build frontend
│   └── package.json                 # Dépendances npm
│
├── auth-service/                    # 🔐 Service d'authentification
│   ├── Dockerfile                   # Build auth service
│   └── config.yml                   # Configuration auth
│
├── backend-simple/                  # 🖥️ Backend de test (développement)
│   ├── Dockerfile
│   └── src/
│
├── backups/                         # 💾 Sauvegardes
│   └── excalidraw-YYYYMMDD-HHMMSS/  # Backups horodatés
│       ├── docker-compose.yml
│       ├── excalidraw_storage.sql.gz
│       ├── *.json                   # Configs containers
│       └── RESTORE.sh               # Script de restauration
│
└── assets/                          # 🖼️ Ressources (images, etc.)
    └── nocodb-postgres-config.png   # Captures d'écran
```

### Fichiers clés

| Fichier | Rôle | À modifier ? |
|---------|------|--------------|
| `CLAUDE.md` | Contexte complet pour Claude | ✅ Oui (si changement majeur) |
| `README.md` | Vue d'ensemble publique | ✅ Oui (si nouvelles features) |
| `docs/TROUBLESHOOTING.md` | Guide de dépannage | ✅ Oui (si nouveau problème) |
| `infra/docker-compose/excalidraw-proxy/nginx.conf` | Config proxy | ⚠️ Rarement (architecture stable) |
| `infra/docker-compose/excalidraw-proxy/Dockerfile` | Build proxy | ⚠️ Rarement |
| `.env.example` | Template environnement | ✅ Oui (si nouvelles variables) |

### Branches Git

**Structure recommandée :**

- `main` → Production (déployé sur VPS)
- `develop` → Développement (tests locaux)
- `feature/*` → Nouvelles fonctionnalités
- `fix/*` → Corrections de bugs
- `docs/*` → Modifications documentation

---

## ⚙️ Fonctionnalités

### Fonctionnalités actuelles

| Fonctionnalité | Status | Description |
|----------------|--------|-------------|
| **Création de schémas** | ✅ Opérationnel | Dessin libre, formes, textes, flèches |
| **Sauvegarde serveur** | ✅ Opérationnel | Stockage PostgreSQL via API |
| **Partage par lien** | ✅ Opérationnel | Liens persistants https://excalidraw.../#json={id} |
| **Export PNG/SVG** | ✅ Opérationnel | Export local dans Excalidraw |
| **Chiffrement E2E** | ✅ Opérationnel | AES-GCM (clé dans l'URL) |
| **Compression** | ✅ Opérationnel | Pako (gzip) |
| **Vue NocoDB** | ✅ Opérationnel | Statistiques et métadonnées |
| **Monitoring Coolify** | ✅ Opérationnel | Logs et statuts containers |

### Fonctionnalités en développement

| Fonctionnalité | Status | ETA | Priorité |
|----------------|--------|-----|----------|
| **MCP Custom** | 🚧 Planifié | Q3 2026 | Haute |
| **Intégration AFFiNE** | 🚧 Planifié | Q3 2026 | Haute |
| **Templates BMC/SWOT/PESTEL** | 📋 Spec | Q3 2026 | Moyenne |
| **Authentification** | ⚠️ Partielle | - | Haute |
| **Collaboration temps réel** | 📋 Spec | Q4 2026 | Basse |
| **Base OPEPARTNER (14 tables)** | 📋 Spec | Q3 2026 | Haute |

### Cas d'usage détaillés

#### Cas d'usage 1 : Atelier BMC avec un client

**Scénario :**
1. Consultant ouvre Excalidraw sur son laptop
2. Partage son écran en visio avec le client
3. Crée un Business Model Canvas en temps réel
4. Ajoute des notes et commentaires au fur et à mesure
5. Clique sur "Share" pour sauvegarder
6. Envoie le lien au client par email
7. Le client peut ouvrir le lien et voir le BMC final

**Avantages :**
- ✅ Pas de compte à créer pour le client
- ✅ Lien permanent (pas d'expiration)
- ✅ Données stockées sur nos serveurs (RGPD OK)
- ✅ Possibilité d'exporter en PNG pour le livrable

#### Cas d'usage 2 : Documentation interne

**Scénario :**
1. Consultant crée un organigramme client
2. Sauvegarde dans Excalidraw
3. Ouvre NocoDB pour suivre le nombre de schémas créés
4. Exporte les statistiques mensuelles (nombre de schémas par client)

**Avantages :**
- ✅ Suivi de l'activité de conseil
- ✅ Statistiques pour reporting
- ✅ Base de données centralisée

#### Cas d'usage 3 (futur) : Génération automatique via MCP

**Scénario :**
1. Dans Claude Desktop, prompt : "Crée un BMC pour le client Dupont SAS"
2. MCP custom :
   - Vérifie si le client existe dans NocoDB
   - Génère un template BMC pré-rempli
   - Crée le schéma dans Excalidraw
   - Enregistre dans PostgreSQL
   - Crée un doc AFFiNE avec le lien embed
3. Claude retourne le lien Excalidraw + lien AFFiNE

**Avantages (futurs) :**
- ✅ Automatisation complète
- ✅ Intégration écosystème AGNI
- ✅ Gain de temps énorme

---

## 🚀 Déploiement

### Architecture de déploiement

**Plateforme :** VPS Hostinger (69.62.110.207)  
**Orchestrateur :** Coolify 4.0.0-beta  
**Méthode :** Docker Compose + Labels Traefik

### Workflow de déploiement

```
1. Développement local (Mac)
   - Modifier le code
   - Tester localement (Docker Desktop)
   - Commit Git
   │
   ▼
2. Push vers GitHub
   - Repository: github.com/christophe39/excalidraw
   - Branche: main
   │
   ▼
3. Build des images
   - Proxy: build local → transfer SCP
   - Frontend: build local → transfer SCP
   - Backend: pull depuis Docker Hub (kiliandeca)
   │
   ▼
4. Déploiement Coolify
   - UI Coolify: clic "Deploy"
   - OU: docker compose up -d via SSH
   │
   ▼
5. Vérification post-deploy
   - Checklist dans TROUBLESHOOTING.md
   - Test POST/GET API
   - Test Excalidraw UI
```

### Commandes de déploiement

**Build et transfert du proxy :**

```bash
# Sur le Mac
cd /Volumes/ZIKE/codage/projet_excalidraw_opepartner/infra/docker-compose/excalidraw-proxy

# Build pour AMD64
docker buildx build --platform linux/amd64 -t excalidraw-proxy:latest --load .

# Sauvegarder et transférer
docker save excalidraw-proxy:latest | gzip > /tmp/excalidraw-proxy.tar.gz
scp /tmp/excalidraw-proxy.tar.gz root@69.62.110.207:/tmp/

# Sur le VPS
ssh root@69.62.110.207
gunzip < /tmp/excalidraw-proxy.tar.gz | docker load
```

**Déploiement via Coolify :**

1. Aller sur https://coolify.agnisolution.fr
2. Service "excalidraw" → Configuration
3. Vérifier que le Backend n'a PAS de domaine
4. Cliquer sur "Deploy"
5. Attendre 30 secondes
6. Vérifier les logs

**Déploiement via SSH :**

```bash
ssh root@69.62.110.207
cd /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0

# Option 1: Restart complet
docker compose restart

# Option 2: Recréer un service spécifique
docker compose up -d --force-recreate proxy

# Option 3: Tout redémarrer avec les nouvelles images
docker compose down
docker compose up -d
```

### Checklist post-déploiement

- [ ] Vérifier que les 3 containers tournent
- [ ] Vérifier que le backend n'a PAS de domaine dans Coolify
- [ ] Vérifier les routes Traefik (pas de route backend)
- [ ] Redémarrer le proxy (`docker restart proxy-*`)
- [ ] Tester POST API (curl)
- [ ] Tester GET API (curl)
- [ ] Tester dans Excalidraw (UI)
- [ ] Vérifier les logs (pas d'erreurs 502/404)

---

## 🎓 Cas d'usage

### Pour OPEPARTNER (Consulting)

**Ateliers clients :**
- Business Model Canvas
- SWOT Analysis
- PESTEL Analysis
- Value Proposition Canvas
- Organigrammes
- Chaînes de valeur
- Plans 90 jours

**Documentation projets :**
- Schémas de process
- Feuilles de route
- Livrables visuels
- Présentations clients

**Collaboration :**
- Partage avec les clients (liens)
- Travail en équipe (futurs rooms)
- Archives des projets (PostgreSQL)

### Pour CaloCalc (Technique - futur)

**Documentation système :**
- Architecture logicielle
- Flux de données
- Schémas d'infrastructure
- Diagrammes de séquence

**Schémas techniques :**
- Schémas de principe chauffage
- Plans de zonage
- Organigrammes techniques

---

## 📞 Support et maintenance

### Contacts

- **Admin système :** Christophe Martin (cmartin@agniconsult.fr)
- **Repository :** https://github.com/christophe39/excalidraw
- **Issues :** https://github.com/christophe39/excalidraw/issues

### Documentation complémentaire

- **Troubleshooting :** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Diagnostic rapide :** [DIAGNOSTIC-RAPIDE.md](./DIAGNOSTIC-RAPIDE.md)
- **CLAUDE.md :** Brief de contexte complet pour Claude

### Monitoring

**Logs containers :**
```bash
docker logs -f proxy-o8wsgoowkcogkgk0g8o4g8s0
docker logs -f backend-o8wsgoowkcogkgk0g8o4g8s0
docker logs -f frontend-o8wsgoowkcogkgk0g8o4g8s0
```

**Traefik dashboard :**
```bash
ssh -L 8080:localhost:8080 root@69.62.110.207
# Ouvrir http://localhost:8080 dans le navigateur
```

**PostgreSQL monitoring :**
```sql
-- Taille de la base
SELECT pg_size_pretty(pg_database_size('excalidraw_storage'));

-- Nombre de connexions actives
SELECT count(*) FROM pg_stat_activity WHERE datname = 'excalidraw_storage';

-- Tables les plus volumineuses
SELECT 
    relname as table,
    pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## 📝 Changelog

### Version 1.0.0 (16 mai 2026)

**Ajouté :**
- Architecture complète 3-tiers (Frontend, Proxy, Backend)
- Intégration PostgreSQL pour stockage pérenne
- Connexion NocoDB pour analyse
- Documentation exhaustive (ARCHITECTURE.md, TROUBLESHOOTING.md)
- Backups automatiques
- Déploiement via Coolify

**Connu :**
- Collaboration temps réel désactivée
- Pas encore de templates BMC/SWOT/PESTEL
- MCP custom en développement
- Authentification basique uniquement

**À venir (Q3 2026) :**
- MCP custom pour génération automatique
- Intégration AFFiNE
- Base OPEPARTNER (14 tables)
- Templates métier
- Amélioration auth

---

**Ce document est vivant. Mets-le à jour à chaque évolution majeure de l'architecture.**
