# NocoDB - Résumé Rapide du Problème

## 🚨 Situation

**TOUTES les bases PostgreSQL dans NocoDB affichent 0 records**
- Base CaloCalc (pe6zak9d7qjwers) : vide
- Erreur systématique : `KnexTimeoutError: pool is probably full`
- **Impact :** Business bloqué, impossible de consulter les données CaloCalc

## ✅ Ce qui fonctionne

- ✅ Données PostgreSQL intactes (vérifiées directement)
- ✅ Réseau Docker OK (tous les containers accessibles)
- ✅ Connexions PostgreSQL directes OK (hors NocoDB)
- ✅ NocoDB démarre correctement (healthy)

## ❌ Ce qui ne fonctionne PAS

- ❌ NocoDB → PostgreSQL : timeout systématique
- ❌ Pool de connexions Knex saturé immédiatement
- ❌ Toutes les requêtes API échouent

## 🔍 Cause probable

**Pool de connexions Knex bloqué/saturé**
- Soit connexions zombies qui ne se ferment pas
- Soit bug version NocoDB 0.301.5
- Soit problème tunnel SSH vers VPS OVH (10.0.1.1:5433)

## 🎯 Prochaines actions (par priorité)

### 1. Diagnostic tunnel SSH (15 min)
```bash
# Tester le tunnel
nc -zv 10.0.1.1 5433

# Connexion via tunnel
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@10.0.1.1:5433/calocalc_inscription' \
  -c 'SELECT COUNT(*) FROM information_schema.tables;'

# Redémarrer si nécessaire
kill PID_autossh && relancer
```

### 2. Nettoyer connexions zombies (10 min)
```bash
# Lister connexions
docker exec c0408wgcs08kc0w480koowcs psql -U agni_admin -c \
  "SELECT pid, state, query_start FROM pg_stat_activity WHERE datname='calocalc_inscription';"

# Killer les bloquées
docker exec c0408wgcs08kc0w480koowcs psql -U agni_admin -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction';"

# Redémarrer NocoDB
docker restart nocodb-hgcocsgs8gk44sgo04w04ckk
```

### 3. Mode debug NocoDB (15 min)
```bash
echo "NC_LOG_LEVEL=debug" >> /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env
echo "DEBUG=nc*" >> /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env
docker restart nocodb-hgcocsgs8gk44sgo04w04ckk
docker logs -f nocodb-hgcocsgs8gk44sgo04w04ckk
```

### 4. Si échec : Instance NocoDB de test (1h)
- Nouveau container NocoDB
- Une seule connexion PostgreSQL simple
- Valider que ça marche
- Migrer si OK

### 5. Si échec : Downgrade NocoDB (30 min)
- Tester version 0.25x ou 0.30x antérieure
- Vérifier changelogs pour bugs pool

## 📄 Documentation complète

Voir [NOCODB_DEBUG_SESSION_20260515.md](./NOCODB_DEBUG_SESSION_20260515.md) pour :
- Diagnostic complet
- Toutes les commandes testées
- Configuration détaillée
- Backups créés
