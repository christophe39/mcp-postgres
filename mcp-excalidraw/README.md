# MCP Custom Excalidraw

> Serveur MCP remote HTTPS pour la génération automatisée de schémas Excalidraw via Claude

## 🎯 Objectif

Exposer des outils Claude permettant de créer, modifier et rechercher des scènes Excalidraw, avec intégration automatique dans NocoDB et AFFiNE.

## 🛠️ Outils exposés (MVP)

### CRUD de base
- `create_scene(json, title, contexte, client?, mission?, document_type)` — Création scène + upsert NocoDB + doc AFFiNE
- `get_scene(id)` — Récupération du JSON
- `update_scene(id, json)` — Modification (version++)
- `list_scenes(filter?)` — Recherche multi-critères

### Export
- `export_scene_png(id)` — Export PNG
- `export_scene_svg(id)` — Export SVG

### Templates
- `create_bmc(client_name?, mission?)` — Business Model Canvas pré-rempli
- `create_pestel(client_name?, mission?)` — Analyse PESTEL
- `create_swot(client_name?, mission?)` — Matrice SWOT
- `create_organigramme(client_name?, mission?)` — Organigramme type

## 🏗️ Architecture technique

**Stack à définir** :
- Option A : **Python + FastMCP** (recommandé pour rapidité)
- Option B : **TypeScript + MCP SDK** (cohérence avec stack Excalidraw)

**Déploiement** :
- Conteneur Docker via Coolify
- Exposition HTTPS : `mcp-excalidraw.agnisolution.fr`
- Traefik + Let's Encrypt automatique

**Intégrations** :
- PostgreSQL `opepartner` (table `Schemas_Excalidraw` + `Clients`)
- NocoDB API (upsert Client, insert Schemas_Excalidraw)
- AFFiNE API (création/maj docs dans workspace OPEPARTNER)
- Excalidraw Storage Backend (push/pull JSON)

## 📋 Workflow type

Prompt utilisateur : *"Crée un BMC pour Client Dupont SAS"*

1. MCP appelle `create_bmc("Dupont SAS")`
2. Génère JSON Excalidraw (9 cases BMC pré-structurées)
3. Push JSON vers Excalidraw Storage Backend → récupère `scene_id`
4. Upsert Client "Dupont SAS" dans NocoDB → récupère `client_id`
5. Insert ligne dans `Schemas_Excalidraw` :
   - `excalidraw_id`, `client_id`, `document_type=BMC_visuel`
   - `edit_url`, `preview_url`, `confidentiel=true`
6. Crée doc AFFiNE sous `03 — Clients / Missions / Dupont SAS / [BMC]`
   - Embed preview Excalidraw + lien d'édition
7. Retourne à Claude les URLs (édition + preview)

## 🔐 Variables d'environnement

Voir `.env.example` dans ce dossier.

Essentielles :
- `DATABASE_URL` — Connexion PostgreSQL
- `NOCODB_URL` + `NOCODB_TOKEN`
- `AFFINE_API_URL` + `AFFINE_TOKEN` + `AFFINE_WORKSPACE_OPEPARTNER`
- `EXCALIDRAW_BACKEND_URL`
- `MCP_EXCALIDRAW_SECRET` — Auth du MCP remote

## 🚀 Développement

*À compléter lors du démarrage du développement (Phase 5)*

## 📝 TODO

- [ ] Choisir stack (Python FastMCP vs TypeScript MCP SDK)
- [ ] Bootstrap projet + structure
- [ ] Implémenter outils CRUD
- [ ] Implémenter templates (BMC, PESTEL, SWOT)
- [ ] Tests unitaires des outils
- [ ] Dockerfile + docker-compose
- [ ] Déploiement Coolify
- [ ] Configuration Connectors Claude.ai

---

*Dernière mise à jour : 15 mai 2026*
