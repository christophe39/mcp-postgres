# CLAUDE.md — Contexte projet OPEPARTNER

> Brief de contexte pour Claude Code. À lire en premier avant toute action.

## 🎯 Vision globale

Mise en place d'un **système Excalidraw self-hosted** intégré à **AFFiNE** (déjà self-hosted) et **NocoDB**, piloté par un **MCP custom** à développer. Objectif : générer et maintenir des schémas (BMC, organigrammes, PESTEL, chaînes de valeur, schémas techniques) directement depuis des prompts Claude, avec stockage pérenne sous mon contrôle.

**Deux cas d'usage cibles**, distincts mais utilisant la même brique technique :

1. **Consulting OPEPARTNER** (priorité actuelle) — Dossiers clients confidentiels (RGPD), schémas stratégiques : Business Model Canvas, SWOT, PESTEL, organigrammes, plans 90 jours.
2. **Documentation CaloCalc** (plus tard) — Schémas techniques publiables : architecture système, flux UI, schémas de principe chauffage.

**Principe directeur de migrabilité** : tout est conçu dès le départ pour qu'OPEPARTNER puisse être déménagé un jour sur un VPS dédié sans douleur. Cloisonnement strict des données entre OPEPARTNER, CaloCalc et AGNI Consult.

## 🏗️ Infrastructure VPS Hostinger (existante)

- **VPS** : Hostinger, IP `69.62.110.207`, hostname `srv764918.hstgr.cloud`, user SSH `root` port 22
- **Orchestration** : Coolify + Traefik + Cloudflare (DNS + SSL)
- **Domaine principal** : `agnisolution.fr`
- **Stockage objet** : Cloudflare R2 (bucket `calocalc-uploads` notamment)

### Containers Postgres en place (audit récent)

| Container ID | Image | User | Bases | Rôle |
|---|---|---|---|---|
| `c0408wgcs08kc0w480koowcs` | postgres standard | `agni_admin` | `Base_AgniConsult`, `calocalc_inscription`, `db_agni`, `nocodb_db`, `postgres` | **Container business principal** |
| `t8440wgs04wwk0cc4w4ko800` | postgres | `crm_user` | `crm_candidatures` | CRM dédié |
| `i004k4ckow8c8o8w004wk8oc` | `pgvector/pgvector:pg17` | `affine_admin` | `affine` | AFFiNE self-hosted |
| `postgresql-bc848ocwk08wc4wg0804oogw` | `postgres:16-alpine` | `OhwmQIIW1R05KAI9` | `umami` | Analytics Umami |
| `pg0kgg4g8kwgg04s4wg0sos8` | postgres | `postgres` | (aucune base applicative) | À investiguer / probable legacy |

### Décision pour OPEPARTNER

**On crée la nouvelle base `opepartner` dans le container business principal** (`c0408wgcs08kc0w480koowcs`, user `agni_admin`).

Justification :
- Cohérence avec `calocalc_inscription` et `db_agni` déjà présentes
- Surcharge ressources minimale (~5-50 MB RAM additionnels vs 150-300 MB pour un nouveau container)
- Migration future facile via `pg_dump opepartner > backup.sql` ciblé sur cette database uniquement
- Si isolation maximale nécessaire un jour, on extraira la base vers un container dédié à ce moment-là (pas de regret)

## 🎨 Composants à mettre en place

### 1. Base PostgreSQL `opepartner`

Création dans le container `c0408wgcs08kc0w480koowcs` avec 14 tables MVP (modèle relationnel détaillé plus bas).

### 2. Excalidraw self-hosted

Déployer via Coolify deux services :

- `excalidraw/excalidraw` — frontend React (HTML/JS statique)
- `kitsteam/excalidraw-storage-backend` — backend de stockage qui donne des liens persistants type `excalidraw.opepartner.fr/#json={uuid}`

Optionnel pour la collaboration temps réel (peut être ajouté plus tard) : `excalidraw/excalidraw-room`.

**Sous-domaine cible** : `excalidraw.opepartner.fr` ou `excalidraw.agnisolution.fr` (à arbitrer — préférence pour `opepartner.fr` si possible, alignement avec la stratégie de migrabilité par sous-domaines logiques).

**Sécurité** : auth Traefik basic auth ou ForwardAuth + IDs longs aléatoires sur les scènes (pas devinables). RGPD-critique pour les dossiers clients OPEPARTNER.

### 3. MCP custom Excalidraw

À développer, hébergé sur le VPS comme MCP **remote HTTPS** (exposé via sous-domaine type `mcp-excalidraw.agnisolution.fr`). Permettra d'être utilisé depuis Claude Desktop, Claude.ai web, app iOS, app iPad — couverture cross-device complète.

**Préférence langage** : à confirmer avec l'utilisateur (Python FastMCP recommandé pour la rapidité, ou TypeScript pour cohérence avec le stack JS existant).

**Outils à exposer (MVP)** :

- `create_scene(json, title, contexte, client?, mission?, document_type)` — push scène dans Excalidraw + upsert NocoDB + crée/maj doc AFFiNE
- `get_scene(id)` — récupère le JSON
- `update_scene(id, json)` — modifie en gardant le même ID (version++)
- `list_scenes(filter?)` — recherche multi-critères
- `export_scene_png(id)`, `export_scene_svg(id)` — pour publication doc
- **Outils templates** : `create_bmc()`, `create_pestel()`, `create_swot()`, `create_organigramme()`

**Variables d'environnement (clé de migrabilité — pas de hardcoding) :**

```
NOCODB_URL
NOCODB_TOKEN
AFFINE_API_URL
AFFINE_TOKEN
AFFINE_WORKSPACE_OPEPARTNER=3869ae28-9638-4390-a28d-905ff5c563d6
AFFINE_WORKSPACE_CALOCALC=<à définir>
EXCALIDRAW_BACKEND_URL
POSTGRES_URL=postgresql://agni_admin:***@host:5432/opepartner
N8N_WEBHOOK_BASE_URL
```

## 🗄️ Modèle relationnel NocoDB / Postgres OPEPARTNER

```
Clients ──1:N── Missions ──1:N── Ateliers
                   │
                   ├──1:N── Livrables ──N:1── Référentiel_modèles
                   ├──1:N── Schemas_Excalidraw  (NOUVEAU — pour le MCP custom)
                   ├──1:N── Business_Model_Canvas
                   ├──1:N── SWOT
                   ├──1:N── PESTEL
                   ├──1:N── Value_Proposition_Canvas
                   ├──1:N── Plan_90_jours
                   ├──1:N── Actions
                   └──1:N── Comptes_rendus

Clients ──1:N── Contacts
```

**14 tables MVP** : Clients, Contacts, Missions, Ateliers, Livrables, Actions, Comptes_rendus, Référentiel_modèles, Business_Model_Canvas, SWOT, PESTEL, Value_Proposition_Canvas, Plan_90_jours, **Schemas_Excalidraw**.

**Colonnes communes** à toutes les tables documentaires : `client_id`, `mission_id`, `document_type`, `document_title`, `status`, `version`, `owner`, `created_at`, `validated_at`, `html_url`, `affine_url`, `excalidraw_url`, `notes_internal`.

**Spécifique Schemas_Excalidraw** : `excalidraw_id`, `edit_url`, `preview_url`, `affine_doc_id`, `confidentiel`, `tags`.

## 📁 Workspaces AFFiNE (déjà créés)

- **AGNI Consult** : `85a5d444-80db-49e6-996d-f2ecda4d66ae` (workspace historique, contient les docs CaloCalc, AGNI, perso)
- **OPEPARTNER** : `3869ae28-9638-4390-a28d-905ff5c563d6` (workspace dédié, **structure 01—06 + TEMPORAIRE déjà en place**)

### Structure Organize folders du workspace OPEPARTNER

```
🎯 OPEPARTNER — Cadre de travail
📁 01 — Identité & Stratégie
   ├─ 🎯 OPEPARTNER — Cadre de travail
   └─ Organisation OPEPARTNER
📁 02 — Offres & Services consulting
📁 03 — Clients / Missions
📁 04 — Communication
📁 05 — Administratif & juridique
📁 06 — Outils & Process
   ├─ OPEPARTNER · Spec technique
   ├─ AFFiNE · Collections & dossiers
   └─ 📁 Templates BMC
        ├─ 📋 Modèle · Business Model Canvas
        ├─ 📋 Modèle · Business Canvas (visuel)
        └─ 📋 BMC · Contenu type des 9 cases
📁 TEMPORAIRE
```

## 🔌 Stack MCP

### Claude Desktop (Mac mini + MacBook Air)

MCP **locaux** configurés dans `~/Library/Application Support/Claude/claude_desktop_config.json` :

- `affine-agni` — pointe sur le workspace AGNI Consult (à configurer)
- `affine-opepartner` — pointe sur le workspace OPEPARTNER (à configurer)
- `affine-native` — MCP DAWNCR0W natif AFFiNE
- MCP NocoDB (par base), Stripe, Notion, Google Drive, Gmail, Calendar, etc.

### Claude Code (VS Code, sur Mac)

- Accès terminal direct → SSH, Docker, Postgres CLI
- Accès filesystem du Mac → édition de fichiers, Git
- **Outil principal pour toutes les opérations VPS et le dev du MCP custom**

### Claude.ai web / iOS / iPad / iPhone

- MCP **remote** uniquement (NocoDB, n8n, Stripe, Notion, Drive, Gmail, Calendar)
- Pour avoir AFFiNE et le futur MCP Excalidraw custom accessibles cross-device, ils doivent être exposés en HTTPS remote (à étudier pour AFFiNE, c'est l'objectif natif du MCP Excalidraw custom)

## 🤝 Mode de collaboration souhaité

### Avec Claude Code (toi)

- **Itératif et validé par étapes** : tu proposes, j'arbitre, on exécute. Pas d'actions destructives sans confirmation explicite.
- **Versioning Git systématique** : tout le code du MCP custom + scripts d'infra (docker-compose, scripts SQL) dans un repo Git dès la première ligne.
- **Variables d'environnement** plutôt que hardcoding : tout ce qui est URL/credential/identifiant externe passe par `.env` (avec `.env.example` versionné).
- **Documentation au fil de l'eau** : chaque composant nouveau doit avoir un README court qui explique son rôle et son usage.
- **Tests fonctionnels rapides** avant de passer à l'étape suivante : "ça marche pour un cas simple" avant d'enrichir.
- **Pas de génération massive** : on construit petit à petit, on valide, on enrichit.

### Avec Claude Desktop (parallèle)

- Claude Desktop continue à gérer la couche métier : AFFiNE (création/maj des docs OPEPARTNER), NocoDB (lecture des données via MCP), n8n (création workflows), réflexion stratégique.
- Quand un livrable doit être documenté, je le crée comme doc AFFiNE depuis Claude Desktop.
- L'info circule dans les deux sens : Claude Code peut générer du code que je discute ensuite avec Claude Desktop, et inversement.

## 📋 Tâches immédiates pour Claude Code (par ordre)

### Phase 1 — Préparation environnement local

1. Vérifier que le repo Git local est initialisé (créer un repo `opepartner-stack` si besoin)
2. Créer la structure de dossiers : `infra/` (docker-compose, scripts SQL), `mcp-excalidraw/` (code du MCP custom), `docs/`
3. Mettre en place un `.env.example` et un `.gitignore` correct

### Phase 2 — Création base PostgreSQL OPEPARTNER

1. Se connecter en SSH au VPS (`ssh root@69.62.110.207`)
2. Créer la base via `docker exec c0408wgcs08kc0w480koowcs psql -U agni_admin -c "CREATE DATABASE opepartner;"`
3. Générer le script SQL des 14 tables (FK, index, contraintes) → `infra/sql/01_init_opepartner.sql`
4. Exécuter le script via `docker exec -i c0408wgcs08kc0w480koowcs psql -U agni_admin -d opepartner < 01_init_opepartner.sql`
5. Valider via `\dt` que les 14 tables existent
6. Commit Git

### Phase 3 — Connexion NocoDB

1. Dans l'UI NocoDB existante, créer une nouvelle "Base" connectée à la database `opepartner` (External database connection)
2. Vérifier que les 14 tables apparaissent avec leurs relations
3. Générer un token MCP pour cette base (à ajouter dans `claude_desktop_config.json` côté Mac)

### Phase 4 — Déploiement Excalidraw self-hosted

1. Préparer le `docker-compose.yml` pour Coolify avec :
   - Service `excalidraw` (frontend) + Traefik labels pour sous-domaine
   - Service `excalidraw-storage-backend` + Traefik labels
   - Optionnel : auth basic Traefik pour la confidentialité
2. Configurer le sous-domaine DNS dans Cloudflare
3. Déployer via Coolify
4. Tests : créer une scène manuellement, obtenir un lien persistant, le rouvrir

### Phase 5 — Développement du MCP custom Excalidraw

1. Bootstrap projet (Python FastMCP ou TypeScript MCP SDK selon arbitrage)
2. Implémenter les outils CRUD : `create_scene`, `get_scene`, `update_scene`, `list_scenes`
3. Intégration NocoDB : upsert Clients, insert Schemas_Excalidraw
4. Intégration AFFiNE : création/maj doc dans le workspace OPEPARTNER
5. Outils templates : `create_bmc`, `create_pestel`, `create_swot`
6. Dockerfile + déploiement via Coolify avec sous-domaine `mcp-excalidraw.agnisolution.fr`
7. Configuration des Connectors Claude.ai (HTTPS remote MCP)

### Phase 6 — Tests bout-en-bout

Prompt type : *"Crée un BMC pour Client Dupont SAS"* → vérifier que :

1. La scène est créée dans Excalidraw avec lien `excalidraw.opepartner.fr/#json={id}`
2. La ligne est insérée dans `Schemas_Excalidraw` avec `client_id`, `document_type=BMC_visuel`
3. Le Client Dupont SAS est créé (ou retrouvé) dans la table `Clients`
4. Un doc AFFiNE est créé sous `03 — Clients / Missions / Dupont SAS / [BMC]` avec preview embed + lien d'édition

## 🎯 Règles d'or de migrabilité (à respecter dans tout le code)

1. **Sous-domaines logiques** : `excalidraw.opepartner.fr`, `nocodb-opepartner.agnisolution.fr` plutôt que générique
2. **Variables d'environnement** : aucun hardcoding d'URL ou de credential
3. **Workflows n8n préfixés** `OPEPARTNER_*` pour pouvoir filtrer à l'export
4. **Pas de logique métier dans NocoDB UI** : tout en SQL ou dans le MCP custom (pour pouvoir migrer sans dépendance à NocoDB si besoin)
5. **Backup automatisé** : `pg_dump opepartner` quotidien vers R2 ou Backblaze
6. **Documentation des dépendances** : tout composant qui dépend d'un autre service est documenté dans son README

## 🗓️ Roadmap globale (vue d'ensemble)

| Phase | Description | Outil principal | Statut |
|---|---|---|---|
| A | Cloisonnement AFFiNE (workspace OPEPARTNER) | Claude Desktop | ✅ Fait |
| B | Migration docs OPEPARTNER | Claude Desktop | ✅ Fait |
| C | Nettoyage ancien workspace | Claude Desktop | ✅ Fait |
| D | Config MCP locale (`affine-agni` + `affine-opepartner`) | Manuel (Mac) | 🟡 En cours |
| E | Création base PostgreSQL + tables OPEPARTNER | **Claude Code** | ⏳ À faire |
| F | Connexion NocoDB à la nouvelle base | Claude Desktop + UI | ⏳ À faire |
| G | Déploiement Excalidraw self-hosted | **Claude Code** | ⏳ À faire |
| H | Développement MCP custom Excalidraw | **Claude Code** | ⏳ À faire |
| I | Connexion MCP custom dans Claude.ai Connectors | Manuel | ⏳ À faire |
| J | Création Projects Claude.ai "OPEPARTNER" et "CaloCalc" | Manuel + Claude Desktop | ⏳ À faire |
| K | Tests bout-en-bout | **Claude Code** + Claude Desktop | ⏳ À faire |
| L | Skills consulting-opepartner (optionnel, plus tard) | Claude Desktop | ⏳ Plus tard |

## 📌 Notes importantes pour toi (Claude Code)

- Je suis **Christophe**, dirigeant d'AGNI Consult (SASU, conseil chauffage bois/granulés) et de OPEPARTNER (conseil généraliste). Je communique en français.
- Mon stack historique : no-code (WeWeb, Xano, Airtable, n8n, Make). Migration progressive vers du dev plus traditionnel (VS Code, React Native/Expo, Node/Express, Prisma, Claude Code).
- Mon VPS Hostinger héberge déjà beaucoup de choses : Coolify, Traefik, AFFiNE, NocoDB, Directus, n8n, Postgres (5 containers), AppFlowy. Je suis **strict sur la souveraineté des données** — self-hosted whenever possible.
- Je suis **méthodique et persistant**, je ne lâche pas un projet à mi-chemin. Évite de me suggérer de "faire une pause" ou "reprendre demain" — sauf vrai problème de fond.
- Pour les actions destructives (suppression de bases, écrasement de fichiers, déploiements qui remplacent quelque chose), **demande confirmation explicite avant**.

## 🔗 Liens et IDs utiles

- **AFFiNE OPEPARTNER** : https://affine.agnisolution.fr/workspace/3869ae28-9638-4390-a28d-905ff5c563d6
- **AFFiNE AGNI Consult** : https://affine.agnisolution.fr/workspace/85a5d444-80db-49e6-996d-f2ecda4d66ae
- **VPS SSH** : `ssh root@69.62.110.207`
- **Hostname** : `srv764918.hstgr.cloud`
- **Container Postgres business** : `c0408wgcs08kc0w480koowcs` (user `agni_admin`)
- **Documents AFFiNE de référence** :
  - `🎯 OPEPARTNER — Cadre de travail` : doc d'accueil et vision
  - `Organisation OPEPARTNER` : architecture 3 couches (AFFiNE/NocoDB/n8n) et workflow standard
  - `OPEPARTNER · Spec technique` : modèle relationnel détaillé, table Schemas_Excalidraw, workflow MCP
  - `📋 BMC · Contenu type des 9 cases` : matière pédagogique pour le BMC, source des futurs templates Excalidraw

---

*Document généré le 15 mai 2026. À tenir à jour au fil du projet.*
