# Guide Installation WireGuard - VPS OVH ↔ VPS Hostinger

**Date :** 15 mai 2026  
**Objectif :** Connexion sécurisée NocoDB (Hostinger) → PostgreSQL CaloCalc (OVH)  
**Sécurité :** Maximale (tunnel chiffré, 0 exposition Internet)

---

## 🎯 Architecture Réseau

```
VPS Hostinger (69.62.110.207)                 VPS OVH (51.255.201.205)
├─ IP WireGuard : 10.8.0.1                    ├─ IP WireGuard : 10.8.0.2
├─ NocoDB (container)                         ├─ PostgreSQL CaloCalc
│   └─> Se connecte à 10.8.0.2:5432           │   └─> Écoute sur 10.8.0.2:5432
│       (via VPN chiffré)                     │       (interface wg0 uniquement)
└─ WireGuard client                           └─ WireGuard serveur
```

**Principe de sécurité :**
- PostgreSQL n'écoute QUE sur l'interface WireGuard (10.8.0.2)
- Port 5432 JAMAIS exposé sur Internet
- Tunnel chiffré avec clés cryptographiques modernes
- Seul le VPS Hostinger peut se connecter

---

## 📋 ÉTAPE 1 : Installation WireGuard sur VPS OVH (Serveur)

### 1.1 Connexion au VPS OVH
```bash
ssh root@51.255.201.205
```

### 1.2 Installation WireGuard

**Pour Ubuntu/Debian :**
```bash
apt update
apt install wireguard wireguard-tools -y
```

**Pour CentOS/Rocky Linux :**
```bash
yum install epel-release elrepo-release -y
yum install kmod-wireguard wireguard-tools -y
```

### 1.3 Activation du routage IP (si nécessaire)
```bash
# Vérifier si déjà activé
sysctl net.ipv4.ip_forward

# Si retourne 0, activer :
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p
```

### 1.4 Génération des clés serveur
```bash
cd /etc/wireguard
umask 077
wg genkey | tee server_private.key | wg pubkey > server_public.key
```

### 1.5 Configuration du serveur WireGuard
```bash
cat > /etc/wireguard/wg0.conf << 'EOF'
[Interface]
# IP du serveur dans le VPN
Address = 10.8.0.2/24

# Port d'écoute WireGuard (UDP)
ListenPort = 51820

# Clé privée du serveur (à remplacer)
PrivateKey = SERA_REMPLI_AUTOMATIQUEMENT

# Configuration réseau
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
# VPS Hostinger (client)
PublicKey = CLE_PUBLIQUE_CLIENT_SERA_AJOUTEE_PLUS_TARD

# IP autorisée dans le VPN
AllowedIPs = 10.8.0.1/32

# Maintenir la connexion active
PersistentKeepalive = 25
EOF
```

### 1.6 Injecter la clé privée dans la config
```bash
PRIVATE_KEY=$(cat /etc/wireguard/server_private.key)
sed -i "s|PrivateKey = SERA_REMPLI_AUTOMATIQUEMENT|PrivateKey = $PRIVATE_KEY|" /etc/wireguard/wg0.conf
```

### 1.7 Sécuriser les permissions
```bash
chmod 600 /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/*.key
```

### 1.8 Afficher la clé publique du serveur (à copier pour plus tard)
```bash
cat /etc/wireguard/server_public.key
```
**⚠️ NOTER CETTE CLÉ**, elle sera nécessaire pour configurer le client.

---

## 📋 ÉTAPE 2 : Configuration Firewall sur VPS OVH

### 2.1 Ouvrir le port WireGuard (UDP 51820)

**Option A : Firewall OVH (via interface web)**
1. Se connecter sur https://www.ovh.com/manager/
2. Dédié → Serveurs dédiés → Votre serveur
3. Network Firewall → Ajouter une règle
4. Autoriser UDP port 51820 depuis 69.62.110.207 (VPS Hostinger)

**Option B : iptables (si pas de firewall OVH)**
```bash
# Autoriser WireGuard uniquement depuis VPS Hostinger
iptables -I INPUT -p udp --dport 51820 -s 69.62.110.207 -j ACCEPT

# Sauvegarder
apt install iptables-persistent -y
iptables-save > /etc/iptables/rules.v4
```

### 2.2 Vérifier que le port 5432 PostgreSQL est FERMÉ sur Internet
```bash
# Le port 5432 ne doit PAS être ouvert sur Internet
iptables -L INPUT -n | grep 5432

# Si ouvert, le bloquer :
iptables -A INPUT -p tcp --dport 5432 -j DROP
iptables-save > /etc/iptables/rules.v4
```

---

## 📋 ÉTAPE 3 : Installation WireGuard sur VPS Hostinger (Client)

### 3.1 Connexion au VPS Hostinger
```bash
ssh root@69.62.110.207
```

### 3.2 Installation WireGuard
```bash
apt update
apt install wireguard wireguard-tools -y
```

### 3.3 Génération des clés client
```bash
cd /etc/wireguard
umask 077
wg genkey | tee client_private.key | wg pubkey > client_public.key
```

### 3.4 Afficher la clé publique du client
```bash
cat /etc/wireguard/client_public.key
```
**⚠️ NOTER CETTE CLÉ**, elle sera ajoutée dans la config du serveur.

### 3.5 Configuration du client WireGuard
```bash
cat > /etc/wireguard/wg0.conf << 'EOF'
[Interface]
# IP du client dans le VPN
Address = 10.8.0.1/24

# Clé privée du client (à remplacer)
PrivateKey = SERA_REMPLI_AUTOMATIQUEMENT

# DNS optionnel (pour résolution de noms dans le VPN)
# DNS = 10.8.0.2

[Peer]
# VPS OVH (serveur)
PublicKey = CLE_PUBLIQUE_SERVEUR_A_REMPLACER

# IP publique et port du serveur WireGuard
Endpoint = 51.255.201.205:51820

# Uniquement router le trafic vers 10.8.0.0/24 via le VPN
# (pas de AllowedIPs = 0.0.0.0/0 pour ne pas router tout le trafic)
AllowedIPs = 10.8.0.0/24

# Maintenir la connexion active
PersistentKeepalive = 25
EOF
```

### 3.6 Injecter la clé privée client
```bash
PRIVATE_KEY=$(cat /etc/wireguard/client_private.key)
sed -i "s|PrivateKey = SERA_REMPLI_AUTOMATIQUEMENT|PrivateKey = $PRIVATE_KEY|" /etc/wireguard/wg0.conf
```

### 3.7 Sécuriser les permissions
```bash
chmod 600 /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/*.key
```

---

## 📋 ÉTAPE 4 : Finalisation de la Configuration

### 4.1 Ajouter la clé publique du client dans le serveur

**Sur VPS OVH :**
```bash
# Récupérer la clé publique du client (copiée depuis VPS Hostinger)
CLIENT_PUBLIC_KEY="<coller_ici_la_cle_publique_client>"

# Remplacer dans la config
sed -i "s|PublicKey = CLE_PUBLIQUE_CLIENT_SERA_AJOUTEE_PLUS_TARD|PublicKey = $CLIENT_PUBLIC_KEY|" /etc/wireguard/wg0.conf
```

### 4.2 Ajouter la clé publique du serveur dans le client

**Sur VPS Hostinger :**
```bash
# Récupérer la clé publique du serveur (copiée depuis VPS OVH)
SERVER_PUBLIC_KEY="<coller_ici_la_cle_publique_serveur>"

# Remplacer dans la config
sed -i "s|PublicKey = CLE_PUBLIQUE_SERVEUR_A_REMPLACER|PublicKey = $SERVER_PUBLIC_KEY|" /etc/wireguard/wg0.conf
```

---

## 📋 ÉTAPE 5 : Démarrage WireGuard

### 5.1 Démarrer le serveur WireGuard (VPS OVH)
```bash
ssh root@51.255.201.205

# Démarrer l'interface WireGuard
wg-quick up wg0

# Vérifier le statut
wg show

# Activer au démarrage
systemctl enable wg-quick@wg0
```

**Sortie attendue :**
```
interface: wg0
  public key: <clé publique serveur>
  private key: (hidden)
  listening port: 51820

peer: <clé publique client>
  allowed ips: 10.8.0.1/32
```

### 5.2 Démarrer le client WireGuard (VPS Hostinger)
```bash
ssh root@69.62.110.207

# Démarrer l'interface WireGuard
wg-quick up wg0

# Vérifier le statut
wg show

# Activer au démarrage
systemctl enable wg-quick@wg0
```

**Sortie attendue :**
```
interface: wg0
  public key: <clé publique client>
  private key: (hidden)
  listening port: <aléatoire>

peer: <clé publique serveur>
  endpoint: 51.255.201.205:51820
  allowed ips: 10.8.0.0/24
  latest handshake: X seconds ago
  transfer: Y B received, Z B sent
```

---

## 📋 ÉTAPE 6 : Tests de Connectivité

### 6.1 Ping depuis VPS Hostinger vers VPS OVH
```bash
ssh root@69.62.110.207

# Ping l'IP WireGuard du serveur
ping -c 4 10.8.0.2
```

**Résultat attendu :**
```
PING 10.8.0.2 (10.8.0.2) 56(84) bytes of data.
64 bytes from 10.8.0.2: icmp_seq=1 ttl=64 time=5.23 ms
64 bytes from 10.8.0.2: icmp_seq=2 ttl=64 time=4.87 ms
```

### 6.2 Ping depuis VPS OVH vers VPS Hostinger
```bash
ssh root@51.255.201.205

# Ping l'IP WireGuard du client
ping -c 4 10.8.0.1
```

### 6.3 Vérifier que les interfaces existent
```bash
# Sur les 2 VPS
ip addr show wg0
```

**Résultat attendu (VPS OVH) :**
```
wg0: <POINTOPOINT,NOARP,UP,LOWER_UP>
    inet 10.8.0.2/24 scope global wg0
```

**Résultat attendu (VPS Hostinger) :**
```
wg0: <POINTOPOINT,NOARP,UP,LOWER_UP>
    inet 10.8.0.1/24 scope global wg0
```

---

## 📋 ÉTAPE 7 : Configuration PostgreSQL pour WireGuard

### 7.1 Configurer PostgreSQL pour écouter sur l'interface WireGuard

**Sur VPS OVH :**
```bash
# Modifier postgresql.conf pour écouter sur l'IP WireGuard
docker exec h48w8cwscggoo0s4ws8s4gws sh -c \
  "sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '10.8.0.2'/\" /var/lib/postgresql/data/postgresql.conf"

# Ajouter règle dans pg_hba.conf pour autoriser VPS Hostinger
docker exec h48w8cwscggoo0s4ws8s4gws sh -c "cat >> /var/lib/postgresql/data/pg_hba.conf << 'EOF'
# VPS Hostinger via WireGuard VPN
host calocalc_inscription calocalc_user 10.8.0.1/32 scram-sha-256
EOF"

# Recharger la configuration PostgreSQL
docker exec h48w8cwscggoo0s4ws8s4gws psql -U postgres -c "SELECT pg_reload_conf();"
```

### 7.2 Exposer le port PostgreSQL du container sur l'interface WireGuard

**Problème :** Le container PostgreSQL écoute sur `0.0.0.0:5432` à l'intérieur, mais il faut le rendre accessible depuis l'IP WireGuard de l'hôte.

**Solution 1 : Publier le port sur l'IP WireGuard**
```bash
# Vérifier le docker-compose du container PostgreSQL
docker inspect h48w8cwscggoo0s4ws8s4gws | grep -A 10 "NetworkSettings"

# Si le port 5432 n'est pas publié, il faut modifier le docker-compose
# Trouver le docker-compose du container PostgreSQL
find /data -name docker-compose.yml -exec grep -l "h48w8cwscggoo0s4ws8s4gws" {} \;

# Ajouter dans le docker-compose :
ports:
  - "10.8.0.2:5432:5432"
  # Ou si pas possible de modifier, utiliser iptables :
```

**Solution 2 : Redirection iptables (si modification docker-compose impossible)**
```bash
# Sur VPS OVH
# Rediriger trafic depuis wg0:5432 vers le container
CONTAINER_IP=$(docker inspect h48w8cwscggoo0s4ws8s4gws | grep -m1 '"IPAddress"' | awk -F'"' '{print $4}')

iptables -t nat -A PREROUTING -i wg0 -p tcp --dport 5432 -j DNAT --to-destination $CONTAINER_IP:5432
iptables -A FORWARD -i wg0 -p tcp -d $CONTAINER_IP --dport 5432 -j ACCEPT

# Sauvegarder
iptables-save > /etc/iptables/rules.v4
```

### 7.3 Tester la connexion PostgreSQL via WireGuard

**Depuis VPS Hostinger :**
```bash
# Test 1 : Port accessible
nc -zv 10.8.0.2 5432

# Test 2 : Connexion PostgreSQL
docker run --rm --network host postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@10.8.0.2:5432/calocalc_inscription' \
  -c 'SELECT COUNT(*) FROM users;'
```

**Résultat attendu :**
```
 count 
-------
    18
(1 row)
```

---

## 📋 ÉTAPE 8 : Configuration NocoDB

### 8.1 Modifier la connexion CaloCalc dans NocoDB

**Interface NocoDB :**
1. Ouvrir https://nocodb.agnisolution.fr
2. Aller dans la base "CaloCalc"
3. Settings → Database
4. Modifier la connexion externe :

```
Type: PostgreSQL
Host: 10.8.0.2        ← IP WireGuard du VPS OVH
Port: 5432
Database: calocalc_inscription
Username: calocalc_user
Password: CaloCalc2024
Schema: public

SSL: Disabled (car tunnel déjà chiffré par WireGuard)
```

### 8.2 Tester la connexion
Cliquer sur "Test Database Connection"

**Résultat attendu :** ✅ Connection successful

### 8.3 Valider les données
- Ouvrir une table (ex: `users`)
- Vérifier que les données s'affichent
- Vérifier le compteur de lignes

---

## 📋 ÉTAPE 9 : Validation Finale

### 9.1 Checklist de sécurité

- [ ] WireGuard fonctionne sur les 2 VPS (`wg show` affiche un handshake récent)
- [ ] Ping `10.8.0.1 ↔ 10.8.0.2` fonctionne
- [ ] PostgreSQL écoute UNIQUEMENT sur `10.8.0.2` (pas sur Internet)
- [ ] Port 5432 est FERMÉ sur Internet (test avec `nc -zv 51.255.201.205 5432` depuis externe → doit échouer)
- [ ] Port 51820 (WireGuard) autorise UNIQUEMENT `69.62.110.207`
- [ ] NocoDB affiche les données de CaloCalc ✅
- [ ] Connexion PostgreSQL fonctionne depuis VPS Hostinger via `10.8.0.2:5432`

### 9.2 Test de sécurité finale

**Depuis un 3ème serveur ou depuis ton Mac local (IP différente de 69.62.110.207) :**
```bash
# Test 1 : Port WireGuard doit être inaccessible
nc -zv 51.255.201.205 51820
# Résultat attendu : Connection refused ou timeout

# Test 2 : Port PostgreSQL doit être inaccessible
nc -zv 51.255.201.205 5432
# Résultat attendu : Connection refused ou timeout
```

### 9.3 Nettoyage du tunnel SSH (optionnel)

**Sur VPS Hostinger :**
```bash
# Stopper le tunnel SSH devenu inutile
pkill autossh

# Supprimer le cron si configuré
crontab -e
# Retirer la ligne avec autossh
```

---

## 🛠️ Maintenance et Monitoring

### Commandes utiles

**Vérifier le statut WireGuard :**
```bash
wg show
```

**Voir les logs :**
```bash
journalctl -u wg-quick@wg0 -f
```

**Redémarrer WireGuard :**
```bash
wg-quick down wg0
wg-quick up wg0
```

**Vérifier la latence :**
```bash
ping -c 10 10.8.0.2
```

### En cas de problème

**Symptôme :** Pas de handshake
```bash
# Vérifier les clés publiques dans les configs
cat /etc/wireguard/wg0.conf

# Vérifier les logs
journalctl -u wg-quick@wg0 --no-pager -n 50

# Vérifier le firewall
iptables -L -n | grep 51820
```

**Symptôme :** Handshake OK mais pas de ping
```bash
# Vérifier le routage IP
sysctl net.ipv4.ip_forward

# Vérifier les routes
ip route show

# Vérifier iptables FORWARD
iptables -L FORWARD -n -v
```

---

## 📊 Comparaison Avant/Après

### Avant (Tunnel SSH)
```
VPS Hostinger → Tunnel SSH (127.0.0.1:5433) → VPS OVH
❌ Inaccessible depuis containers Docker
❌ Pas de chiffrement bout-en-bout
❌ Fragile (autossh peut crasher)
```

### Après (WireGuard)
```
VPS Hostinger → WireGuard VPN (10.8.0.2:5432) → VPS OVH
✅ Accessible depuis tous les containers (IP routée)
✅ Chiffrement moderne (ChaCha20-Poly1305)
✅ Stable, auto-reconnexion, performant
✅ 0 exposition Internet
```

---

## 🎯 Résumé

**Temps d'installation :** ~30-45 minutes  
**Sécurité :** ⭐⭐⭐⭐⭐ Maximale  
**Performance :** ~5-10ms de latence ajoutée (négligeable)  
**Maintenance :** Aucune (auto-reconnexion)  

**Bénéfices :**
- PostgreSQL jamais exposé sur Internet
- Tunnel chiffré avec cryptographie moderne
- Réutilisable pour d'autres services (n8n, backups, etc.)
- Standard industriel (utilisé par entreprises et VPN commerciaux)

---

**Document créé :** 15 mai 2026  
**Auteur :** Claude Code  
**Projet :** OPEPARTNER Stack - Connexion sécurisée NocoDB ↔ PostgreSQL CaloCalc
