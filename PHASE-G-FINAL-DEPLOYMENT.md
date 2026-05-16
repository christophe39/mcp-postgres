# Phase G Final - Déploiement Authentification + Backup

> **Date** : 16 mai 2026  
> **Objectif** : Sécuriser Excalidraw avec authentification multi-utilisateurs + backup quotidien

---

## 🎯 Vue d'ensemble

### Composants ajoutés

1. **Table PostgreSQL `utilisateurs`** — Gestion des utilisateurs avec bcrypt
2. **Table PostgreSQL `templates`** — Stockage des templates BMC/PESTEL/SWOT
3. **Service d'authentification** (Node.js + Express) — ForwardAuth pour Traefik
4. **Backup automatique quotidien** — Cron avec rotation 7 jours

### Architecture finale

```
User → Traefik ForwardAuth → Service Auth → Check Postgres utilisateurs
                ↓ (si auth OK)                      ↓
         Excalidraw Frontend              Set X-Forwarded-User header
                ↓                                   ↓
         Excalidraw Backend            Insert keyv avec created_by
                ↓
         Postgres (excalidraw_storage)
              ↓
       Backup quotidien 2h00
```

---

## 📋 Checklist de déploiement

### ✅ Étape 1 : Créer les tables PostgreSQL (15 min)

**1.1. Copier le script SQL sur le VPS**

```bash
# Depuis le Mac
scp infra/sql/03_auth_and_templates.sql root@69.62.110.207:/root/
```

**1.2. Exécuter le script**

```bash
# SSH sur le VPS
ssh root@69.62.110.207

# Exécuter le script
docker exec -i pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage < /root/03_auth_and_templates.sql
```

**1.3. Vérifier que les tables sont créées**

```bash
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "\dt"
```

Vous devez voir :
- `keyv` (modifiée avec colonnes `created_by`, `template_id`)
- `utilisateurs` (nouvelle)
- `templates` (nouvelle)

---

### ✅ Étape 2 : Déployer le service d'authentification (30 min)

**2.1. Préparer le code**

```bash
# Depuis le Mac, dans le dossier auth-service
cd auth-service

# Installer les dépendances (pour le script create-user.js)
npm install
```

**2.2. Build l'image Docker pour AMD64**

```bash
docker build --platform linux/amd64 -t excalidraw-auth:latest .
```

**2.3. Option A — Déploiement via Coolify UI (RECOMMANDÉ)**

1. Ouvrir Coolify : https://coolify.agnisolution.fr
2. **New Resource** → **Docker Image**
3. Configuration :
   - **Name** : `excalidraw-auth`
   - **Source** : `Simple Dockerfile`
   - **Build Pack** : Dockerfile
   - **Repository** : `<URL_DU_REPO_GIT>`
   - **Branch** : `main`
   - **Dockerfile Location** : `/auth-service/Dockerfile`
   - **Build Context** : `/auth-service`

4. **Variables d'environnement** :
   ```
   PORT=3000
   DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@10.0.1.23:5432/excalidraw_storage
   DATABASE_SSL=false
   NODE_ENV=production
   ```

5. **Domaine** : `exca-auth.agnisolution.fr`

6. **Deploy** → Attendre le build et le déploiement

**2.3. Option B — Déploiement manuel via SSH**

```bash
# Sauvegarder l'image Docker
docker save excalidraw-auth:latest | gzip > excalidraw-auth.tar.gz

# Copier sur le VPS
scp excalidraw-auth.tar.gz root@69.62.110.207:/root/

# SSH sur le VPS
ssh root@69.62.110.207

# Charger l'image
gunzip -c /root/excalidraw-auth.tar.gz | docker load

# Créer le fichier .env
cat > /root/excalidraw-auth.env <<EOF
PORT=3000
DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@10.0.1.23:5432/excalidraw_storage
DATABASE_SSL=false
NODE_ENV=production
EOF

# Lancer le container
docker run -d \
  --name excalidraw-auth \
  --network coolify \
  --env-file /root/excalidraw-auth.env \
  --label "traefik.enable=true" \
  --label "traefik.http.routers.excalidraw-auth.rule=Host(\`exca-auth.agnisolution.fr\`)" \
  --label "traefik.http.routers.excalidraw-auth.entrypoints=websecure" \
  --label "traefik.http.routers.excalidraw-auth.tls.certresolver=letsencrypt" \
  --label "traefik.http.services.excalidraw-auth.loadbalancer.server.port=3000" \
  excalidraw-auth:latest
```

**2.4. Configurer le DNS**

Ajouter un enregistrement A dans le panel Hostinger :
- **Host** : `exca-auth`
- **Type** : A
- **Value** : `69.62.110.207`
- **TTL** : Automatique

**2.5. Tester le service auth**

```bash
# Healthcheck (doit retourner 200)
curl https://exca-auth.agnisolution.fr/health

# Endpoint /test (doit retourner la liste vide des users)
curl https://exca-auth.agnisolution.fr/test
```

---

### ✅ Étape 3 : Créer le premier utilisateur (5 min)

**3.1. Créer l'utilisateur Christophe**

```bash
# Depuis le Mac, dans le dossier auth-service
# Configurer le .env pour pointer vers le VPS
cat > .env <<EOF
DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@69.62.110.207:5432/excalidraw_storage
DATABASE_SSL=false
PORT=3000
NODE_ENV=production
EOF

# Créer l'utilisateur
node create-user.js cmartin@agniconsult.fr <MOT_DE_PASSE> "Christophe Martin"
```

**3.2. Vérifier en base**

```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c 'SELECT id, email, nom, actif, created_at FROM utilisateurs;'"
```

**3.3. Tester l'authentification**

```bash
# Doit retourner 200 + headers X-Forwarded-User
curl -I -u cmartin@agniconsult.fr:<MOT_DE_PASSE> https://exca-auth.agnisolution.fr/auth
```

---

### ✅ Étape 4 : Configurer Traefik ForwardAuth (15 min)

**4.1. Identifier le container du frontend Excalidraw**

```bash
ssh root@69.62.110.207
docker ps | grep excalidraw
```

Note le container ID du frontend (celui qui expose le port 80).

**4.2. Option A — Via Coolify UI**

1. Ouvrir le service `excalidraw-frontend` dans Coolify
2. Aller dans **Settings** → **Advanced** → **Labels**
3. Ajouter les labels suivants :

```
traefik.http.middlewares.excalidraw-auth.forwardauth.address=http://excalidraw-auth:3000/auth
traefik.http.middlewares.excalidraw-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Forwarded-Email,X-Forwarded-Name
traefik.http.routers.excalidraw.middlewares=excalidraw-auth@docker
```

4. **Redeploy** le service

**4.2. Option B — Modification manuelle du docker-compose**

```bash
# Éditer le docker-compose du service Excalidraw
nano /data/coolify/applications/<app-uuid>/docker-compose.yml
```

Ajouter les labels au service `frontend` :

```yaml
services:
  frontend:
    # ... config existante ...
    labels:
      # ... labels existants ...
      - "traefik.http.middlewares.excalidraw-auth.forwardauth.address=http://excalidraw-auth:3000/auth"
      - "traefik.http.middlewares.excalidraw-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Forwarded-Email,X-Forwarded-Name"
      - "traefik.http.routers.excalidraw.middlewares=excalidraw-auth@docker"
```

Puis redémarrer :

```bash
docker compose -f /data/coolify/applications/<app-uuid>/docker-compose.yml up -d
```

**4.3. Tester l'authentification sur Excalidraw**

```bash
# Sans auth (doit retourner 401 + challenge BasicAuth)
curl -I https://excalidraw.agnisolution.fr

# Avec auth (doit retourner 200)
curl -I -u cmartin@agniconsult.fr:<MOT_DE_PASSE> https://excalidraw.agnisolution.fr
```

**4.4. Tester dans le navigateur**

1. Ouvrir https://excalidraw.agnisolution.fr
2. Une popup BasicAuth doit s'afficher
3. Entrer : `cmartin@agniconsult.fr` / `<MOT_DE_PASSE>`
4. Accès accordé ✅

---

### ✅ Étape 5 : Configurer le backup automatique (10 min)

**5.1. Copier les scripts sur le VPS**

```bash
# Depuis le Mac
scp infra/scripts/backup-excalidraw.sh root@69.62.110.207:/root/
scp infra/scripts/install-backup-cron.sh root@69.62.110.207:/root/
```

**5.2. Installer le cron**

```bash
# SSH sur le VPS
ssh root@69.62.110.207

# Rendre le script d'installation exécutable
chmod +x /root/install-backup-cron.sh

# Exécuter l'installation
/root/install-backup-cron.sh
```

Le script va :
- Copier le script de backup dans `/root/backup-excalidraw.sh`
- Faire un premier test de backup
- Ajouter le cron job (tous les jours à 2h00)
- Créer le fichier de log `/var/log/backup-excalidraw.log`

**5.3. Vérifier le cron**

```bash
# Lister les cron jobs
crontab -l | grep backup-excalidraw

# Devrait afficher :
# 0 2 * * * /root/backup-excalidraw.sh >> /var/log/backup-excalidraw.log 2>&1
```

**5.4. Tester manuellement le backup**

```bash
/root/backup-excalidraw.sh
```

Vérifier que le backup est créé :

```bash
ls -lh /backup/excalidraw/
```

---

### ✅ Étape 6 : Vérifier le tracking created_by (15 min)

**6.1. Modifier le backend pour récupérer X-Forwarded-User**

⚠️ **Important** : Le backend actuel (`kiliandeca/excalidraw-storage-backend`) ne lit pas le header `X-Forwarded-User` pour remplir `created_by`.

**Solution temporaire** : On trackera `created_by` dans le MCP custom (Phase H).

**Solution permanente** (optionnel) : Fork le backend et ajouter le code pour lire le header.

**6.2. Test de bout-en-bout**

1. Ouvrir https://excalidraw.agnisolution.fr (s'authentifier)
2. Créer un dessin
3. Récupérer l'ID depuis l'URL (ex: `#json=abc123def456`)
4. Vérifier en base :

```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c \"SELECT key, created_by, created_at_tracked FROM keyv ORDER BY created_at_tracked DESC LIMIT 5;\""
```

Pour l'instant, `created_by` sera `NULL` (normal, le backend ne remplit pas cette colonne).

---

## 📊 Vérifications finales

### Checklist de validation

- [ ] Table `utilisateurs` créée avec 1 user (Christophe)
- [ ] Table `templates` créée (vide pour l'instant)
- [ ] Table `keyv` a les colonnes `created_by`, `template_id`, `metadata`
- [ ] Service `excalidraw-auth` déployé et accessible sur `exca-auth.agnisolution.fr`
- [ ] Authentification BasicAuth fonctionne sur `excalidraw.agnisolution.fr`
- [ ] Backup quotidien configuré (cron à 2h00)
- [ ] Premier backup créé dans `/backup/excalidraw/`

### Commandes de vérification rapide

```bash
# SSH sur le VPS
ssh root@69.62.110.207

# 1. Vérifier les tables
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "\dt"

# 2. Vérifier les utilisateurs
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "SELECT id, email, nom, actif FROM utilisateurs;"

# 3. Vérifier le service auth
docker ps | grep excalidraw-auth
docker logs <container_id> --tail 20

# 4. Vérifier le cron
crontab -l | grep backup-excalidraw

# 5. Vérifier les backups
ls -lh /backup/excalidraw/
```

---

## 🎯 Prochaines étapes (Phase H)

Une fois cette phase terminée, on pourra attaquer la **Phase H : MCP custom Excalidraw** :

1. **Créer les templates** BMC, PESTEL, SWOT manuellement dans Excalidraw
2. **Sauvegarder les templates** dans la table `templates`
3. **Développer le MCP custom** (Python FastMCP) avec :
   - `create_from_template(template_id, data)` — Clone un template et remplit les données
   - `create_scene(json, metadata)` — Crée une scène custom avec tracking `created_by`
   - `list_scenes(filter)` — Liste les scènes avec filtres (par user, par template, etc.)
   - `get_scene(id)` — Récupère une scène
4. **Intégration NocoDB** : Insert dans `Schemas_Excalidraw` avec FK vers `Clients`, `Missions`
5. **Intégration AFFiNE** : Création/maj de docs dans le workspace OPEPARTNER

---

## 🐛 Troubleshooting

### Problème : Service auth retourne 500

```bash
# Vérifier les logs
docker logs <auth_container_id> --tail 50

# Vérifier la connexion Postgres
docker exec <auth_container_id> node -e "const {Pool}=require('pg'); new Pool({connectionString: process.env.DATABASE_URL}).query('SELECT NOW()', console.log)"
```

### Problème : ForwardAuth ne fonctionne pas

```bash
# Vérifier les logs Traefik
docker logs coolify-proxy --tail 100 | grep excalidraw

# Vérifier que le middleware est bien attaché au router
docker exec coolify-proxy cat /etc/traefik/dynamic/excalidraw.yml
```

### Problème : Backup échoue

```bash
# Tester manuellement
/root/backup-excalidraw.sh

# Vérifier les permissions
ls -ld /backup/excalidraw/

# Vérifier que le container Postgres est accessible
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "SELECT 1"
```

---

**Auteur** : Claude Code + Christophe Martin  
**Date** : 16 mai 2026  
**Statut** : 📋 **PRÊT POUR DÉPLOIEMENT**
