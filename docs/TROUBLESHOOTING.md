# Guide de Dépannage Excalidraw OPEPARTNER

> Documentation exhaustive des problèmes rencontrés, diagnostics et solutions

**Dernière mise à jour :** 16 mai 2026  
**Auteur :** Christophe Martin + Claude Sonnet 4.5

---

## 📋 Table des matières

1. [Architecture du système](#architecture-du-système)
2. [Diagnostic rapide (checklist)](#diagnostic-rapide-checklist)
3. [Erreurs courantes et solutions](#erreurs-courantes-et-solutions)
4. [Commandes de diagnostic](#commandes-de-diagnostic)
5. [Workflow de résolution](#workflow-de-résolution)
6. [Bonnes pratiques](#bonnes-pratiques)

---

## 🏗️ Architecture du système

### Stack technique

```
┌─────────────────────────────────────────────────────┐
│ Frontend (React/Excalidraw)                         │
│ https://excalidraw.agnisolution.fr                  │
│ Container: frontend-o8wsgoowkcogkgk0g8o4g8s0       │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ Traefik (Reverse Proxy)                             │
│ Container: coolify-proxy                            │
│ Dashboard: http://localhost:8080 (sur VPS)          │
└─────────────────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
┌─────────────────────┐   ┌─────────────────────────┐
│ Proxy Nginx         │   │ (NE PAS router ici!)    │
│ exca-api.agni...fr  │   │                         │
│ Container: proxy-*  │   │                         │
└─────────────────────┘   └─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────┐
│ Backend (Node.js/NestJS)                            │
│ PAS de domaine public (interne seulement)          │
│ Container: backend-o8wsgoowkcogkgk0g8o4g8s0        │
└─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────┐
│ PostgreSQL                                           │
│ IP: 10.0.1.23:5432                                  │
│ Container: pk4s888o4wkc8ogokg0sg840                │
│ Base: excalidraw_storage                            │
│ User: excalidraw_backend                            │
└─────────────────────────────────────────────────────┘
```

### Points critiques

| Composant | Rôle | ⚠️ Point d'attention |
|-----------|------|---------------------|
| **Frontend** | Interface utilisateur | Variables VITE compilées au build |
| **Traefik** | Routing HTTPS | Routes multiples peuvent entrer en conflit |
| **Proxy Nginx** | Adaptateur URL | Met en cache la résolution DNS de "backend" |
| **Backend** | API + Stockage | **NE DOIT PAS** avoir de domaine public configuré |
| **PostgreSQL** | Base de données | Table `keyv` pour les schémas (pas `scenes`) |

---

## 🚨 Diagnostic rapide (checklist)

### Symptôme : "Impossible de créer un lien de partage"

**Suivre cette checklist dans l'ordre :**

```bash
# 1. Vérifier que les containers tournent
ssh root@69.62.110.207
docker ps --filter 'name=o8wsgoowkcogkgk0g8o4g8s0' --format 'table {{.Names}}\t{{.Status}}'

# 2. Tester l'API directement
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ \
  -H "Content-Type: application/json" \
  -d '{"test":true}' \
  -w "\nHTTP: %{http_code}\n"

# Si HTTP 404 "Cannot POST /api/v2/post/" → PROBLÈME DE ROUTING
# Si HTTP 502 Bad Gateway → PROBLÈME DE CONNEXION PROXY ↔ BACKEND
# Si HTTP 201 + {"id":"..."} → API OK, problème ailleurs

# 3. Vérifier les routes Traefik
curl -s http://localhost:8080/api/http/routers | \
  jq -r '.[] | select(.rule | contains("exca-api")) | {name:.name, service:.service}'

# ⚠️ SI tu vois une route backend-* pointant vers exca-api → ERREUR CRITIQUE
```

### Symptôme : Coolify affiche "Degraded (unhealthy)"

**Ce n'est PAS grave si les services fonctionnent.**

- C'est juste un healthcheck qui échoue
- Le service fonctionne normalement
- Solution : ignorer, ou supprimer le healthcheck

---

## 🔥 Erreurs courantes et solutions

### Erreur #1 : HTTP 404 "Cannot POST /api/v2/post/"

**Cause :** Traefik route directement vers le **backend** au lieu du **proxy**.

**Symptôme :**
```bash
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
# → {"statusCode":404,"message":"Cannot POST /api/v2/post/","error":"Not Found"}
```

**Diagnostic :**
```bash
# Vérifier les routes Traefik
curl -s http://localhost:8080/api/http/routers | \
  jq -r '.[] | select(.rule | contains("exca-api")) | {name:.name, service:.service}'

# ❌ ERREUR si tu vois :
# {
#   "name": "https-0-o8wsgoowkcogkgk0g8o4g8s0-backend@docker",
#   "service": "backend-o8wsgoowkcogkgk0g8o4g8s0"
# }
```

**Cause racine :**
Le service **Backend** a un domaine configuré dans Coolify → Coolify génère automatiquement des labels Traefik → Traefik route direct au backend.

**Solution A (Coolify UI) - RECOMMANDÉE :**

1. Aller dans Coolify → Service Excalidraw → Settings du **Backend**
2. Champ **"Domains"** : VIDER complètement (supprimer `https://exca-api.agnisolution.fr`)
3. Cliquer sur **"Save"**
4. Cliquer sur **"Deploy"**

**Solution B (SSH) - Temporaire :**

```bash
ssh root@69.62.110.207
cd /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0

# Supprimer les labels Traefik du backend
sed -i '/traefik.http.routers.*backend.*exca-api/d' docker-compose.yml
sed -i '/traefik.http.routers.https-0-o8wsgoowkcogkgk0g8o4g8s0-backend/d' docker-compose.yml
sed -i '/traefik.http.routers.http-0-o8wsgoowkcogkgk0g8o4g8s0-backend/d' docker-compose.yml

# Relancer le backend
docker compose up -d backend

# Redémarrer le proxy (résolution DNS)
docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0
```

⚠️ **IMPORTANT :** La solution B est temporaire. Le problème reviendra au prochain deploy Coolify si le domaine n'est pas supprimé dans l'UI.

---

### Erreur #2 : HTTP 502 Bad Gateway

**Cause :** Le proxy ne peut pas joindre le backend (IP changée, cache DNS).

**Symptôme :**
```bash
curl https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
# → Bad Gateway (502)
```

**Diagnostic :**
```bash
# Voir les logs du proxy
docker logs proxy-o8wsgoowkcogkgk0g8o4g8s0 --tail 20

# ❌ ERREUR si tu vois :
# upstream prematurely closed connection
# connect() failed (111: Connection refused)
# no live upstreams while connecting to upstream
```

**Cause racine :**
Nginx (dans le proxy) a mis en **cache la résolution DNS** de "backend". Quand le backend redémarre, il obtient une nouvelle IP, mais le proxy garde l'ancienne IP en cache.

**Solution :**

```bash
# Redémarrer le proxy pour forcer la re-résolution DNS
ssh root@69.62.110.207
docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0

# Attendre 3 secondes
sleep 3

# Retester
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
# → HTTP 201 {"id":"..."}
```

**Solution permanente (TODO) :**

Modifier `nginx.conf` pour utiliser une résolution DNS dynamique :

```nginx
# Au lieu de :
proxy_pass http://backend:8080;

# Utiliser :
resolver 127.0.0.11 valid=10s;
set $backend_upstream backend:8080;
proxy_pass http://$backend_upstream;
```

---

### Erreur #3 : Coolify affiche "Degraded (unhealthy)"

**Cause :** Healthcheck Docker échoue (endpoint `/health` n'existe plus).

**Symptôme :**
- Coolify affiche un badge orange "Degraded (unhealthy)"
- Mais le service **fonctionne normalement** quand même

**Diagnostic :**
```bash
docker ps --filter 'name=proxy' --format '{{.Names}}\t{{.Status}}'
# → proxy-o8wsgoowkcogkgk0g8o4g8s0   Up 10 minutes (unhealthy)
```

**Solution : IGNORER**

Ce n'est **PAS un problème**. Le healthcheck a été volontairement supprimé car il était inutile et causait une incompatibilité avec docker-compose v1.

Le statut "unknown" est normal et attendu.

---

### Erreur #4 : Incompatibilité docker-compose v1 vs v2

**Cause :** Docker Engine 28.x avec docker-compose v1.29.2 (incompatible).

**Symptôme :**
```bash
docker-compose up -d
# → ERROR: 'ContainerConfig'
# → KeyError: 'ContainerConfig'
```

**Solution :**

**Toujours utiliser `docker compose` (v2, avec espace) au lieu de `docker-compose` (v1, avec tiret) :**

```bash
# ❌ NE PAS utiliser :
docker-compose up -d

# ✅ Utiliser :
docker compose up -d
```

**Vérifier quelle version est installée :**

```bash
docker-compose --version  # v1.29.2 (ancien)
docker compose version    # v2.35.1 (nouveau)
```

---

### Erreur #5 : Les schémas ne se sauvegardent pas dans PostgreSQL

**Cause :** Mauvaise table ou mauvaise base de données.

**Diagnostic :**
```bash
# Vérifier que les données sont dans la table keyv
ssh root@69.62.110.207
docker exec pk4s888o4wkc8ogokg0sg840 \
  psql -U excalidraw_backend -d excalidraw_storage \
  -c "SELECT COUNT(*) FROM keyv WHERE key LIKE 'SCENES:%';"

# Si 0 rows → Problème de connexion backend ↔ PostgreSQL
# Si > 0 rows → Les données sont bien stockées
```

**Important :** Les schémas sont stockés dans la table `keyv`, PAS dans `excalidraw_scenes`.

---

## 🛠️ Commandes de diagnostic

### Vérifier l'état des services

```bash
# Connexion SSH au VPS
ssh root@69.62.110.207

# Lister les containers Excalidraw
docker ps --filter 'name=o8wsgoowkcogkgk0g8o4g8s0' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Voir les logs en temps réel
docker logs -f proxy-o8wsgoowkcogkgk0g8o4g8s0
docker logs -f backend-o8wsgoowkcogkgk0g8o4g8s0
docker logs -f frontend-o8wsgoowkcogkgk0g8o4g8s0

# Vérifier les dernières erreurs
docker logs proxy-o8wsgoowkcogkgk0g8o4g8s0 2>&1 | grep -i error | tail -10
```

### Vérifier le routing Traefik

```bash
# Lister toutes les routes pour exca-api
curl -s http://localhost:8080/api/http/routers | \
  jq -r '.[] | select(.rule | contains("exca-api")) | {name:.name, rule:.rule, service:.service, middlewares:.middlewares}'

# Lister tous les services Traefik
curl -s http://localhost:8080/api/http/services | \
  jq -r '.[] | select(.name | contains("proxy") or contains("backend")) | {name:.name, serverStatus:.serverStatus}'

# ✅ Résultat attendu :
# Toutes les routes exca-api doivent pointer vers le service "excalidraw-proxy"
# AUCUNE route ne doit pointer vers "backend-o8wsgoowkcogkgk0g8o4g8s0"
```

### Tester l'API

```bash
# Test POST (création)
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ \
  -H "Content-Type: application/json" \
  -d '{"elements":[],"appState":{}}' \
  -w "\nHTTP: %{http_code}\n"

# ✅ Résultat attendu : HTTP 201 + {"id":"1234567890"}

# Test GET (lecture) - remplacer {ID} par un vrai ID
curl -s https://exca-api.agnisolution.fr/api/v2/{ID} -w "\nHTTP: %{http_code}\n" | tail -2

# ✅ Résultat attendu : HTTP 200 + données binaires compressées
```

### Vérifier PostgreSQL

```bash
# Connexion à la base
ssh root@69.62.110.207
docker exec -it pk4s888o4wkc8ogokg0sg840 \
  psql -U excalidraw_backend -d excalidraw_storage

# Lister les tables
\dt

# Compter les schémas stockés
SELECT COUNT(*) FROM keyv WHERE key LIKE 'SCENES:%';

# Voir les derniers schémas créés
SELECT key, LENGTH(value) as size_bytes, created_at 
FROM keyv 
WHERE key LIKE 'SCENES:%' 
ORDER BY created_at DESC 
LIMIT 10;

# Quitter
\q
```

### Vérifier les IPs des containers

```bash
# IP du backend
docker inspect backend-o8wsgoowkcogkgk0g8o4g8s0 \
  --format='{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'

# IP du proxy
docker inspect proxy-o8wsgoowkcogkgk0g8o4g8s0 \
  --format='{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'

# Tester la résolution DNS depuis le proxy
docker exec proxy-o8wsgoowkcogkgk0g8o4g8s0 ping -c 1 backend
```

---

## 🔄 Workflow de résolution

### Procédure standard de troubleshooting

```
1. SYMPTÔME
   ↓
2. VÉRIFIER LES CONTAINERS
   docker ps --filter 'name=o8wsgoowkcogkgk0g8o4g8s0'
   ↓
3. TESTER L'API
   curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
   ↓
4. SI HTTP 404 → PROBLÈME ROUTING
   → Aller à "Erreur #1"
   ↓
5. SI HTTP 502 → PROBLÈME PROXY ↔ BACKEND
   → Aller à "Erreur #2"
   ↓
6. SI HTTP 201 → API OK
   → Problème ailleurs (frontend, CORS, auth)
   ↓
7. VÉRIFIER LES LOGS
   docker logs proxy-* --tail 50
   docker logs backend-* --tail 50
   ↓
8. APPLIQUER LA SOLUTION
   ↓
9. RETESTER
   curl + test manuel Excalidraw
   ↓
10. DOCUMENTER
    Ajouter dans ce fichier si nouveau problème
```

---

## ✅ Bonnes pratiques

### Avant de modifier quoi que ce soit dans Coolify

1. **Backup du docker-compose.yml**
   ```bash
   ssh root@69.62.110.207
   cp /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0/docker-compose.yml \
      /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0/docker-compose.yml.backup-$(date +%Y%m%d-%H%M%S)
   ```

2. **Vérifier que le Backend n'a PAS de domaine configuré**
   - Aller dans Coolify → Backend → Settings
   - Champ "Domains" doit être **VIDE**
   - Seul le Proxy doit avoir `exca-api.agnisolution.fr`

3. **Après un deploy, toujours vérifier les routes Traefik**
   ```bash
   curl -s http://localhost:8080/api/http/routers | \
     jq -r '.[] | select(.rule | contains("exca-api")) | .service' | sort -u
   
   # ✅ Résultat attendu : seulement "excalidraw-proxy"
   # ❌ Si tu vois "backend-..." → CORRIGER IMMÉDIATEMENT
   ```

4. **Redémarrer le proxy après tout redémarrage du backend**
   ```bash
   docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0
   ```

### Configuration Coolify recommandée

| Service | Domaine | Expose publicly | Notes |
|---------|---------|-----------------|-------|
| **Frontend** | `excalidraw.agnisolution.fr` | ✅ Oui | Interface utilisateur |
| **Proxy** | `exca-api.agnisolution.fr` | ✅ Oui | Point d'entrée API |
| **Backend** | *(vide)* | ❌ NON | Interne seulement |

### Variables d'environnement critiques

**Backend :**
```bash
STORAGE_URI=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@10.0.1.23:5432/excalidraw_storage
PORT=8080
NODE_ENV=production
CORS_ALLOWED_ORIGINS=https://excalidraw.agnisolution.fr,https://mcp-excalidraw.agnisolution.fr
ID_LENGTH=12
```

**Frontend :**
```bash
VITE_APP_BACKEND_V2_GET_URL=https://exca-api.agnisolution.fr/api/v2/
VITE_APP_BACKEND_V2_POST_URL=https://exca-api.agnisolution.fr/api/v2/post/
VITE_APP_DISABLE_TRACKING=true
```

⚠️ Les variables VITE sont **compilées au build** du frontend. Si tu les changes, il faut rebuilder l'image frontend.

---

## 📊 Checklist de santé du système

### Tous les jours / Après chaque modification

- [ ] Les 3 containers tournent (`docker ps`)
- [ ] POST API fonctionne (HTTP 201)
- [ ] GET API fonctionne (HTTP 200)
- [ ] Coolify affiche "Running" (pas "Exited")
- [ ] Pas de routes backend vers exca-api dans Traefik
- [ ] Logs proxy/backend sans erreurs 502/404

### Après un deploy Coolify

- [ ] Vérifier que le champ "Domains" du Backend est vide
- [ ] Vérifier les routes Traefik (pas de backend-*)
- [ ] Redémarrer le proxy : `docker restart proxy-*`
- [ ] Tester POST + GET
- [ ] Tester dans Excalidraw (export + import)

---

## 🆘 En cas de panique totale

**Si tout est cassé et que rien ne fonctionne :**

```bash
# 1. Connexion SSH
ssh root@69.62.110.207
cd /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0

# 2. Tout redémarrer
docker compose restart

# 3. Attendre 10 secondes
sleep 10

# 4. Vérifier l'état
docker ps --filter 'name=o8wsgoowkcogkgk0g8o4g8s0'

# 5. Tester l'API
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'

# 6. Si toujours cassé, vérifier les routes Traefik
curl -s http://localhost:8080/api/http/routers | \
  jq -r '.[] | select(.rule | contains("exca-api")) | {name:.name, service:.service}'

# 7. Si une route backend existe, la supprimer
sed -i '/traefik.http.routers.*backend.*exca-api/d' docker-compose.yml
sed -i '/traefik.http.routers.https-0-o8wsgoowkcogkgk0g8o4g8s0-backend/d' docker-compose.yml
sed -i '/traefik.http.routers.http-0-o8wsgoowkcogkgk0g8o4g8s0-backend/d' docker-compose.yml
docker compose up -d backend
docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0

# 8. Retester
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
```

---

## 📝 Historique des incidents

### 16 mai 2026 - Problème de routing Traefik (2ème occurrence)

**Symptôme :** "Impossible de créer un lien de partage" après mise en place d'un système d'auth.

**Cause :** Coolify a régénéré le docker-compose.yml et rajouté les labels Traefik sur le backend.

**Solution appliquée :** Suppression du domaine du Backend dans Coolify UI.

**Leçon apprise :** Ne JAMAIS configurer de domaine public sur le service Backend dans Coolify. Toujours laisser ce champ vide.

### 16 mai 2026 - Incompatibilité docker-compose v1 / Docker Engine 28.x

**Symptôme :** Coolify affiche "Degraded (unhealthy)", erreur `KeyError: 'ContainerConfig'`.

**Cause :** docker-compose v1.29.2 incompatible avec Docker Engine 28.5.1.

**Solution appliquée :** 
- Utilisation de `docker compose` v2 au lieu de v1
- Suppression du healthcheck du Dockerfile du proxy

**Leçon apprise :** Toujours utiliser `docker compose` (v2) dans les commandes SSH.

---

## 🔗 Ressources utiles

- **VPS SSH :** `ssh root@69.62.110.207`
- **Coolify :** https://coolify.agnisolution.fr
- **Traefik Dashboard :** http://localhost:8080 (sur VPS)
- **Frontend :** https://excalidraw.agnisolution.fr
- **API :** https://exca-api.agnisolution.fr
- **Repo GitHub :** https://github.com/christophe39/excalidraw

---

## 📞 Contacts

- **Admin :** Christophe Martin (cmartin@agniconsult.fr)
- **Support Coolify :** https://github.com/coollabsio/coolify/issues

---

**Ce document est vivant. Ajoute chaque nouveau problème rencontré pour construire une base de connaissances complète.**
