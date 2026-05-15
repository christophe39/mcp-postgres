# Excalidraw Stack - Déploiement Coolify

## Architecture

```
┌─────────────────────────────────────────────────┐
│ Frontend (excalidraw.agnisolution.fr)           │
│ Image: excalidraw/excalidraw:latest             │
│ Port: 80                                         │
└──────────────┬──────────────────────────────────┘
               │
               │ API calls (POST/GET scenes)
               ▼
┌─────────────────────────────────────────────────┐
│ Backend (exca-api.agnisolution.fr)              │
│ Image: kiliandeca/excalidraw-storage-backend    │
│ Port: 8080                                       │
└──────────────┬──────────────────────────────────┘
               │
               │ Postgres connection
               ▼
┌─────────────────────────────────────────────────┐
│ Postgres (10.0.1.23:5432)                       │
│ Base: excalidraw_storage                        │
│ User: excalidraw_backend                        │
└─────────────────────────────────────────────────┘
```

## Prérequis

- ✅ Base `excalidraw_storage` créée (voir `infra/sql/02_init_excalidraw_storage.sql`)
- ✅ User `excalidraw_backend` créé avec droits
- ✅ DNS configurés dans Cloudflare :
  - `excalidraw.agnisolution.fr` → CNAME vers `agnisolution.fr`
  - `exca-api.agnisolution.fr` → CNAME vers `agnisolution.fr`

## Déploiement dans Coolify

### Étape 1 — Créer un nouveau Service Stack

1. Aller dans Coolify → **New Resource**
2. Choisir **Service**
3. Sélectionner le projet : `My first project` (ou créer `OPEPARTNER`)
4. Sélectionner l'environnement : `production`
5. Donner un nom : `OPEPARTNER-Excalidraw`

### Étape 2 — Importer le docker-compose.yml

1. Cliquer sur **Edit Compose File**
2. Copier-coller le contenu de `docker-compose.yml` (ce fichier dans le même dossier)
3. Sauvegarder

### Étape 3 — Configurer les variables d'environnement

1. Onglet **Environment Variables**
2. Ajouter la variable :
   ```
   POSTGRES_PASSWORD=aMU2bB7AFT0BNeOVbmW5Zey8Qnk2G6tXyTe1oqpC7PA=
   ```
   (Cocher "Secret" pour masquer la valeur)

### Étape 4 — Configurer les domaines

Pour chaque service :

**Service `frontend`** :
- Settings → Domains
- Ajouter : `excalidraw.agnisolution.fr`
- Activer "Generate SSL Certificate"

**Service `backend`** :
- Settings → Domains
- Ajouter : `exca-api.agnisolution.fr`
- Activer "Generate SSL Certificate"

### Étape 5 — Déployer

1. Cliquer sur **Deploy**
2. Attendre que les deux services soient "Healthy"
3. Vérifier les logs en cas d'erreur

## Tests post-déploiement

### Test 1 : Frontend accessible

```bash
curl -I https://excalidraw.agnisolution.fr
# Devrait retourner 200 OK
```

### Test 2 : Backend API accessible

```bash
curl https://exca-api.agnisolution.fr/health
# Devrait retourner {"status": "ok"} ou équivalent
```

### Test 3 : Création d'une scène

1. Ouvrir `https://excalidraw.agnisolution.fr` dans un navigateur
2. Dessiner quelques formes
3. Cliquer sur "Share" → "Link"
4. Vérifier que l'URL générée est sous `excalidraw.agnisolution.fr/#json=...`
5. Copier le lien, l'ouvrir dans un onglet incognito
6. Vérifier que la scène se charge correctement

### Test 4 : Scène stockée en BDD

```bash
ssh root@69.62.110.207
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "SELECT id, created_at FROM excalidraw_scenes ORDER BY created_at DESC LIMIT 5;"
```

Devrait afficher les scènes créées.

## Troubleshooting

### Le frontend ne charge pas

- Vérifier les logs : Coolify → Service `frontend` → Logs
- Vérifier le certificat SSL : `curl -v https://excalidraw.agnisolution.fr`

### Les scènes ne sont pas persistantes (erreur "Failed to save")

- Vérifier que le backend est accessible : `curl https://exca-api.agnisolution.fr/health`
- Vérifier les logs du backend : erreurs de connexion Postgres ?
- Vérifier les variables d'environnement : `POSTGRES_PASSWORD` correcte ?

### Erreur CORS

Si le frontend affiche une erreur CORS dans la console navigateur :
- Vérifier la variable `CORS_ALLOWED_ORIGINS` dans le backend
- Ajouter le domaine manquant

### Le backend ne se connecte pas à Postgres

- Vérifier l'IP `10.0.1.23` du container Postgres :
  ```bash
  docker inspect pk4s888o4wkc8ogokg0sg840 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
  ```
- Vérifier que les deux services sont sur le réseau `coolify`
- Tester la connexion depuis le container backend :
  ```bash
  docker exec excalidraw-backend nc -zv 10.0.1.23 5432
  ```

## Migration future vers opepartner.fr

Quand le domaine `opepartner.fr` sera configuré :

1. Ajouter les DNS dans Cloudflare :
   - `excalidraw.opepartner.fr` → CNAME vers `opepartner.fr`
   - `exca-api.opepartner.fr` → CNAME vers `opepartner.fr`

2. Modifier les variables d'environnement dans Coolify :
   - Frontend : `VITE_APP_BACKEND_V2_*` → remplacer `agnisolution.fr` par `opepartner.fr`
   - Backend : `CORS_ALLOWED_ORIGINS` → ajouter les domaines `opepartner.fr`

3. Modifier les domaines dans les settings Coolify de chaque service

4. Redéployer

5. Mettre à jour les liens dans la BDD `opepartner.schemas_excalidraw` (requête UPDATE)

## Backup et restauration

### Backup de la base excalidraw_storage

```bash
ssh root@69.62.110.207
docker exec pk4s888o4wkc8ogokg0sg840 pg_dump -U excalidraw_backend excalidraw_storage > excalidraw_storage_backup_$(date +%Y%m%d).sql
```

### Restauration

```bash
cat excalidraw_storage_backup_20260515.sql | ssh root@69.62.110.207 "docker exec -i pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage"
```

## Monitoring

### Santé des services

```bash
ssh root@69.62.110.207
docker ps | grep excalidraw
```

### Nombre de scènes stockées

```bash
ssh root@69.62.110.207
docker exec pk4s888o4wkc8ogokg0sg840 psql -U excalidraw_backend -d excalidraw_storage -c "SELECT COUNT(*) FROM excalidraw_scenes;"
```

### Taille de la base

```bash
ssh root@69.62.110.207
docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('excalidraw_storage'));"
```

---

**Document créé le 15 mai 2026**
**Auteur : Claude Code + Christophe Martin**
