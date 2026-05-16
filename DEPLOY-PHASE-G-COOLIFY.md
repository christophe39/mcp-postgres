# Déploiement Phase G — Guide complet Coolify

> **Date** : 16 mai 2026  
> **Repo GitHub** : https://github.com/christophe39/excalidraw (privé)  
> **VPS** : Hostinger (69.62.110.207)

---

## 📋 Vue d'ensemble

**Ce qu'on va déployer** :
1. ✅ Tables PostgreSQL (utilisateurs, templates, colonnes tracking)
2. ✅ Service d'authentification ForwardAuth (Node.js)
3. ✅ Configuration Traefik ForwardAuth sur Excalidraw
4. ✅ Backup automatique quotidien PostgreSQL

**Durée estimée** : 2-3 heures

---

## 🔧 Étape 0 : Préparation locale (5 min)

### 0.1. Vérifier que tout est commité

```bash
cd /Volumes/ZIKE/codage/projet_excalidraw_opepartner

# Vérifier le statut Git
git status

# Si des modifications non committées, les commiter
git add -A
git commit -m "Préparation déploiement Phase G"
```

### 0.2. Pusher sur GitHub

```bash
# Ajouter le remote GitHub (si pas déjà fait)
git remote add origin https://github.com/christophe39/excalidraw.git

# Ou si déjà configuré, mettre à jour l'URL
git remote set-url origin https://github.com/christophe39/excalidraw.git

# Pusher la branche main
git push -u origin main
```

### 0.3. Générer un token admin aléatoire

```bash
# Sur Mac, dans Terminal
openssl rand -base64 32
```

**Note ce token** (exemple : `AbC123xYz...`), tu en auras besoin pour les variables d'environnement Coolify.

---

## 🗄️ Étape 1 : Créer les tables PostgreSQL (15 min)

### 1.1. Copier le script SQL sur le VPS

```bash
# Depuis ton Mac
scp infra/sql/03_auth_and_templates.sql root@69.62.110.207:/root/
```

### 1.2. Exécuter le script SQL

```bash
# SSH sur le VPS
ssh root@69.62.110.207

# Exécuter le script
docker exec -i pk4s888o4wkc8ogokg0sg840 \
  psql -U excalidraw_backend -d excalidraw_storage \
  < /root/03_auth_and_templates.sql
```

**Sortie attendue** :
```
CREATE TABLE
CREATE INDEX
CREATE TABLE
CREATE INDEX
ALTER TABLE
CREATE FUNCTION
CREATE TRIGGER
CREATE VIEW
GRANT
```

### 1.3. Vérifier que les tables sont créées

```bash
docker exec pk4s888o4wkc8ogokg0sg840 \
  psql -U excalidraw_backend -d excalidraw_storage \
  -c "\dt"
```

**Tu dois voir** :
- `keyv` (modifiée)
- `utilisateurs` (nouvelle)
- `templates` (nouvelle)

```bash
# Vérifier les colonnes de keyv
docker exec pk4s888o4wkc8ogokg0sg840 \
  psql -U excalidraw_backend -d excalidraw_storage \
  -c "\d keyv"
```

**Tu dois voir les nouvelles colonnes** :
- `created_by` (integer)
- `template_id` (integer)
- `created_at_tracked` (timestamptz)
- `metadata` (jsonb)

✅ **Checkpoint** : Tables créées et visibles dans Postgres.

---

## 🐳 Étape 2 : Déployer le service d'authentification via Coolify (30 min)

### 2.1. Configurer le DNS

1. Ouvre le panel DNS Hostinger
2. Ajoute un enregistrement **A** :
   - **Host** : `exca-auth`
   - **Type** : A
   - **Value** : `69.62.110.207`
   - **TTL** : Automatique
3. Sauvegarder

⏳ **Attendre 2-5 minutes** que le DNS propage.

**Tester** :
```bash
# Depuis ton Mac
dig exca-auth.agnisolution.fr

# Ou
ping exca-auth.agnisolution.fr
```

### 2.2. Créer l'application dans Coolify

1. Ouvre Coolify : https://coolify.agnisolution.fr
2. Clique sur **"+ New"** → **"Resource"**
3. Sélectionne **"Application"**

**Configuration** :

**General** :
- **Name** : `excalidraw-auth`
- **Description** : `Service d'authentification ForwardAuth pour Excalidraw`

**Source** :
- **Type** : Git Repository
- **Repository URL** : `https://github.com/christophe39/excalidraw`
- **Branch** : `main`
- **Credentials** : Ajoute ton token GitHub personnel (si repo privé)
  - Settings → Developer settings → Personal access tokens → Generate new token
  - Scopes : `repo` (Full control of private repositories)

**Build** :
- **Build Pack** : Dockerfile
- **Dockerfile Location** : `/auth-service/Dockerfile`
- **Docker Build Context** : `/auth-service`

**Port** :
- **Port Exposes** : `3000`

### 2.3. Configurer les variables d'environnement

Dans l'onglet **"Environment Variables"**, ajoute :

```bash
PORT=3000
NODE_ENV=production
DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@10.0.1.23:5432/excalidraw_storage
DATABASE_SSL=false
ADMIN_TOKEN=<TON_TOKEN_GENERE_A_L_ETAPE_0.3>
```

**⚠️ Important** : Remplace `<TON_TOKEN_GENERE_A_L_ETAPE_0.3>` par le token généré à l'étape 0.3.

### 2.4. Configurer le domaine

Dans l'onglet **"Domains"** :

1. Clique sur **"+ Add Domain"**
2. Entre : `exca-auth.agnisolution.fr`
3. **HTTPS** : ✅ Activé (Let's Encrypt automatique)
4. Sauvegarder

### 2.5. Configurer les labels Traefik (optionnel, si pas auto-configuré)

Si Coolify ne configure pas automatiquement Traefik, ajoute manuellement dans **"Advanced"** → **"Labels"** :

```yaml
traefik.enable=true
traefik.http.routers.excalidraw-auth.rule=Host(`exca-auth.agnisolution.fr`)
traefik.http.routers.excalidraw-auth.entrypoints=websecure
traefik.http.routers.excalidraw-auth.tls.certresolver=letsencrypt
traefik.http.services.excalidraw-auth.loadbalancer.server.port=3000
```

### 2.6. Déployer

1. Clique sur **"Deploy"** (bouton en haut à droite)
2. Coolify va :
   - Cloner le repo GitHub
   - Build l'image Docker depuis `/auth-service/Dockerfile`
   - Démarrer le container
   - Configurer Traefik automatiquement
   - Générer le certificat SSL Let's Encrypt

⏳ **Attendre 3-5 minutes** (le build Node.js prend du temps).

**Suivre les logs** :
- Onglet **"Logs"** dans Coolify
- Tu devrais voir :
  ```
  ✅ Connexion PostgreSQL OK: 2026-05-16...
  🚀 Service d'authentification démarré sur le port 3000
  ```

### 2.7. Tester le service

**Test 1 : Healthcheck**
```bash
curl https://exca-auth.agnisolution.fr/health
```

**Sortie attendue** :
```json
{
  "status": "ok",
  "timestamp": "2026-05-16T...",
  "service": "excalidraw-auth-service"
}
```

**Test 2 : Endpoint /test (liste des users, doit être vide)**
```bash
curl https://exca-auth.agnisolution.fr/test
```

**Sortie attendue** :
```json
{
  "status": "ok",
  "users_count": 0,
  "users": []
}
```

✅ **Checkpoint** : Service d'authentification déployé et accessible.

---

## 👤 Étape 3 : Créer ton utilisateur initial (5 min)

### 3.1. Préparer les dépendances du script local

```bash
# Depuis ton Mac, dans le dossier projet
cd /Volumes/ZIKE/codage/projet_excalidraw_opepartner/auth-service

# Installer les dépendances (si pas déjà fait)
npm install
```

### 3.2. Configurer le .env local

```bash
# Créer le fichier .env
cat > .env <<EOF
DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@69.62.110.207:5432/excalidraw_storage
DATABASE_SSL=false
PORT=3000
NODE_ENV=production
EOF
```

### 3.3. Créer ton utilisateur

```bash
node create-user.js cmartin@agniconsult.fr Farlac2023 "Christophe Martin"
```

**Sortie attendue** :
```
🔐 Hashing du mot de passe...
📧 Création de l'utilisateur : cmartin@agniconsult.fr
✅ Utilisateur créé avec succès !
ID: 1
Email: cmartin@agniconsult.fr
Nom: Christophe Martin
Créé le: 2026-05-16T...

🔍 Test de vérification du mot de passe...
✅ Vérification OK
```

### 3.4. Vérifier en base

```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c 'SELECT id, email, nom, actif, created_at FROM utilisateurs;'"
```

**Sortie attendue** :
```
 id |         email         |       nom         | actif |         created_at
----+-----------------------+-------------------+-------+----------------------------
  1 | cmartin@agniconsult.fr | Christophe Martin | t     | 2026-05-16 ...
```

### 3.5. Tester l'authentification

```bash
curl -I -u cmartin@agniconsult.fr:Farlac2023 https://exca-auth.agnisolution.fr/auth
```

**Sortie attendue** :
```
HTTP/2 200
x-forwarded-user: 1
x-forwarded-email: cmartin@agniconsult.fr
x-forwarded-name: Christophe Martin
```

✅ **Checkpoint** : Utilisateur créé et authentification fonctionnelle.

---

## 🔐 Étape 4 : Configurer Traefik ForwardAuth sur Excalidraw (15 min)

### 4.1. Identifier l'application Excalidraw dans Coolify

1. Ouvre Coolify
2. Va dans **"Resources"** → cherche l'application `excalidraw-frontend` (ou le nom que tu lui as donné)
3. Note l'UUID de l'application (visible dans l'URL : `/application/<uuid>`)

### 4.2. Ajouter les labels ForwardAuth

**Option A — Via Coolify UI (RECOMMANDÉ)** :

1. Ouvre l'application `excalidraw-frontend`
2. Va dans **"Advanced"** → **"Custom Docker Options"** → **"Labels"**
3. Ajoute les labels suivants :

```yaml
traefik.http.middlewares.excalidraw-auth.forwardauth.address=http://excalidraw-auth:3000/auth
traefik.http.middlewares.excalidraw-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Forwarded-Email,X-Forwarded-Name
traefik.http.routers.excalidraw.middlewares=excalidraw-auth@docker
```

4. **Sauvegarder**
5. **Redeploy** l'application (bouton "Deploy")

**Option B — Via SSH (si Coolify ne permet pas d'éditer les labels)** :

```bash
# SSH sur le VPS
ssh root@69.62.110.207

# Trouver le fichier docker-compose.yml de l'application Excalidraw
find /data/coolify/applications -name "docker-compose.yml" | xargs grep -l "excalidraw"

# Éditer le fichier (remplacer <path> par le chemin trouvé)
nano <path>/docker-compose.yml
```

Ajoute les labels au service `frontend` :

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

Redémarrer :
```bash
docker compose -f <path>/docker-compose.yml up -d
```

### 4.3. Tester l'authentification sur Excalidraw

**Test 1 : Sans authentification (doit retourner 401)**
```bash
curl -I https://excalidraw.agnisolution.fr
```

**Sortie attendue** :
```
HTTP/2 401
www-authenticate: Basic realm="Excalidraw OPEPARTNER"
```

**Test 2 : Avec authentification (doit retourner 200)**
```bash
curl -I -u cmartin@agniconsult.fr:Farlac2023 https://excalidraw.agnisolution.fr
```

**Sortie attendue** :
```
HTTP/2 200
```

### 4.4. Tester dans le navigateur

1. Ouvre https://excalidraw.agnisolution.fr
2. **Une popup BasicAuth doit s'afficher** :
   ```
   Authentification requise
   Excalidraw OPEPARTNER
   
   Nom d'utilisateur : [_______________]
   Mot de passe :      [_______________]
   
   [Annuler]  [Se connecter]
   ```
3. Entre :
   - **Nom d'utilisateur** : `cmartin@agniconsult.fr`
   - **Mot de passe** : `Farlac2023`
4. Clique sur **"Se connecter"**
5. **Accès accordé** → Tu dois voir l'interface Excalidraw

✅ **Checkpoint** : Authentification ForwardAuth fonctionnelle sur Excalidraw.

---

## 💾 Étape 5 : Configurer le backup automatique (10 min)

### 5.1. Copier les scripts sur le VPS

```bash
# Depuis ton Mac
scp infra/scripts/backup-excalidraw.sh root@69.62.110.207:/root/
scp infra/scripts/install-backup-cron.sh root@69.62.110.207:/root/
```

### 5.2. Installer le cron

```bash
# SSH sur le VPS
ssh root@69.62.110.207

# Rendre le script d'installation exécutable
chmod +x /root/install-backup-cron.sh

# Exécuter l'installation
/root/install-backup-cron.sh
```

**Le script va** :
1. Copier le script de backup dans `/root/backup-excalidraw.sh`
2. Faire un premier test de backup
3. Ajouter le cron job (tous les jours à 2h00)
4. Créer le fichier de log `/var/log/backup-excalidraw.log`

**Sortie attendue** :
```
📋 Copie du script de backup vers /root/backup-excalidraw.sh...
✅ Script copié et rendu exécutable
🧪 Test du script de backup...
🚀 Démarrage backup de excalidraw_storage...
✅ Backup réussi : /backup/excalidraw/excalidraw_20260516_143052.sql.gz (124K)
...
✅ Installation terminée
```

### 5.3. Vérifier le cron

```bash
# Lister les cron jobs
crontab -l | grep backup-excalidraw
```

**Sortie attendue** :
```
0 2 * * * /root/backup-excalidraw.sh >> /var/log/backup-excalidraw.log 2>&1
```

### 5.4. Vérifier que le backup a été créé

```bash
ls -lh /backup/excalidraw/
```

**Sortie attendue** :
```
total 124K
-rw-r--r-- 1 root root 124K mai 16 14:30 excalidraw_20260516_143052.sql.gz
-rw-r--r-- 1 root root  145 mai 16 14:30 backup.log
```

### 5.5. Tester une restauration (optionnel)

```bash
# Décompresser le backup
gunzip -c /backup/excalidraw/excalidraw_20260516_143052.sql.gz > /tmp/test_restore.sql

# Vérifier que le SQL est valide
head -20 /tmp/test_restore.sql

# Nettoyer
rm /tmp/test_restore.sql
```

✅ **Checkpoint** : Backup automatique configuré et testé.

---

## 🎯 Étape 6 : Vérifications finales (10 min)

### Checklist complète

- [ ] **Tables PostgreSQL** : `utilisateurs`, `templates`, colonnes dans `keyv`
- [ ] **Service auth** : Déployé et accessible sur `exca-auth.agnisolution.fr`
- [ ] **Utilisateur initial** : `cmartin@agniconsult.fr` créé et actif
- [ ] **ForwardAuth** : Popup BasicAuth sur `excalidraw.agnisolution.fr`
- [ ] **Authentification** : Connexion avec email/password fonctionne
- [ ] **Backup quotidien** : Cron configuré, premier backup créé

### Tests bout-en-bout

**Test 1 : Créer un dessin et vérifier le tracking** :

1. Ouvre https://excalidraw.agnisolution.fr (authentifie-toi)
2. Crée un dessin simple (rectangle + texte)
3. Clique sur "Save"
4. Note l'ID depuis l'URL : `#json=abc123def456`
5. Vérifie en base :

```bash
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c \"SELECT key, created_by, created_at_tracked FROM keyv WHERE key='abc123def456';\""
```

**Note** : Pour l'instant, `created_by` sera `NULL` car le backend actuel ne remplit pas cette colonne. Ce sera fait via le MCP custom (Phase H).

**Test 2 : Vérifier les logs du service auth** :

```bash
# Depuis Coolify
# Onglet "Logs" de l'application excalidraw-auth

# Ou via SSH
ssh root@69.62.110.207
docker logs <container_id_excalidraw_auth> --tail 50
```

**Tu dois voir** :
```
✅ Auth réussie : cmartin@agniconsult.fr (ID: 1)
```

**Test 3 : Vérifier les backups** :

```bash
ssh root@69.62.110.207
ls -lh /backup/excalidraw/
cat /var/log/backup-excalidraw.log
```

---

## 📊 Récapitulatif des URLs et credentials

### URLs déployées

| Service | URL | Description |
|---------|-----|-------------|
| Excalidraw Frontend | https://excalidraw.agnisolution.fr | Interface principale (protégée BasicAuth) |
| Backend API | https://exca-api.agnisolution.fr | API de stockage (interne) |
| Service Auth | https://exca-auth.agnisolution.fr | ForwardAuth + Admin endpoints |

### Credentials

**Utilisateur Excalidraw** :
- Email : `cmartin@agniconsult.fr`
- Password : `Farlac2023`

**Admin Token** (pour endpoint `/admin/create-user`) :
- Token : `<TON_TOKEN_GENERE>`
- Usage : `Authorization: Bearer <TOKEN>`

**PostgreSQL** :
- Host : `69.62.110.207:5432` (externe) ou `10.0.1.23:5432` (interne Docker)
- User : `excalidraw_backend`
- Password : `aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=`
- Database : `excalidraw_storage`

### Backups

- **Dossier** : `/backup/excalidraw/`
- **Fréquence** : Quotidienne (2h00)
- **Rétention** : 7 jours
- **Log** : `/var/log/backup-excalidraw.log`

---

## 🔧 Ajouter un template manuellement (bonus)

Maintenant que tout est en place, si tu veux créer un template :

### 1. Créer le dessin dans Excalidraw

1. Ouvre https://excalidraw.agnisolution.fr
2. Crée ton BMC avec placeholders `{{CLIENT_NAME}}`, `{{PARTNERS}}`, etc.
3. Clique sur "Save"
4. Note l'ID : `abc123def456`

### 2. Via NocoDB (SIMPLE)

1. Ouvre NocoDB → base `excalidraw_storage` → table `keyv`
2. Cherche la ligne où `key = 'abc123def456'`
3. Copie le contenu de la colonne `value`
4. Va dans la table `templates`
5. Nouvelle ligne :
   - `nom` : `BMC`
   - `description` : `Business Model Canvas avec 9 cases`
   - `excalidraw_json` : colle le JSON copié
   - `categorie` : `strategy`
   - `tags` : `{consulting,strategy,business-model}`
   - `created_by` : `1`
6. Sauvegarder

### 3. Via SQL (ALTERNATIF)

```sql
INSERT INTO templates (nom, description, excalidraw_json, categorie, tags, created_by)
SELECT 
  'BMC',
  'Business Model Canvas avec 9 cases',
  value,
  'strategy',
  ARRAY['consulting', 'strategy', 'business-model'],
  1
FROM keyv
WHERE key = 'abc123def456';
```

---

## 🐛 Troubleshooting

### Problème : Service auth retourne 500

```bash
# Vérifier les logs
docker logs <container_id> --tail 50

# Vérifier la connexion Postgres
docker exec <container_id> node -e "const {Pool}=require('pg'); new Pool({connectionString: process.env.DATABASE_URL}).query('SELECT NOW()', console.log)"
```

### Problème : ForwardAuth ne fonctionne pas

```bash
# Vérifier les logs Traefik
docker logs coolify-proxy --tail 100 | grep excalidraw

# Vérifier que le middleware est bien attaché
docker exec coolify-proxy traefik version
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

## 🎉 Prochaines étapes (Phase H)

Une fois cette phase terminée, tu pourras :

1. **Créer tes 3 premiers templates** (BMC, PESTEL, SWOT) manuellement
2. **Développer le MCP custom Excalidraw** (Python FastMCP)
   - Fonctions : `create_from_template`, `create_bmc`, `create_pestel`, `create_swot`
   - Intégrations : NocoDB, AFFiNE, n8n
3. **Tester bout-en-bout** : Prompt Claude → génération BMC → stockage → doc AFFiNE

---

**Auteur** : Claude Code + Christophe Martin  
**Date** : 16 mai 2026  
**Statut** : 📋 **PRÊT POUR DÉPLOIEMENT**
