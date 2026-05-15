# Infrastructure OPEPARTNER

Scripts et configurations pour le déploiement sur VPS Hostinger via Coolify.

## 📁 Structure

### `docker-compose/`
Compositions Docker pour chaque composant :
- `excalidraw/` — Frontend + storage backend Excalidraw

### `sql/`
Scripts SQL versionnés :
- `01_init_opepartner.sql` — Création des 14 tables MVP
- `02_seed_data.sql` — Données de test (optionnel)
- Futures migrations : `03_add_column_xxx.sql`, etc.

### `traefik/`
Exemples de labels Traefik pour Coolify :
- Configuration HTTPS automatique
- Basic Auth pour Excalidraw
- Routing par sous-domaine

## 🚀 Utilisation

### Création base PostgreSQL
```bash
# SSH vers le VPS
ssh root@69.62.110.207

# Créer la base
docker exec c0408wgcs08kc0w480koowcs psql -U agni_admin -c "CREATE DATABASE opepartner;"

# Exécuter le script d'init
docker exec -i c0408wgcs08kc0w480koowcs psql -U agni_admin -d opepartner < sql/01_init_opepartner.sql

# Vérifier
docker exec c0408wgcs08kc0w480koowcs psql -U agni_admin -d opepartner -c "\dt"
```

### Déploiement Excalidraw via Coolify
1. Copier le contenu de `docker-compose/excalidraw/docker-compose.yml`
2. Dans Coolify UI : New Resource > Docker Compose
3. Coller le YAML
4. Configurer les variables d'environnement
5. Deploy

## 📝 Notes

- Tous les scripts SQL doivent être idempotents (`CREATE TABLE IF NOT EXISTS`, etc.)
- Préfixer les migrations par numéro séquentiel : `01_`, `02_`, etc.
- Documenter chaque migration dans un commentaire d'en-tête
