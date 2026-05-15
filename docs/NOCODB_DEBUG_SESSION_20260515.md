# Session de Debug NocoDB - 15 mai 2026

## 🚨 PROBLÈME CRITIQUE

**Toutes les bases PostgreSQL dans NocoDB sont vides (0 records)** depuis aujourd'hui.
- ❌ Base CaloCalc (pe6zak9d7qjwers) : vide
- ❌ Toutes les sources PostgreSQL : timeout errors
- ✅ Les données PostgreSQL existent bien (vérifiées directement)
- ✅ La connectivité réseau fonctionne

**Impact business :** Impossibilité de consulter les bases CaloCalc depuis NocoDB.

---

## 🔍 DIAGNOSTIC COMPLET

### 1. Infrastructure VPS

**VPS Hostinger (69.62.110.207)**
- Hostname : `srv764918.hstgr.cloud`
- NocoDB : `nocodb-hgcocsgs8gk44sgo04w04ckk` (nocodb/nocodb v0.301.5)
- URL : https://nocodb.agnisolution.fr

**Containers PostgreSQL identifiés :**
```
pk4s888o4wkc8ogokg0sg840     postgres:17-alpine    Up 9h (healthy)
c0408wgcs08kc0w480koowcs     postgres              Up 9h (healthy)
pg0kgg4g8kwgg04s4wg0sos8     postgres              Up 9h (healthy)
postgresql-bc848...           postgres:16-alpine    Up 9h (healthy)
i004k4ckow8c8o8w004wk8oc     pgvector/pgvector:pg17 Up 9h (healthy)
```

**Tunnel SSH actif vers VPS OVH :**
```bash
/usr/lib/autossh/autossh -M 0 -N -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -L 0.0.0.0:5433:10.0.1.7:5432 root@51.255.201.205
```
- Port local 5433 → VPS OVH 51.255.201.205:10.0.1.7:5432

### 2. Erreurs observées dans NocoDB

**Erreur récurrente (logs) :**
```
KnexTimeoutError: Knex: Timeout acquiring a connection. 
The pool is probably full. Are you missing a .transacting(trx) call?
```

**Tous les appels API échouent :**
- `/api/v1/db/data/noco/pe6zak9d7qjwers/.../count` → timeout
- Même erreur pour toutes les bases PostgreSQL
- Aucune erreur pour les bases SQLite locales

### 3. Tests de connectivité effectués

✅ **Réseau Docker :**
```bash
docker exec nocodb nc -zv pk4s888o4wkc8ogokg0sg840 5432
# → pk4s888o4wkc8ogokg0sg840 (10.0.1.23:5432) open

docker exec nocodb nc -zv c0408wgcs08kc0w480koowcs 5432
# → c0408wgcs08kc0w480koowcs (10.0.1.8:5432) open
```

✅ **Connexion PostgreSQL directe (hors NocoDB) :**
```bash
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://agni_admin:HB4DuyxwL5X3SkEH5BH57sTysyl5Y6t8lehfMetN63T641f6KqMKmLBaqapV1m2a@c0408wgcs08kc0w480koowcs:5432/calocalc_inscription' \
  -c 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';'
# → count: 14 (succès)
```

✅ **Données PostgreSQL intactes :**
```bash
docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -d opepartner -c '\dt'
# → 14 tables présentes
```

❌ **Mais NocoDB ne peut pas se connecter** → timeout systématique

### 4. Configuration NocoDB analysée

**Métadonnées stockées dans :** SQLite `/usr/app/data/noco.db`

**Tables importantes :**
- `nc_sources_v2` : Sources de données (connexions aux bases)
- `nc_integrations_v2` : Connexions réutilisables (credentials)
- `nc_bases_v2` : Projets/Bases NocoDB

**Intégrations PostgreSQL configurées :**

| ID | Titre | Host | Port | Database | User |
|----|-------|------|------|----------|------|
| int240z8j85vmw44x | calocalc_base | 10.0.1.14 | 5432 | (vide) | postgres |
| into7dni0bem5n0dh | test_migration | pg0kgg4g8kwgg04s4wg0sos8 | 5432 | postgres | postgres |
| intjxgl0swf6i36st | CaloCalc Inscription | c0408wgcs08kc0w480koowcs | 5432 | calocalc_inscription | agni_admin |
| int2ptxjt9nswq4kb | calocalc_inscription | c0408wgcs08kc0w480koowcs | 5432 | calocalc_inscription | calocalc_user |
| intqbr934aqj9soz6 | BDD_AGNI | c0408wgcs08kc0w480koowcs | 5432 | db_agni | agni_admin |
| int5qcx74gs6ftou5 | SuperToken | postgres-xck84kccwoggg844wowwswsc | 5432 | supertokens | UHB4eTGTdVdAWyZ0 |
| int91iaig4491ti6j | departements | c0408wgcs08kc0w480koowcs | 5432 | departements | agni_admin |
| int7ic4bz94sd7pjt | Calocalc_native | pk4s888o4wkc8ogokg0sg840 | 5432 | postgres | postgres |
| int04apf3q3ntfp2c | CaloCalc-App | pk4s888o4wkc8ogokg0sg840 | 5432 | calocalc_inscription | postgres |
| int5i9d981c3e2lmu | calocalc_prospection | pk4s888o4wkc8ogokg0sg840 | 5432 | calocalc_prospection | postgres |
| **intd0vv1u63p7ikwd** | **calocalc sur OVH** | **10.0.1.1** | **5433** | **calocalc_inscription** | **calocalc_user** |
| int4m5ohkvprylg0x | Base_AgniConsult | c0408wgcs08kc0w480koowcs | 5432 | Base_AgniConsult | agni_admin |

**⚠️ Connexion problématique : "calocalc sur OVH"**
- Host: `10.0.1.1` (gateway réseau Docker)
- Port: `5433` (tunnel SSH vers VPS OVH)
- Password : `CaloCalc2024`
- Cette connexion est utilisée par la base CaloCalc (pe6zak9d7qjwers)

**Source de données CaloCalc (pe6zak9d7qjwers) :**
```sql
SELECT s.alias, s.fk_integration_id, i.title 
FROM nc_sources_v2 s 
LEFT JOIN nc_integrations_v2 i ON s.fk_integration_id = i.id 
WHERE s.base_id = 'pe6zak9d7qjwers';

-- Résultat:
-- calocalc | intd0vv1u63p7ikwd | calocalc sur OVH
```

### 5. Variables d'environnement NocoDB

**Fichier `/data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env` :**
```env
SERVICE_NAME_NOCODB=nocodb
SERVICE_FQDN_NOCODB=nocodb.agnisolution.fr
SERVICE_URL_NOCODB=https://nocodb.agnisolution.fr
SERVICE_URL_NOCODB_8080=https://nocodb.agnisolution.fr:8080
SERVICE_FQDN_NOCODB_8080=nocodb.agnisolution.fr:8080
NC_AUTH_JWT_SECRET=CALOSECRET123_NOCODB_JWT_2025_AGNI
NC_ALLOW_LOCAL_HOOKS=true
NOCODB_TOKEN=RdmmBLZGR_Akhvmc3k-qEa-bkQFYjL2jChJ6nDf2
DB_MAX_POOL_SIZE=50
DB_QUERY_LIMIT_DEFAULT=100
DB_QUERY_LIMIT_GROUP_BY_GROUP=1000
DB_QUERY_LIMIT_MAX=1000
NC_DB_POOL_MIN=0
NC_DB_POOL_MAX=100
NC_DB_POOL_TIMEOUT=60000
NC_DB_POOL_IDLE_TIMEOUT=30000
```

**Changements effectués lors du debug :**
1. ❌ Ajout de `NC_DISABLE_SSRF=true` → **Enlevée** (cassait les connexions)
2. ✅ Augmentation des limites de pool (50 → 100)
3. ✅ Augmentation des timeouts (60s)

### 6. Réseaux Docker

**NocoDB est sur 2 réseaux :**
- `coolify` (partagé avec les containers PostgreSQL)
- `hgcocsgs8gk44sgo04w04ckk` (réseau isolé propre à NocoDB)

**Tous les containers PostgreSQL sont accessibles depuis NocoDB** (tests nc réussis).

---

## ❌ TENTATIVES INFRUCTUEUSES

### 1. Modification du fichier noco.db
- ❌ Insertion manuelle d'une source de données dans SQLite
- **Résultat :** Corruption temporaire, restauration nécessaire
- **Leçon :** NocoDB utilise un système mixte SQLite + métadonnées en cache

### 2. Création tunnel temporaire
- ❌ Tunnel socat vers PostgreSQL exposé sur port 15432
- **Résultat :** Connexion OK hors NocoDB, mais NocoDB timeout quand même
- **Leçon :** Le problème n'est pas réseau mais interne à NocoDB

### 3. Redémarrage NocoDB (multiple fois)
- ❌ Ne résout pas le problème de timeout
- Pool de connexions se remplit immédiatement à chaque tentative

### 4. Augmentation limites pool
- ❌ Passage de 50 à 100 connexions max
- ❌ Timeout augmenté à 60s
- **Résultat :** Aucune amélioration

---

## 🔧 PISTES DE SOLUTION À EXPLORER

### Piste 1 : Problème de version NocoDB

**Hypothèse :** Version 0.301.5 a un bug de pool de connexions

**Actions à tester :**
```bash
# Vérifier les changelogs NocoDB
# Tester downgrade vers version stable antérieure
# Ou upgrade vers version plus récente
```

### Piste 2 : Problème de tunnel SSH

**Hypothèse :** Le tunnel `10.0.1.1:5433` est cassé ou pointe vers une mauvaise destination

**Actions à tester :**
```bash
# 1. Vérifier l'IP destination sur VPS OVH
ssh root@51.255.201.205 "docker ps --format '{{.Names}}\t{{.IPAddress}}' | grep postgres"

# 2. Tester connexion DIRECTE au tunnel depuis le VPS
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@10.0.1.1:5433/calocalc_inscription' \
  -c 'SELECT current_database();'

# 3. Redémarrer le tunnel proprement
systemctl restart autossh-calocalc  # ou équivalent

# 4. Vérifier les logs du tunnel
tail -f /tmp/autossh.log
```

### Piste 3 : Recréer la connexion "calocalc sur OVH"

**Hypothèse :** La configuration de l'intégration est corrompue

**Actions à tester :**
```bash
# 1. Sauvegarder la config actuelle
sqlite3 /usr/app/data/noco.db \
  "SELECT * FROM nc_integrations_v2 WHERE id='intd0vv1u63p7ikwd';" \
  > backup_integration_calocalc_ovh.sql

# 2. Supprimer l'intégration via UI NocoDB
# 3. Recréer une nouvelle intégration identique
# 4. Réassigner à la source de données
```

### Piste 4 : Créer une instance NocoDB de test

**Hypothèse :** Problème spécifique à cette instance

**Actions à tester :**
```bash
# 1. Déployer NocoDB fresh via Coolify (nouveau service)
# 2. Créer UNE SEULE connexion PostgreSQL simple
# 3. Tester si le problème persiste
# 4. Si ça marche, migrer progressivement les sources
```

### Piste 5 : Vérifier les connexions "zombies"

**Hypothèse :** Des connexions PostgreSQL restent ouvertes et bloquent le pool

**Actions à tester :**
```bash
# 1. Lister toutes les connexions actives
docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -c \
  "SELECT pid, usename, application_name, client_addr, state, query_start 
   FROM pg_stat_activity WHERE datname IS NOT NULL ORDER BY query_start;"

# 2. Killer les connexions NocoDB bloquées
docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE application_name LIKE '%noco%' AND state = 'idle in transaction';"

# 3. Redémarrer NocoDB immédiatement après
docker restart nocodb-hgcocsgs8gk44sgo04w04ckk
```

### Piste 6 : Debug mode NocoDB

**Actions à tester :**
```bash
# Activer le mode debug NocoDB
echo "NC_LOG_LEVEL=debug" >> /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env
echo "DEBUG=nc*" >> /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env
docker restart nocodb-hgcocsgs8gk44sgo04w04ckk

# Observer les logs en détail
docker logs -f nocodb-hgcocsgs8gk44sgo04w04ckk --tail 100
```

### Piste 7 : Vérifier pg_hba.conf

**Hypothèse :** PostgreSQL rejette les connexions de NocoDB

**Actions à tester :**
```bash
# Vérifier les règles d'authentification
docker exec c0408wgcs08kc0w480koowcs cat /var/lib/postgresql/data/pg_hba.conf

# Vérifier les logs PostgreSQL pour des rejets
docker logs c0408wgcs08kc0w480koowcs 2>&1 | grep -i "authentication\|reject\|fail" | tail -50
```

---

## 📋 COMMANDES UTILES DE DIAGNOSTIC

### Vérifier l'état global
```bash
# Status containers
ssh root@69.62.110.207 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'nocodb|postgres'"

# Logs NocoDB
ssh root@69.62.110.207 "docker logs nocodb-hgcocsgs8gk44sgo04w04ckk --tail 50 | grep -i error"

# Connexions PostgreSQL actives
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 psql -U postgres -c 'SELECT count(*), state FROM pg_stat_activity GROUP BY state;'"
```

### Tester une connexion PostgreSQL
```bash
# Depuis le réseau Docker
ssh root@69.62.110.207 "docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://USER:PASS@HOST:PORT/DATABASE' -c 'SELECT current_database();'"

# Tester le tunnel OVH
ssh root@69.62.110.207 "nc -zv 10.0.1.1 5433"
```

### Sauvegarder/Restaurer noco.db
```bash
# Backup
ssh root@69.62.110.207 "docker cp nocodb-hgcocsgs8gk44sgo04w04ckk:/usr/app/data/noco.db /tmp/noco_backup_$(date +%Y%m%d_%H%M%S).db"

# Restore
ssh root@69.62.110.207 "docker stop nocodb-hgcocsgs8gk44sgo04w04ckk && \
  docker cp /tmp/noco_backup_XXXXXX.db nocodb-hgcocsgs8gk44sgo04w04ckk:/usr/app/data/noco.db && \
  docker start nocodb-hgcocsgs8gk44sgo04w04ckk"
```

---

## 📁 BACKUPS CRÉÉS

**Backup complet NocoDB :** `/tmp/nocodb_backup_20260515_160057/`
- `data/` : Volume complet NocoDB
- `nocodb_db.sql` : Dump PostgreSQL des métadonnées (si utilisées)

**Fichiers sauvegardés localement :**
- `/tmp/noco_opepartner.db` : Copie du fichier SQLite original
- `/tmp/noco_check.db` : Copie après restauration

---

## 🎯 PLAN D'ACTION RECOMMANDÉ

### Étape 1 : Diagnostic approfondi du tunnel (30 min)
1. Vérifier que le tunnel pointe vers le bon container sur VPS OVH
2. Tester la connexion PostgreSQL à travers le tunnel
3. Redémarrer le tunnel si nécessaire
4. Vérifier les logs du tunnel

### Étape 2 : Test avec NocoDB en mode debug (30 min)
1. Activer `NC_LOG_LEVEL=debug`
2. Tenter une connexion
3. Analyser les logs détaillés
4. Identifier exactement où le timeout se produit

### Étape 3 : Nettoyer les connexions zombies (15 min)
1. Lister toutes les connexions PostgreSQL
2. Killer les connexions bloquées
3. Redémarrer NocoDB immédiatement après

### Étape 4 : Si échec, créer instance de test (1h)
1. Déployer nouveau NocoDB via Coolify
2. Tester avec UNE connexion simple
3. Si ça marche, migrer progressivement

### Étape 5 : Si échec, downgrade/upgrade NocoDB (1h)
1. Identifier version stable connue
2. Modifier image Docker dans Coolify
3. Redéployer
4. Tester

---

## 🔗 LIENS UTILES

- **NocoDB GitHub Issues :** https://github.com/nocodb/nocodb/issues
- **NocoDB Discord :** https://discord.gg/5RgZmkW
- **Documentation Pool Knex :** https://knexjs.org/guide/#pooling

---

## 📝 NOTES IMPORTANTES

1. **NE PAS toucher au fichier noco.db directement** → Risque de corruption
2. **Toujours faire un backup avant toute manipulation**
3. **Le problème n'est PAS lié aux données** (elles sont intactes dans PostgreSQL)
4. **Le problème n'est PAS réseau** (connectivité testée et OK)
5. **Le problème est interne à NocoDB** → Pool de connexions Knex
6. **Impact business critique** → À résoudre en priorité absolue

---

**Dernière mise à jour :** 15 mai 2026 16:15
**Prochaine session :** Implémenter le plan d'action étape par étape
