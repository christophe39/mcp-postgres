# NocoDB - Résumé du Problème et Solution (15 mai 2026)

## 🚨 Problème Initial

**TOUTES les bases PostgreSQL dans NocoDB affichaient 0 records**
- Erreur : `KnexTimeoutError: pool is probably full`
- Erreur UI : "Forbidden host name or IP address"
- **Impact :** Impossible de consulter les données

## ✅ SOLUTION TROUVÉE

### Cause Racine
**NocoDB 2026 bloque par défaut les connexions vers des bases de données sur le réseau local** (protection SSRF - Server-Side Request Forgery).

### Fix en 2 étapes

#### 1. Ajouter la variable d'environnement
```bash
echo 'NC_ALLOW_LOCAL_EXTERNAL_DBS=true' >> /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env
```

#### 2. RECRÉER le container (important : pas juste restart)
```bash
cd /data/coolify/services/hgcocsgs8gk44sgo04w04ckk
docker compose up -d --force-recreate
```

#### 3. Vérifier que la variable est chargée
```bash
docker exec nocodb-hgcocsgs8gk44sgo04w04ckk printenv | grep NC_ALLOW_LOCAL_EXTERNAL_DBS
# Doit afficher : NC_ALLOW_LOCAL_EXTERNAL_DBS=true
```

## 📊 Résultat

✅ **OPEPARTNER** : Base locale connectée avec succès
- Container : `pk4s888o4wkc8ogokg0sg840`
- IP : `10.0.1.23`
- Port : `5432`
- User : `nocodb_opepartner`
- Password : `OpePartner2024!`
- 14 tables visibles et fonctionnelles

## ⚠️ Problème Restant : Tunnel SSH

**CaloCalc (VPS OVH via tunnel SSH)** : Toujours bloqué

### Diagnostic
- Tunnel SSH fonctionne depuis l'hôte (`127.0.0.1:5433` ✅)
- Tunnel SSH **inaccessible depuis containers Docker** (`10.0.1.1:5433` ❌)
- Problème : Routage réseau Docker bloque l'accès au tunnel

### Options pour CaloCalc

#### Option A : Migrer CaloCalc en local (recommandé)
Créer la base `calocalc_inscription` sur le VPS Hostinger et migrer les données.

#### Option B : Proxy PostgreSQL en mode host
Créer un container proxy avec `network_mode: host` qui expose le tunnel SSH dans le réseau Docker.

#### Option C : NocoDB en mode host (non recommandé)
Mettre NocoDB en `network_mode: host` mais perd l'intégration Traefik/Coolify.

## 📝 Leçons Apprises

1. **Toujours vérifier les bases locales d'abord** avant de diagnostiquer les tunnels
2. **NocoDB 2026 a changé la sécurité** : `NC_ALLOW_LOCAL_EXTERNAL_DBS=true` est nécessaire
3. **`docker compose restart` ne recharge PAS le .env** : il faut `--force-recreate`
4. **Tunnels SSH + Docker = complexe** : privilégier les bases locales quand possible

## 🔗 Connexions Actuelles

### OPEPARTNER (Locale - Fonctionne ✅)
```
Host: 10.0.1.23 (ou pk4s888o4wkc8ogokg0sg840)
Port: 5432
Database: opepartner
User: nocodb_opepartner
Password: OpePartner2024!
```

### CaloCalc (Tunnel SSH - À corriger ⚠️)
```
Host: 10.0.1.1 (tunnel SSH vers VPS OVH)
Port: 5433
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
```

## 🛠️ Commandes Utiles

### Tester connexion PostgreSQL locale
```bash
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://nocodb_opepartner:OpePartner2024!@10.0.1.23:5432/opepartner' \
  -c 'SELECT COUNT(*) FROM clients;'
```

### Vérifier le tunnel SSH
```bash
ssh root@69.62.110.207 "nc -zv 127.0.0.1 5433"
```

### Logs NocoDB
```bash
docker logs --tail 100 nocodb-hgcocsgs8gk44sgo04w04ckk 2>&1 | grep -i error
```

---

**Date de résolution :** 15 mai 2026  
**Temps de debug :** ~2h30  
**Solution finale :** Variable d'environnement + base locale
