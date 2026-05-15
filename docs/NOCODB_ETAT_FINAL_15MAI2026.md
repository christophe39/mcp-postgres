# NocoDB - État Final Debug Session 15 Mai 2026

## 📊 ÉTAT ACTUEL (17h00)

### ✅ CE QUI FONCTIONNE

#### OPEPARTNER (Base Locale VPS Hostinger)
- **Status :** ✅ 100% Fonctionnel
- **Container PostgreSQL :** `pk4s888o4wkc8ogokg0sg840`
- **Réseau :** coolify (même réseau que NocoDB)
- **IP :** `10.0.1.23`
- **Connexion NocoDB :**
  ```
  Host: 10.0.1.23
  Port: 5432
  Database: opepartner
  User: nocodb_opepartner
  Password: OpePartner2024!
  Schema: public
  ```
- **Résultat :** 14 tables visibles, données accessibles

### ❌ CE QUI NE FONCTIONNE PAS

#### CaloCalc (Base VPS OVH via Tunnel SSH)
- **Status :** ❌ 0 records affichés
- **Erreur :** KnexTimeoutError - Pool de connexions saturé
- **Tunnel SSH :** Fonctionne depuis l'hôte (✅ `127.0.0.1:5433`)
- **Problème :** Containers Docker ne peuvent PAS accéder au tunnel (`10.0.1.1:5433` ❌)
- **Configuration actuelle :**
  ```
  Host: 10.0.1.1 (gateway réseau coolify)
  Port: 5433 (tunnel SSH vers VPS OVH)
  Database: calocalc_inscription
  User: calocalc_user
  Password: CaloCalc2024
  ```

## 🔍 DIAGNOSTIC COMPLET

### Architecture Réseau

```
VPS Hostinger (69.62.110.207)
├─ NocoDB (container sur réseau coolify, IP: 10.0.1.16)
├─ PostgreSQL OPEPARTNER (container, IP: 10.0.1.23) ✅ ACCESSIBLE
├─ Tunnel SSH (hôte, écoute sur 0.0.0.0:5433)
│   └─> Forward vers VPS OVH (51.255.201.205)
│       └─> PostgreSQL CaloCalc (10.0.1.7:5432)
│
└─ Problème : NocoDB ne peut pas accéder au tunnel SSH

Réseau Docker coolify :
- Gateway : 10.0.1.1
- Sous-réseau : 10.0.1.0/24
- Interface hôte docker0 : 10.0.0.1
```

### Tests Effectués

#### ✅ Tests qui ont réussi
```bash
# 1. Tunnel SSH accessible depuis l'hôte
ssh root@69.62.110.207 "nc -zv 127.0.0.1 5433"
# Résultat : Connection succeeded

# 2. Connexion PostgreSQL directe depuis l'hôte
docker run --rm --network host postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@127.0.0.1:5433/calocalc_inscription' \
  -c 'SELECT COUNT(*) FROM users;'
# Résultat : 18 users

# 3. Connexion PostgreSQL locale depuis réseau Docker
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://nocodb_opepartner:OpePartner2024!@10.0.1.23:5432/opepartner' \
  -c 'SELECT COUNT(*) FROM clients;'
# Résultat : 0 clients (normal, base vide)
```

#### ❌ Tests qui ont échoué
```bash
# 1. Accès au tunnel depuis réseau Docker (gateway)
docker run --rm --network coolify postgres:17-alpine \
  nc -zv 10.0.1.1 5433
# Résultat : Operation timed out

# 2. Accès au tunnel depuis réseau Docker (docker0)
docker run --rm --network coolify postgres:17-alpine \
  nc -zv 10.0.0.1 5433
# Résultat : Operation timed out

# 3. Accès au tunnel via IP publique
docker run --rm --network coolify postgres:17-alpine \
  nc -zv 69.62.110.207 5433
# Résultat : Operation timed out
```

### Tentatives de Résolution (toutes échouées)

1. **Règles iptables DOCKER-USER**
   ```bash
   iptables -I DOCKER-USER -p tcp --dport 5433 -j ACCEPT
   ```
   ❌ Résultat : Aucun effet

2. **NocoDB en network_mode: host**
   ✅ Accès au tunnel OK
   ❌ Mais conflit port 8080 + perte intégration Traefik

3. **Container proxy PostgreSQL (socat)**
   - Mode 1 : Proxy sur réseau coolify avec extra_hosts
     ❌ Ne peut pas accéder au tunnel
   - Mode 2 : Proxy en network_mode: host
     ❌ Pas accessible depuis réseau coolify

4. **extra_hosts dans docker-compose NocoDB**
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```
   ❌ Résolution DNS OK mais connexion timeout

## 🎯 SOLUTIONS RESTANTES À TESTER

### Solution A : IP Publique VPS OVH (Recommandée avec précaution)

**Principe :** Configurer PostgreSQL sur VPS OVH pour accepter connexions depuis IP publique VPS Hostinger

#### Étapes
```bash
# 1. Sur VPS OVH : Modifier pg_hba.conf
docker exec h48w8cwscggoo0s4ws8s4gws sh -c \
  "echo 'host calocalc_inscription calocalc_user 69.62.110.207/32 scram-sha-256' >> /var/lib/postgresql/data/pg_hba.conf"

# 2. Recharger PostgreSQL
docker exec h48w8cwscggoo0s4ws8s4gws psql -U postgres -c "SELECT pg_reload_conf();"

# 3. Vérifier firewall OVH autorise port 5432 depuis 69.62.110.207

# 4. Tester depuis VPS Hostinger
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@51.255.201.205:5432/calocalc_inscription' \
  -c 'SELECT COUNT(*) FROM users;'

# 5. Dans NocoDB : Modifier connexion CaloCalc
Host: 51.255.201.205
Port: 5432
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
SSL: require (important!)
```

#### ⚠️ Sécurité
- ✅ Firewall limité à l'IP 69.62.110.207
- ✅ Connexion SSL obligatoire
- ✅ User dédié avec permissions limitées
- ⚠️ Port PostgreSQL exposé sur Internet (risque DDoS)

### Solution B : Migrer CaloCalc en Local (La plus sûre)

**Principe :** Créer `calocalc_inscription` sur VPS Hostinger et migrer les données

#### Étapes
```bash
# 1. Sur VPS OVH : Dump de la base
ssh root@51.255.201.205 "docker exec h48w8cwscggoo0s4ws8s4gws \
  pg_dump -U calocalc_user -d calocalc_inscription -Fc -f /tmp/calocalc_dump.backup"

# 2. Copier le dump vers VPS Hostinger
scp root@51.255.201.205:/tmp/calocalc_dump.backup /tmp/

# 3. Sur VPS Hostinger : Créer la base dans le container existant
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 \
  psql -U postgres -c 'CREATE DATABASE calocalc_inscription;'"

# 4. Créer l'utilisateur
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 \
  psql -U postgres -c \"CREATE USER calocalc_user WITH PASSWORD 'CaloCalc2024';\""

# 5. Restaurer le dump
ssh root@69.62.110.207 "docker exec -i pk4s888o4wkc8ogokg0sg840 \
  pg_restore -U postgres -d calocalc_inscription < /tmp/calocalc_dump.backup"

# 6. Permissions
ssh root@69.62.110.207 "docker exec pk4s888o4wkc8ogokg0sg840 \
  psql -U postgres -c 'GRANT ALL ON DATABASE calocalc_inscription TO calocalc_user;'"

# 7. Dans NocoDB : Modifier connexion CaloCalc
Host: 10.0.1.23 (ou pk4s888o4wkc8ogokg0sg840)
Port: 5432
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
```

#### ✅ Avantages
- Tout en local, pas de tunnel
- Même container que OPEPARTNER (simplifie gestion)
- Pas d'exposition Internet
- Performance optimale

### Solution C : Proxy PostgreSQL avec Tunnel (Complexe)

**Principe :** Container dédié en network_mode: host qui expose le tunnel dans le réseau Docker

#### Étapes
```bash
# 1. Créer container socat en mode host
cat > /data/postgres-tunnel-proxy/docker-compose.yml << 'EOF'
services:
  tunnel-proxy:
    image: alpine/socat:latest
    container_name: postgres-tunnel-calocalc
    restart: unless-stopped
    network_mode: host
    command: tcp-listen:15432,fork,reuseaddr tcp-connect:127.0.0.1:5433
    labels:
      - proxy.managed=true
EOF

# 2. Démarrer le proxy
cd /data/postgres-tunnel-proxy && docker compose up -d

# 3. Ajouter règle iptables
iptables -I INPUT -p tcp --dport 15432 -s 10.0.1.0/24 -j ACCEPT

# 4. Dans NocoDB : Modifier connexion CaloCalc
Host: 69.62.110.207 (IP publique hôte)
Port: 15432
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
```

⚠️ **Attention :** Cette solution a échoué lors des tests précédents à cause du routage Docker.

## 📝 CONFIGURATION ACTUELLE

### NocoDB Container
```yaml
# /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/docker-compose.yml
services:
  nocodb:
    image: nocodb/nocodb
    networks:
      - coolify
      - hgcocsgs8gk44sgo04w04ckk
    # PAS de network_mode: host
    # PAS de extra_hosts actuellement
```

### Variables d'environnement importantes
```bash
# /data/coolify/services/hgcocsgs8gk44sgo04w04ckk/.env
NC_ALLOW_LOCAL_EXTERNAL_DBS=true  # ✅ AJOUTÉ ET FONCTIONNE
NC_ALLOW_LOCAL_HOOKS=true
NC_DB_POOL_MIN=0
NC_DB_POOL_MAX=100
NC_DB_POOL_TIMEOUT=60000
NC_DB_POOL_IDLE_TIMEOUT=30000
```

### Tunnel SSH (autossh)
```bash
# Processus actif
root     2845735  /usr/lib/autossh/autossh -M 0 -N -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -L 0.0.0.0:5433:10.0.1.7:5432 root@51.255.201.205

# Écoute
tcp  0  0  0.0.0.0:5433  0.0.0.0:*  LISTEN  ssh
```

### PostgreSQL Containers sur VPS Hostinger
```
pk4s888o4wkc8ogokg0sg840  (postgres:17-alpine)
├─ opepartner (✅ connecté à NocoDB)
├─ calocalc_inscription (❌ à créer/migrer)
└─ Réseau: coolify, IP: 10.0.1.23

coolify-db (postgres:15-alpine)
└─ Base Coolify uniquement

postgresql-bc848ocwk08wc4wg0804oogw (postgres:16-alpine)
└─ Base Umami uniquement
```

## 🚀 PROCHAINES ACTIONS RECOMMANDÉES

### Priorité 1 : Solution B (Migration locale) - LA PLUS SÛRE
1. Faire un backup complet de `calocalc_inscription` sur VPS OVH
2. Créer la base sur VPS Hostinger (container `pk4s888o4wkc8ogokg0sg840`)
3. Migrer les données via pg_dump/pg_restore
4. Reconfigurer NocoDB pour pointer vers la base locale
5. Tester et valider
6. Supprimer le tunnel SSH (optionnel, garder en backup)

**Temps estimé :** 1h  
**Risque :** Faible (avec backup)  
**Bénéfice :** Architecture simplifiée, pas de tunnel, tout local

### Priorité 2 : Solution A (IP Publique) - SI MIGRATION IMPOSSIBLE
1. Configurer pg_hba.conf sur VPS OVH
2. Vérifier firewall OVH
3. Activer SSL obligatoire
4. Tester connexion depuis VPS Hostinger
5. Reconfigurer NocoDB

**Temps estimé :** 30min  
**Risque :** Moyen (exposition Internet)  
**Bénéfice :** Rapide, garde les données sur VPS OVH

## 📞 CONTACTS / INFOS UTILES

### VPS OVH
- IP : 51.255.201.205
- Container PostgreSQL : h48w8cwscggoo0s4ws8s4gws
- User : postgres / calocalc_user

### VPS Hostinger
- IP : 69.62.110.207
- Container PostgreSQL : pk4s888o4wkc8ogokg0sg840
- User : postgres

### NocoDB
- URL : https://nocodb.agnisolution.fr
- Container : nocodb-hgcocsgs8gk44sgo04w04ckk
- Version : 0.301.5 (ou similaire 2026.x)

## 🎓 LEÇONS APPRISES

1. **NocoDB 2026 a la protection SSRF** → Toujours ajouter `NC_ALLOW_LOCAL_EXTERNAL_DBS=true`
2. **Docker restart ne recharge PAS .env** → Utiliser `docker compose up -d --force-recreate`
3. **Tunnels SSH + Docker = problème de routage réseau** → Privilégier bases locales
4. **Toujours vérifier bases locales en premier** avant de débugger les tunnels
5. **Container name ou IP ?** → IP plus fiable pour connexions inter-containers

---

**Session de debug :** 15 mai 2026, 14h30-17h00 (2h30)  
**Résultat :** OPEPARTNER ✅ | CaloCalc ❌ (routage Docker)  
**Prochaine étape :** Migration CaloCalc en local (Solution B)
