# NocoDB → CaloCalc VPS OVH : Solution avec Tunnel

## 🎯 DÉCISION ARCHITECTURE

**CaloCalc RESTE sur VPS OVH** (51.255.201.205)

### Justification
- ✅ VPS OVH plus puissant pour gérer la charge
- ✅ Code des applications déjà hébergé sur VPS OVH
- ✅ Cohérence : données + code au même endroit
- ✅ VPS Hostinger : uniquement outils (NocoDB, n8n, etc.)

## 🔧 SOLUTIONS POSSIBLES (par ordre de recommandation)

### Solution 1 : PostgreSQL Direct avec IP Whitelistée (RECOMMANDÉE)

**Principe :** Exposer PostgreSQL OVH uniquement pour l'IP du VPS Hostinger avec SSL obligatoire

#### Avantages
- ✅ Pas de tunnel à gérer
- ✅ Performance directe
- ✅ Simple à maintenir
- ✅ SSL chiffré
- ✅ Firewall limitant l'accès à 1 seule IP

#### Sécurité
```
Firewall OVH → Autoriser 69.62.110.207:* → 51.255.201.205:5432
PostgreSQL → SSL obligatoire (hostssl)
PostgreSQL → User dédié avec permissions limitées
```

#### Configuration

##### 1. Sur VPS OVH - Configurer PostgreSQL

```bash
# Se connecter au VPS OVH
ssh root@51.255.201.205

# Modifier pg_hba.conf pour autoriser VPS Hostinger avec SSL
docker exec h48w8cwscggoo0s4ws8s4gws sh -c "cat >> /var/lib/postgresql/data/pg_hba.conf << 'EOF'
# NocoDB VPS Hostinger - SSL obligatoire
hostssl calocalc_inscription calocalc_user 69.62.110.207/32 scram-sha-256
EOF"

# Modifier postgresql.conf pour écouter sur toutes les interfaces
docker exec h48w8cwscggoo0s4ws8s4gws sh -c \
  "sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/\" /var/lib/postgresql/data/postgresql.conf"

# Activer SSL
docker exec h48w8cwscggoo0s4ws8s4gws sh -c \
  "sed -i 's/#ssl = off/ssl = on/' /var/lib/postgresql/data/postgresql.conf"

# Recharger PostgreSQL
docker exec h48w8cwscggoo0s4ws8s4gws psql -U postgres -c "SELECT pg_reload_conf();"

# Vérifier que PostgreSQL écoute
docker exec h48w8cwscggoo0s4ws8s4gws netstat -tlnp | grep 5432
```

##### 2. Configurer le Firewall OVH

**Option A : Via interface web OVH**
1. Se connecter sur https://www.ovh.com/manager/
2. Dédié → Serveurs dédiés → Votre serveur
3. Network Firewall → Ajouter une règle
4. Autoriser TCP port 5432 depuis 69.62.110.207

**Option B : Via iptables (si pas de firewall OVH activé)**
```bash
# Autoriser uniquement VPS Hostinger
iptables -I INPUT -p tcp --dport 5432 -s 69.62.110.207 -j ACCEPT
iptables -A INPUT -p tcp --dport 5432 -j DROP

# Sauvegarder
iptables-save > /etc/iptables/rules.v4
```

##### 3. Tester depuis VPS Hostinger

```bash
# Test connexion depuis VPS Hostinger
ssh root@69.62.110.207

# Test 1 : Port accessible
nc -zv 51.255.201.205 5432

# Test 2 : Connexion PostgreSQL (sans SSL d'abord)
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@51.255.201.205:5432/calocalc_inscription?sslmode=disable' \
  -c 'SELECT COUNT(*) FROM users;'

# Test 3 : Connexion PostgreSQL avec SSL
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@51.255.201.205:5432/calocalc_inscription?sslmode=require' \
  -c 'SELECT COUNT(*) FROM users;'
```

##### 4. Configurer dans NocoDB

```
Type: PostgreSQL
Host: 51.255.201.205
Port: 5432
Database: calocalc_inscription
Username: calocalc_user
Password: CaloCalc2024

Connection parameters:
+ Add parameter:
  Key: sslmode
  Value: require
```

#### ⚠️ Considérations Sécurité

**Risques :**
- Port PostgreSQL exposé sur Internet (même si limité à 1 IP)
- Cible potentielle de scan/attaque DDoS

**Mitigations :**
- ✅ Firewall : SEULE l'IP 69.62.110.207 autorisée
- ✅ SSL obligatoire (chiffrement)
- ✅ User dédié avec permissions limitées (pas de DROP/CREATE DATABASE)
- ✅ Mot de passe fort
- ✅ fail2ban pour bloquer tentatives de brute-force (optionnel)

**Alternative plus sûre :** Utiliser un VPN WireGuard entre les 2 VPS (voir Solution 3)

---

### Solution 2 : NocoDB en network_mode: host + Traefik Reconfiguration

**Principe :** Sortir NocoDB du réseau Docker pour qu'il accède au tunnel SSH local

#### Configuration

```bash
# 1. Modifier docker-compose NocoDB
ssh root@69.62.110.207
cd /data/coolify/services/hgcocsgs8gk44sgo04w04ckk

# Backup
cp docker-compose.yml docker-compose.yml.backup

# Modifier
cat > docker-compose-host.yml << 'EOF'
services:
  nocodb:
    image: nocodb/nocodb
    network_mode: host
    environment:
      PORT: 8081  # Changer le port pour éviter conflit
      SERVICE_URL_NOCODB_8081: 'https://nocodb.agnisolution.fr'
      NC_ALLOW_LOCAL_HOOKS: 'true'
      NC_ALLOW_LOCAL_EXTERNAL_DBS: 'true'
    volumes:
      - 'hgcocsgs8gk44sgo04w04ckk_nocodb-data:/usr/app/data/'
    restart: unless-stopped
    labels:
      - traefik.enable=true
      - traefik.http.services.nocodb.loadbalancer.server.port=8081
      - traefik.http.routers.nocodb-https.rule=Host(`nocodb.agnisolution.fr`)
      - traefik.http.routers.nocodb-https.entrypoints=https
      - traefik.http.routers.nocodb-https.tls.certresolver=letsencrypt
    env_file:
      - .env

volumes:
  hgcocsgs8gk44sgo04w04ckk_nocodb-data:
    name: hgcocsgs8gk44sgo04w04ckk_nocodb-data
    external: true
EOF

# Appliquer
docker compose -f docker-compose-host.yml up -d
```

#### Dans NocoDB
```
Host: 127.0.0.1 (ou 10.0.1.1)
Port: 5433
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
```

#### Problèmes
- ⚠️ Perd l'isolation réseau Docker
- ⚠️ Configuration Traefik plus complexe
- ⚠️ Conflit potentiel avec d'autres services

---

### Solution 3 : VPN WireGuard entre VPS (LA PLUS SÛRE)

**Principe :** Créer un tunnel VPN chiffré entre VPS Hostinger ↔ VPS OVH

#### Avantages
- ✅ Sécurité maximale (tunnel chiffré)
- ✅ Pas d'exposition Internet
- ✅ Réseau privé entre les 2 VPS
- ✅ Utilisable pour d'autres services

#### Architecture
```
VPS Hostinger (10.8.0.1)
    |
    | WireGuard VPN (chiffré)
    |
VPS OVH (10.8.0.2)
    |
    └─> PostgreSQL accessible sur 10.8.0.2:5432
```

#### Configuration (rapide avec script)

```bash
# Sur VPS OVH
curl -O https://raw.githubusercontent.com/angristan/wireguard-install/master/wireguard-install.sh
chmod +x wireguard-install.sh
./wireguard-install.sh
# Créer client "hostinger"
# Copier le fichier .conf généré

# Sur VPS Hostinger
apt install wireguard
# Copier le client.conf
wg-quick up wg0

# Tester
ping 10.8.0.2
```

#### Dans NocoDB
```
Host: 10.8.0.2 (IP VPN du VPS OVH)
Port: 5432
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
```

**Temps d'installation :** ~30min  
**Sécurité :** ⭐⭐⭐⭐⭐ Maximum

---

## 📊 COMPARAISON DES SOLUTIONS

| Solution | Complexité | Sécurité | Performance | Maintenance |
|----------|------------|----------|-------------|-------------|
| **1. IP Whitelistée + SSL** | ⭐⭐ Faible | ⭐⭐⭐ Bonne | ⭐⭐⭐⭐⭐ Excellente | ⭐⭐⭐⭐ Facile |
| **2. network_mode: host** | ⭐⭐⭐ Moyenne | ⭐⭐⭐⭐ Très bonne | ⭐⭐⭐⭐ Bonne | ⭐⭐⭐ Moyenne |
| **3. VPN WireGuard** | ⭐⭐⭐⭐ Élevée | ⭐⭐⭐⭐⭐ Maximale | ⭐⭐⭐⭐ Bonne | ⭐⭐⭐ Moyenne |

## 🎯 RECOMMANDATION FINALE

**Pour démarrer rapidement :** Solution 1 (IP Whitelistée + SSL)
- Rapide à mettre en place (30min)
- Sécurité suffisante pour données non ultra-sensibles
- Facile à débugger

**Pour production sensible :** Solution 3 (VPN WireGuard)
- Sécurité maximale
- Réutilisable pour autres flux
- Standard industriel

**À éviter :** Solution 2 (network_mode: host)
- Trop de contraintes avec Coolify/Traefik
- Moins flexible

## 🚀 PLAN D'ACTION PROPOSÉ

### Phase 1 : Solution 1 (Immédiat)
1. Configurer PostgreSQL OVH pour accepter IP Hostinger (15min)
2. Configurer firewall OVH (10min)
3. Tester connexion depuis Hostinger (5min)
4. Reconfigurer NocoDB (5min)
5. Valider que CaloCalc affiche les données ✅

**Total : 35min**

### Phase 2 : Solution 3 (Optionnel, plus tard)
1. Installer WireGuard sur les 2 VPS
2. Migrer la connexion PostgreSQL vers le VPN
3. Fermer le port 5432 sur le firewall OVH
4. Documentation

**Total : 1h**

---

**Document créé :** 15 mai 2026  
**Contexte :** CaloCalc doit rester sur VPS OVH (performance + proximité code)  
**Objectif :** Connexion sécurisée NocoDB (Hostinger) → PostgreSQL (OVH)
