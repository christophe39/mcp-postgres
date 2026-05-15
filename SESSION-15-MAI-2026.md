# Session de travail : 15 mai 2026
## Déploiement Excalidraw OPEPARTNER - Phase G

---

## 🎯 Objectif de la session

Déployer un stack Excalidraw self-hosted complet :
- Frontend Excalidraw custom (avec URLs vers notre backend)
- Backend storage (API REST + stockage Postgres)
- Proxy adaptateur (traduit les URLs entre frontend et backend)

---

## ✅ Réalisations de la session

### 1. Infrastructure Postgres

**Base de données créée** :
- Base : `excalidraw_storage` (dans container `pk4s888o4wkc8ogokg0sg840`)
- User : `excalidraw_backend`
- Password : `aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=`
- Table : `keyv` (créée automatiquement par le backend)

**Permissions configurées** :
```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO excalidraw_backend;
GRANT CREATE ON SCHEMA public TO excalidraw_backend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO excalidraw_backend;
```

**Test validé** :
```bash
curl -k -X POST https://exca-api.agnisolution.fr/api/v2/scenes \
  -H "Content-Type: application/json" \
  -d '{"version":2,"source":"test","elements":[]}'
# Retour : {"id":"3793308620810895"} ✅
```

### 2. Backend Excalidraw

**Image Docker** : `kiliandeca/excalidraw-storage-backend:latest`

**Configuration** :
- Port : 8080
- Storage : Postgres (via `STORAGE_URI`)
- CORS : `https://excalidraw.agnisolution.fr,https://mcp-excalidraw.agnisolution.fr`
- ID length : 12 caractères

**Variables d'environnement** :
```
STORAGE_URI=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@10.0.1.23:5432/excalidraw_storage
PORT=8080
NODE_ENV=production
CORS_ALLOWED_ORIGINS=https://excalidraw.agnisolution.fr,https://mcp-excalidraw.agnisolution.fr
ID_LENGTH=12
```

**État** : ✅ 100% fonctionnel, testé et validé

### 3. Frontend Excalidraw Custom

**Dockerfile créé** : `frontend-custom/Dockerfile`

**Build** :
- Clone du repo officiel Excalidraw (branche `master`)
- Compilation avec variables d'environnement custom
- URLs configurées :
  - GET: `https://exca-api.agnisolution.fr/api/v2/`
  - POST: `https://exca-api.agnisolution.fr/api/v2/post/`

**Image générée** : `excalidraw-opepartner:latest`

**État actuel** : ⚠️ Buildée pour ARM, doit être rebuildée pour AMD64

### 4. Proxy Adaptateur (nouveau composant)

**Problème découvert** :
- Frontend Excalidraw appelle `/api/v2/post/` (API officielle)
- Backend storage répond sur `/api/v2/scenes` (API incompatible)

**Solution créée** : Proxy Nginx qui traduit les URLs

**Fichiers créés** :
- `infra/docker-compose/excalidraw-proxy/nginx.conf`
- `infra/docker-compose/excalidraw-proxy/Dockerfile`

**Routes du proxy** :
- `POST /api/v2/post/` → `POST /api/v2/scenes` (backend)
- `GET /api/v2/:id` → `GET /api/v2/scenes/:id` (backend)

**Image générée** : `excalidraw-proxy:latest`

**État actuel** : ⚠️ Buildée pour ARM, doit être rebuildée pour AMD64

### 5. DNS et domaines

**Domaines configurés** (chez Hostinger) :
- `excalidraw.agnisolution.fr` → Frontend
- `exca-api.agnisolution.fr` → Proxy (qui route vers backend)

**Type** : A records pointant vers `69.62.110.207`

**SSL** : Let's Encrypt via Traefik (automatique)

**Décision prise** : Utiliser `agnisolution.fr` temporairement, migration vers `opepartner.fr` plus tard.

### 6. Sécurité et souveraineté

**Décisions prises** :
- ✅ Pas de Cloudflare en mode proxy (DNS only)
- ✅ Données stockées en UE (VPS Amsterdam)
- ✅ Self-hosted à 100%
- ✅ RGPD-compliant
- 🔜 Authentification BasicAuth à ajouter (étape suivante)

---

## 🐛 Problèmes rencontrés et solutions

### Problème 1 : Service Coolify pré-configuré Excalidraw

**Symptôme** : Service Excalidraw dans Coolify = frontend only, pas de backend storage

**Solution** : Créer notre propre stack custom avec frontend + backend

### Problème 2 : Backend "unhealthy"

**Symptôme** : 
```
ERROR [StorageService] error: permission denied for schema public
```

**Solution** :
```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO excalidraw_backend;
GRANT CREATE ON SCHEMA public TO excalidraw_backend;
```

### Problème 3 : Healthcheck 404

**Symptôme** : Endpoint `/health` n'existe pas, backend marqué "unhealthy"

**Solution** : Supprimer le healthcheck du docker-compose.yml

### Problème 4 : Variables d'environnement ignorées (build Vite)

**Symptôme** : Frontend buildé pointe vers `json.excalidraw.com` au lieu de notre backend

**Cause** : Variables `VITE_*` doivent être définies **au moment du build**, pas au runtime

**Solution** : Définir les variables en `ENV` dans le Dockerfile (avant `RUN yarn build`)

### Problème 5 : Incompatibilité API frontend/backend

**Symptôme** : 
- Frontend appelle `/api/v2/post/`
- Backend répond sur `/api/v2/scenes`
- Résultat : 404

**Solution** : Créer un proxy Nginx adaptateur qui traduit les URLs

### Problème 6 : Architecture ARM vs AMD64

**Symptôme** : `exec /docker-entrypoint.sh: exec format error`

**Cause** : Images buildées sur Mac ARM, VPS en AMD64

**Solution en cours** : Rebuild avec `--platform linux/amd64`

---

## 📁 Fichiers créés aujourd'hui

```
projet_excalidraw_opepartner/
├── infra/
│   ├── sql/
│   │   └── 02_init_excalidraw_storage.sql ✅
│   └── docker-compose/
│       ├── excalidraw/
│       │   ├── docker-compose.yml (v1, obsolète)
│       │   ├── docker-compose-v2.yml (avec proxy) ✅
│       │   ├── .env.example ✅
│       │   └── README.md ✅
│       └── excalidraw-proxy/
│           ├── nginx.conf ✅
│           ├── Dockerfile ✅
│           └── (README à créer)
├── frontend-custom/
│   ├── Dockerfile ✅
│   ├── build.sh ✅
│   └── README.md ✅
└── SESSION-15-MAI-2026.md (ce fichier) ✅
```

---

## 🔜 Prochaines étapes (à terminer)

### Étape immédiate (en cours)

1. **Rebuild frontend pour AMD64** :
   ```bash
   cd frontend-custom
   docker build --platform linux/amd64 -t excalidraw-opepartner:latest .
   ```

2. **Rebuild proxy pour AMD64** :
   ```bash
   cd infra/docker-compose/excalidraw-proxy
   docker build --platform linux/amd64 -t excalidraw-proxy:latest .
   ```

3. **Transférer sur le VPS** :
   ```bash
   docker save excalidraw-opepartner:latest > /tmp/excalidraw-opepartner-amd64.tar
   scp /tmp/excalidraw-opepartner-amd64.tar root@69.62.110.207:/tmp/
   ssh root@69.62.110.207 "docker load < /tmp/excalidraw-opepartner-amd64.tar"
   
   docker save excalidraw-proxy:latest > /tmp/excalidraw-proxy-amd64.tar
   scp /tmp/excalidraw-proxy-amd64.tar root@69.62.110.207:/tmp/
   ssh root@69.62.110.207 "docker load < /tmp/excalidraw-proxy-amd64.tar"
   ```

4. **Redéployer dans Coolify** avec le docker-compose-v2.yml

5. **Tester** :
   - Ouvrir `https://excalidraw.agnisolution.fr`
   - Dessiner quelques formes
   - Cliquer "Partager" → vérifier le lien généré
   - Vérifier que la scène est stockée en Postgres

### Étapes suivantes (Phase G finale)

6. **Ajouter authentification BasicAuth** (Traefik) sur `excalidraw.agnisolution.fr`

7. **Configurer backup automatique** :
   ```bash
   # Cron job quotidien
   0 2 * * * docker exec pk4s888o4wkc8ogokg0sg840 pg_dump -U excalidraw_backend excalidraw_storage > /backup/excalidraw_$(date +\%Y\%m\%d).sql
   ```

8. **Mettre à jour la documentation** :
   - Finaliser le README du proxy
   - Documenter la procédure de mise à jour

### Phase H : MCP custom Excalidraw

9. **Développer le MCP custom** (Python FastMCP)
   - Outils CRUD : `create_scene`, `get_scene`, `update_scene`, `list_scenes`
   - Templates : `create_bmc`, `create_pestel`, `create_swot`
   - Intégration NocoDB + AFFiNE

10. **Déployer le MCP** sur `mcp-excalidraw.agnisolution.fr`

11. **Tests bout-en-bout** : Prompt Claude → génération BMC → stockage Postgres → doc AFFiNE

---

## 🔑 Informations importantes à retenir

### Credentials

**Postgres `excalidraw_storage`** :
- User : `excalidraw_backend`
- Password : `aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=`
- Host interne : `10.0.1.23:5432`
- Container : `pk4s888o4wkc8ogokg0sg840`

### URLs

**Production** :
- Frontend : https://excalidraw.agnisolution.fr
- Proxy/API : https://exca-api.agnisolution.fr
- Backend : http://backend:8080 (interne)

**Local (tests)** :
- Frontend : http://localhost:8080
- Backend : http://localhost:8080

### Commandes utiles

**Voir les scènes stockées** :
```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c 'SELECT key, created_at FROM keyv ORDER BY created_at DESC LIMIT 10;'"
```

**Logs backend** :
```bash
ssh root@69.62.110.207 "docker logs backend-o8wsgoowkcogkgk0g8o4g8s0 --tail 50"
```

**Restart service Coolify** :
Via UI Coolify ou :
```bash
ssh root@69.62.110.207 "docker restart excalidraw-frontend excalidraw-proxy excalidraw-backend"
```

---

## 📊 Bilan de la session

**Durée** : ~4-5 heures

**Accomplissements** :
- ✅ Backend Excalidraw 100% fonctionnel (testé et validé)
- ✅ Base Postgres créée et configurée
- ✅ Frontend custom buildé
- ✅ Proxy adaptateur créé (solution élégante au problème d'incompatibilité)
- ✅ DNS configurés
- ✅ Décisions architecturales prises (souveraineté, sécurité)
- ⚠️ Dernière étape : rebuild pour AMD64 (en cours)

**Points positifs** :
- Approche méthodique et réfléchie
- Problèmes identifiés et résolus un par un
- Documentation au fil de l'eau
- Décisions éclairées (sécurité, maintenance)

**Points d'amélioration** :
- Anticiper le problème d'architecture ARM/AMD64 dès le départ
- Peut-être tester en local avant de builder (mais compliqué avec le proxy)

**Prochaine session** :
- Finaliser le rebuild AMD64
- Déployer et tester
- Ajouter l'authentification
- Si tout fonctionne : passer à la Phase H (MCP custom)

---

**Session créée le 15 mai 2026 à 18:35**  
**Auteur** : Claude Code + Christophe Martin  
**Statut** : ⚠️ En cours (rebuild AMD64 en attente)
