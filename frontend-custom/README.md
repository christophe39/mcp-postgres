# Excalidraw Frontend Custom - OPEPARTNER

## 🎯 Objectif

Builder une image Docker Excalidraw personnalisée qui pointe vers notre backend self-hosted (`exca-api.agnisolution.fr`) au lieu du backend officiel Excalidraw.

## 📋 Prérequis

- Docker installé sur ton Mac
- Connexion internet pour télécharger les sources Excalidraw

## 🔨 Build de l'image

### Option A : Build local (pour utiliser directement dans Coolify)

```bash
cd frontend-custom
./build.sh
```

**Temps estimé** : 10-15 minutes (dépend de ta connexion et de la puissance du Mac)

L'image sera créée localement avec le nom : `excalidraw-opepartner:latest`

### Option B : Build + Push vers Docker Hub (pour partager/sauvegarder)

1. **Créer un compte Docker Hub** (si pas déjà fait) : https://hub.docker.com

2. **Login Docker Hub** :
   ```bash
   docker login
   ```

3. **Builder l'image** :
   ```bash
   cd frontend-custom
   ./build.sh
   ```

4. **Tagger et pusher** :
   ```bash
   # Remplace TON_USERNAME par ton username Docker Hub
   docker tag excalidraw-opepartner:latest TON_USERNAME/excalidraw-opepartner:latest
   docker push TON_USERNAME/excalidraw-opepartner:latest
   ```

## 🚀 Déploiement dans Coolify

### Si build local (Option A)

1. **Sauvegarder l'image en tar** :
   ```bash
   docker save excalidraw-opepartner:latest > excalidraw-opepartner.tar
   ```

2. **Transférer sur le VPS** :
   ```bash
   scp excalidraw-opepartner.tar root@69.62.110.207:/tmp/
   ```

3. **Charger l'image sur le VPS** :
   ```bash
   ssh root@69.62.110.207 "docker load < /tmp/excalidraw-opepartner.tar"
   ```

4. **Modifier le docker-compose.yml** dans Coolify :
   Remplacer :
   ```yaml
   image: excalidraw/excalidraw:latest
   ```
   
   Par :
   ```yaml
   image: excalidraw-opepartner:latest
   ```

5. **Redéployer** le frontend dans Coolify

### Si push Docker Hub (Option B)

1. **Modifier le docker-compose.yml** dans Coolify :
   Remplacer :
   ```yaml
   image: excalidraw/excalidraw:latest
   ```
   
   Par :
   ```yaml
   image: TON_USERNAME/excalidraw-opepartner:latest
   ```

2. **Redéployer** le frontend dans Coolify

## 🔐 Sécurisation de l'accès (Étape suivante)

Une fois le frontend custom déployé, on ajoutera une authentification Traefik BasicAuth pour protéger l'accès.

## 🧪 Test local avant déploiement

```bash
docker run -p 8080:80 excalidraw-opepartner:latest
```

Ouvrir dans le navigateur : http://localhost:8080

Tester de créer un dessin et de cliquer sur "Partager" → le lien devrait pointer vers `exca-api.agnisolution.fr`.

## 📝 Notes

- Le build clone le repo GitHub officiel d'Excalidraw (branche `main`)
- Les variables d'environnement sont compilées au moment du build
- L'image finale fait environ 100-150 MB

## ❓ Troubleshooting

**Erreur "Cannot connect to Docker daemon"** :
- Vérifie que Docker Desktop est lancé sur ton Mac

**Build très lent** :
- Normal la première fois (téléchargement des dépendances Node.js)
- Les builds suivants seront plus rapides grâce au cache Docker

**Erreur "git clone failed"** :
- Vérifie ta connexion internet
- Essaie avec un autre réseau WiFi

---

**Créé le 15 mai 2026**
**Auteur : Claude Code + Christophe Martin**
