# Service d'authentification Excalidraw

Service ForwardAuth pour Traefik qui authentifie les utilisateurs contre PostgreSQL.

## 🎯 Fonctionnement

1. Traefik intercepte toutes les requêtes vers `excalidraw.agnisolution.fr`
2. Traefik appelle le endpoint `/auth` de ce service
3. Le service vérifie les credentials BasicAuth contre la table `utilisateurs`
4. Si OK : retourne `200` + headers `X-Forwarded-User`, `X-Forwarded-Email`
5. Si KO : retourne `401` + challenge BasicAuth

## 📦 Installation locale (dev)

```bash
# Installer les dépendances
npm install

# Copier et configurer .env
cp .env.example .env
nano .env

# Démarrer en mode dev
npm run dev
```

## 🐳 Build Docker

```bash
# Build pour AMD64 (VPS Hostinger)
docker build --platform linux/amd64 -t excalidraw-auth:latest .

# Test local
docker run -p 3000:3000 --env-file .env excalidraw-auth:latest
```

## 👤 Créer un utilisateur

```bash
# Depuis le dossier auth-service avec .env configuré
node create-user.js <email> <password> [nom]

# Exemple
node create-user.js cmartin@agniconsult.fr MonP@ssw0rd "Christophe Martin"
```

Ou directement en SQL :

```sql
INSERT INTO utilisateurs (email, password_hash, nom, actif)
VALUES (
  'cmartin@agniconsult.fr',
  '$2b$10$...',  -- hash bcrypt généré avec le script
  'Christophe Martin',
  true
);
```

## 🚀 Déploiement sur Coolify

### 1. Préparer l'image Docker

```bash
# Sur le Mac (build cross-platform)
cd auth-service
docker build --platform linux/amd64 -t excalidraw-auth:latest .

# Tag pour le registry (si nécessaire)
docker tag excalidraw-auth:latest registry.example.com/excalidraw-auth:latest
docker push registry.example.com/excalidraw-auth:latest
```

### 2. Créer le service dans Coolify

**Option A : Via Dockerfile depuis Git** (RECOMMANDÉ)

1. Dans Coolify : **New Resource** → **Docker Image**
2. Configure:
   - Name: `excalidraw-auth`
   - Source: Git Repository
   - Repository: `<url_du_repo>`
   - Branch: `main`
   - Dockerfile Location: `/auth-service/Dockerfile`
   - Build Context: `/auth-service`

3. Variables d'environnement:
   ```
   PORT=3000
   DATABASE_URL=postgresql://excalidraw_backend:aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=@10.0.1.23:5432/excalidraw_storage
   DATABASE_SSL=false
   NODE_ENV=production
   ```

4. Ajouter le domaine: `exca-auth.agnisolution.fr`

5. Ajouter les labels Traefik (dans Settings → Advanced):
   ```yaml
   traefik.enable=true
   traefik.http.routers.excalidraw-auth.rule=Host(`exca-auth.agnisolution.fr`)
   traefik.http.routers.excalidraw-auth.entrypoints=websecure
   traefik.http.routers.excalidraw-auth.tls.certresolver=letsencrypt
   traefik.http.services.excalidraw-auth.loadbalancer.server.port=3000
   ```

**Option B : Via image pré-buildée**

1. Build local + push vers Docker Hub ou registry privé
2. Dans Coolify : **New Resource** → **Docker Image**
3. Image name: `<registry>/excalidraw-auth:latest`
4. Mêmes variables d'env et labels que Option A

### 3. Configurer Traefik ForwardAuth

Modifier le service `excalidraw-frontend` dans Coolify (ou docker-compose) :

```yaml
labels:
  # Middleware ForwardAuth
  - "traefik.http.middlewares.excalidraw-auth.forwardauth.address=http://excalidraw-auth:3000/auth"
  - "traefik.http.middlewares.excalidraw-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Forwarded-Email,X-Forwarded-Name"
  
  # Appliquer le middleware au router
  - "traefik.http.routers.excalidraw.middlewares=excalidraw-auth@docker"
```

### 4. Tester l'authentification

```bash
# Sans auth (doit retourner 401)
curl -I https://excalidraw.agnisolution.fr

# Avec auth (doit retourner 200)
curl -I -u cmartin@agniconsult.fr:MonP@ssw0rd https://excalidraw.agnisolution.fr

# Tester directement le service auth
curl -I -u cmartin@agniconsult.fr:MonP@ssw0rd https://exca-auth.agnisolution.fr/auth
```

## 🔍 Endpoints disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/auth` | GET | Endpoint ForwardAuth (appelé par Traefik) |
| `/health` | GET | Healthcheck (retourne `{"status":"ok"}`) |
| `/test` | GET | Liste les utilisateurs (à retirer en prod) |

## 📊 Logs et debug

```bash
# Logs du service auth
ssh root@69.62.110.207 "docker logs <container_id> --tail 50 -f"

# Vérifier les utilisateurs en base
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c 'SELECT id, email, nom, actif, last_login FROM utilisateurs;'"

# Tester une connexion directe
curl -v -u email:password http://exca-auth.agnisolution.fr/auth
```

## 🔐 Sécurité

- Les mots de passe sont hashés avec **bcrypt** (10 rounds minimum)
- Le service n'expose que 3 endpoints (auth, health, test)
- Les credentials transitent en HTTPS (Traefik + Let's Encrypt)
- La connexion Postgres est interne au réseau Docker (pas exposée)

## 🐛 Troubleshooting

### Problème : 401 même avec bon mot de passe

```bash
# Vérifier que l'utilisateur existe et est actif
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "SELECT * FROM utilisateurs WHERE email='cmartin@agniconsult.fr';"

# Vérifier les logs du service auth
docker logs <auth_container_id> --tail 20
```

### Problème : Traefik ne transmet pas les headers

Vérifier que le middleware ForwardAuth a bien `authResponseHeaders` configuré :

```yaml
traefik.http.middlewares.excalidraw-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Forwarded-Email,X-Forwarded-Name
```

### Problème : Service auth ne se connecte pas à Postgres

Vérifier :
1. `DATABASE_URL` correcte (IP interne Docker, port 5432)
2. Permissions de l'utilisateur `excalidraw_backend`
3. Network Docker commun entre auth et postgres

## 📝 Notes

- Le endpoint `/test` doit être retiré en production (expose la liste des users)
- `last_login` est mis à jour à chaque authentification réussie
- Les utilisateurs inactifs (`actif=false`) ne peuvent pas se connecter
