# 🛡️ Guide de déploiement sécurisé
# Service d'authentification v2.0 avec page de login

## ⚠️ IMPORTANT : Rollback instantané disponible

À CHAQUE étape, si un problème survient :

```bash
cd /Volumes/ZIKE/codage/agni-mcp-stack/auth-service
./ROLLBACK-URGENCE.sh
```

**Temps de rollback : 2-3 minutes maximum**

---

## 📋 Checklist pré-déploiement

- [ ] Excalidraw fonctionne actuellement (vérifier : https://excalidraw.agnisolution.fr)
- [ ] Service auth actuel fonctionne (vérifier : https://exca-auth.agnisolution.fr/health)
- [ ] Branche de sécurité créée (`feature/auth-login-page-with-rate-limiting`)
- [ ] Backup du server.js original créé

---

## 🚀 Étape 1 : Test en local (ZÉRO RISQUE)

### 1.1 Préparer les fichiers

```bash
cd /Volumes/ZIKE/codage/agni-mcp-stack/auth-service

# Remplacer les fichiers
cp package-new.json package.json
cp server-new.js server.js
cp .env-new.example .env.example

# Mettre à jour le .env avec SESSION_SECRET
echo "SESSION_SECRET=$(openssl rand -base64 32)" >> .env
```

### 1.2 Installer les dépendances

```bash
npm install
```

**Vérification** :
- `express-session`, `connect-pg-simple`, `cookie-parser` doivent apparaître dans `node_modules/`

### 1.3 Lancer en local

```bash
# Terminal 1 : Lancer le serveur
npm run dev

# Terminal 2 : Tester
chmod +x test-auth.sh
./test-auth.sh http://localhost:3000 "VOTRE_MOT_DE_PASSE"
```

**✅ Critère de succès** : 
```
✅ TOUS LES TESTS RÉUSSIS
🚀 Prêt pour le déploiement !
```

**❌ Si ça ne marche pas** :
```bash
# Annuler les changements
git checkout server.js package.json
```

---

## 📦 Étape 2 : Commit et push (RÉVERSIBLE)

```bash
cd /Volumes/ZIKE/codage/agni-mcp-stack

# Vérifier les changements
git status
git diff auth-service/

# Commit
git add auth-service/
git commit -m "feat(auth): Ajout page de login HTML + session + rate limiting

- Page de login minimaliste avec autocomplete
- Gestion de session avec PostgreSQL
- Rate limiting : 3 tentatives = 5 min blocage
- Session définitive (1 an)
- Rollback possible vers branche main"

# Push sur la branche feature
git push origin feature/auth-login-page-with-rate-limiting
```

**✅ Critère de succès** : Push réussi sur GitHub

**❌ Si problème** : Pas de risque, les changements sont locaux

---

## 🔧 Étape 3 : Déploiement sur Coolify (SANS IMPACT EXCALIDRAW)

### 3.1 Mettre à jour la branche de déploiement dans Coolify

1. Aller sur https://coolify.agnisolution.fr
2. Trouver l'application `excalidraw-auth`
3. Aller dans **Settings** → **Source**
4. Changer la branche de `main` vers `feature/auth-login-page-with-rate-limiting`
5. Ajouter la variable d'environnement `SESSION_SECRET` :
   ```
   SESSION_SECRET=<générer avec: openssl rand -base64 32>
   ```

### 3.2 Rebuild

6. Cliquer sur **Force Rebuild**
7. Suivre les logs en temps réel

**✅ Critères de succès** :
- Build réussi
- Container démarré (healthy)
- Logs montrent : `✅ Connexion PostgreSQL OK`
- Logs montrent : `✅ Table session prête`

**❌ Si le build échoue** :
```bash
# Revenir immédiatement à main
1. Coolify → Settings → Source → Branch: main
2. Force Rebuild
# → Retour à BasicAuth en 2 minutes
```

### 3.3 Vérification post-déploiement

```bash
# Healthcheck
curl https://exca-auth.agnisolution.fr/health

# Doit retourner :
{
  "status": "ok",
  "version": "2.0.0-with-login-page"
}

# Page de login
curl -I https://exca-auth.agnisolution.fr/login
# Doit retourner : HTTP/2 200
```

**⚠️ À ce stade** :
- ✅ Le nouveau service d'auth fonctionne
- ✅ **Excalidraw est TOUJOURS accessible** (pas de ForwardAuth activé)
- ✅ Aucun impact utilisateur

---

## 🧪 Étape 4 : Test de connexion manuel

Ouvrir https://exca-auth.agnisolution.fr/login dans un navigateur :

1. Vérifier que la page s'affiche correctement
2. Tester login avec **mauvais** mot de passe → message d'erreur
3. Tester login avec **bons** identifiants → redirection
4. Tester 3 mauvais logins → message "Trop de tentatives"
5. **Important** : Tester autocomplete (gestionnaire de mots de passe)
   - Safari : doit proposer d'enregistrer
   - Chrome : doit proposer d'enregistrer

**✅ Critères de succès** :
- Page moderne s'affiche
- Erreurs gérées proprement
- Rate limiting fonctionne
- **Gestionnaire de mots de passe détecte le formulaire** ⭐

**❌ Si problème** :
```bash
./ROLLBACK-URGENCE.sh
```

---

## 🔐 Étape 5 : Activation ForwardAuth sur Excalidraw (RÉVERSIBLE)

**⚠️ CETTE ÉTAPE ACTIVE LA PROTECTION**

### 5.1 Backup de la configuration Excalidraw

```bash
ssh root@69.62.110.207

# Sauvegarder la config actuelle
docker exec coolify-db psql -U coolify -d coolify -c \
  "SELECT name, fqdn, custom_labels FROM applications WHERE name LIKE '%excalidraw%';" \
  > /root/excalidraw-config-backup-$(date +%Y%m%d).sql
```

### 5.2 Ajouter le middleware ForwardAuth

Dans Coolify, application `excalidraw.agnisolution V2` :

1. Aller dans **Settings** → **Advanced** → **Custom Labels**
2. Ajouter :

```yaml
traefik.http.middlewares.excalidraw-auth.forwardauth.address=http://exca-auth.agnisolution.fr/auth
traefik.http.middlewares.excalidraw-auth.forwardauth.authResponseHeaders=X-Forwarded-User,X-Forwarded-Email,X-Forwarded-Name
traefik.http.routers.excalidraw-main.middlewares=excalidraw-auth@docker
```

3. **Redémarrer** l'application (pas rebuild, juste restart)

### 5.3 Test immédiat

```bash
# En navigation privée (pas de session)
curl -I https://excalidraw.agnisolution.fr

# Doit retourner : HTTP/2 302 (redirect vers login)
# Location: https://exca-auth.agnisolution.fr/login?redirect=...
```

**✅ Critères de succès** :
- Sans session → redirect vers /login
- Après login → accès à Excalidraw
- Session persistante (pas de re-login)

**❌ Si problème (ex: boucle infinie, erreur 500)** :

### 🚨 ROLLBACK FORWARDAUTH IMMÉDIAT

```bash
# Depuis Coolify, application Excalidraw
# Settings → Advanced → Custom Labels
# → SUPPRIMER les 3 lignes ajoutées
# → Restart

# OU en SSH :
ssh root@69.62.110.207
docker exec coolify-db psql -U coolify -d coolify -c \
  "UPDATE applications SET custom_labels = '{}' \
   WHERE name = 'excalidraw.agnisolution V2';"
docker restart coolify-proxy

# → Excalidraw redevient accessible IMMÉDIATEMENT
```

**Temps de rollback : 30 secondes**

---

## ✅ Étape 6 : Validation finale

### 6.1 Checklist utilisateur

- [ ] Ouvrir https://excalidraw.agnisolution.fr en navigation privée
- [ ] Redirection vers page de login ✅
- [ ] Login avec identifiants corrects ✅
- [ ] Accès à Excalidraw ✅
- [ ] Fermer le navigateur et rouvrir → toujours connecté ✅
- [ ] Gestionnaire de mots de passe fonctionne ✅

### 6.2 Checklist sécurité

- [ ] 3 mauvais logins → blocage 5 min ✅
- [ ] Cookie `excalidraw.sid` présent (HttpOnly, Secure) ✅
- [ ] HTTPS forcé ✅
- [ ] Headers `X-Forwarded-*` transmis à Excalidraw ✅

---

## 📊 Monitoring post-déploiement

### Logs du service auth

```bash
ssh root@69.62.110.207
docker logs l400k4gwo0kgw440w4848gc0-145306625781 -f --tail 100
```

**À surveiller** :
- `✅ Auth réussie via session` → Bon
- `❌ Auth échouée` → Normal si tentatives invalides
- `🚫 IP bloquée` → Rate limiting fonctionne

### Vérifier les sessions en base

```bash
ssh root@69.62.110.207
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c \
  "SELECT sid, expire, sess->>'userEmail' as email FROM session ORDER BY expire DESC LIMIT 5;"
```

---

## 🔄 Si tout est OK : Merger vers main

```bash
cd /Volumes/ZIKE/codage/agni-mcp-stack

# Revenir sur main
git checkout main

# Merger la branche feature
git merge feature/auth-login-page-with-rate-limiting

# Push
git push origin main

# Dans Coolify : changer la branche de déploiement vers main
```

---

## 📞 Contacts en cas de problème

- **Rollback** : `./ROLLBACK-URGENCE.sh`
- **Logs** : `ssh root@69.62.110.207 "docker logs <container> -f"`
- **VPS** : 69.62.110.207
- **Coolify** : https://coolify.agnisolution.fr

---

## 🎯 Résumé des points de rollback

| Étape | Problème | Rollback | Temps |
|-------|----------|----------|-------|
| 1 (local) | Tests échouent | `git checkout server.js` | 5 sec |
| 2 (commit) | Erreur Git | Aucun impact | 0 sec |
| 3 (deploy) | Build échoue | Changer branche → main | 2 min |
| 4 (test) | Login bugué | `./ROLLBACK-URGENCE.sh` | 2 min |
| 5 (ForwardAuth) | Boucle/erreur | Supprimer labels Traefik | 30 sec |

**À chaque étape, Excalidraw reste fonctionnel jusqu'à l'Étape 5.**
