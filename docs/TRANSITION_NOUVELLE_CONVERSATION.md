# 🔄 Transition Nouvelle Conversation - NocoDB CaloCalc

**Date :** 15 mai 2026 - 17h15  
**Contexte :** Debug NocoDB - Connexion PostgreSQL VPS OVH

---

## 📍 OÙ ON EN EST

### ✅ RÉSOLU
- **OPEPARTNER** : Base locale connectée et fonctionnelle
  - Container : `pk4s888o4wkc8ogokg0sg840`
  - IP : `10.0.1.23`
  - 14 tables visibles dans NocoDB

### ❌ À RÉSOUDRE
- **CaloCalc** : Base VPS OVH inaccessible depuis NocoDB
  - Erreur : 0 records affichés (KnexTimeoutError)
  - Problème : Tunnel SSH inaccessible depuis containers Docker

---

## 🎯 DÉCISION PRISE

**CaloCalc RESTE sur VPS OVH** (51.255.201.205)
- Raison : VPS plus puissant + code applications déjà là-bas
- Solution choisie : **IP Whitelistée + SSL** (Solution 1)

---

## 📚 DOCUMENTS À LIRE (dans l'ordre)

1. **`NOCODB_ETAT_FINAL_15MAI2026.md`**  
   → État complet du système, tous les tests effectués

2. **`NOCODB_SOLUTION_TUNNEL_OVH.md`**  
   → 3 solutions détaillées pour connecter NocoDB → PostgreSQL OVH  
   → Solution 1 recommandée (IP Whitelistée + SSL)

3. **`NOCODB_QUICK_RESUME.md`**  
   → Solution SSRF (NC_ALLOW_LOCAL_EXTERNAL_DBS=true) déjà appliquée

---

## 🚀 PROCHAINE ÉTAPE : Solution 1 (30min)

### Configuration à faire

```bash
# 1. Sur VPS OVH - Autoriser IP Hostinger
ssh root@51.255.201.205
docker exec h48w8cwscggoo0s4ws8s4gws sh -c "cat >> /var/lib/postgresql/data/pg_hba.conf << 'EOF'
hostssl calocalc_inscription calocalc_user 69.62.110.207/32 scram-sha-256
EOF"

# 2. PostgreSQL écoute sur toutes interfaces
docker exec h48w8cwscggoo0s4ws8s4gws sh -c \
  "sed -i \"s/#listen_addresses = 'localhost'/listen_addresses = '*'/\" /var/lib/postgresql/data/postgresql.conf"

# 3. Activer SSL
docker exec h48w8cwscggoo0s4ws8s4gws sh -c \
  "sed -i 's/#ssl = off/ssl = on/' /var/lib/postgresql/data/postgresql.conf"

# 4. Recharger config
docker exec h48w8cwscggoo0s4ws8s4gws psql -U postgres -c "SELECT pg_reload_conf();"

# 5. Configurer firewall OVH pour autoriser 69.62.110.207 → port 5432

# 6. Tester depuis VPS Hostinger
ssh root@69.62.110.207
docker run --rm --network coolify postgres:17-alpine \
  psql 'postgresql://calocalc_user:CaloCalc2024@51.255.201.205:5432/calocalc_inscription?sslmode=require' \
  -c 'SELECT COUNT(*) FROM users;'

# 7. Dans NocoDB : Modifier connexion CaloCalc
Host: 51.255.201.205
Port: 5432
Database: calocalc_inscription
User: calocalc_user
Password: CaloCalc2024
SSL: require
```

---

## 📋 INFOS TECHNIQUES ESSENTIELLES

### VPS OVH (PostgreSQL CaloCalc)
- **IP :** 51.255.201.205
- **Container :** h48w8cwscggoo0s4ws8s4gws
- **Base :** calocalc_inscription
- **User :** calocalc_user
- **Password :** CaloCalc2024

### VPS Hostinger (NocoDB)
- **IP :** 69.62.110.207
- **Container NocoDB :** nocodb-hgcocsgs8gk44sgo04w04ckk
- **Container PostgreSQL local :** pk4s888o4wkc8ogokg0sg840 (IP: 10.0.1.23)
- **Variable d'env :** NC_ALLOW_LOCAL_EXTERNAL_DBS=true ✅

### Tunnel SSH (actuellement utilisé mais non fonctionnel depuis Docker)
```bash
# Processus actif sur VPS Hostinger
autossh -L 0.0.0.0:5433:10.0.1.7:5432 root@51.255.201.205
# Accessible depuis hôte uniquement, pas depuis containers Docker
```

---

## ⚠️ POINTS D'ATTENTION

1. **Firewall OVH** : Vérifier qu'il autorise bien 69.62.110.207 → 5432
2. **SSL** : Doit être activé dans postgresql.conf et pg_hba.conf (hostssl)
3. **Connection parameters dans NocoDB** : Ajouter `sslmode=require`
4. **Test avant NocoDB** : Toujours tester avec psql depuis VPS Hostinger d'abord

---

## 🎬 PROMPT POUR NOUVELLE CONVERSATION

```
Bonjour, je continue le debug NocoDB pour connecter la base CaloCalc 
(VPS OVH) à NocoDB (VPS Hostinger).

Contexte :
- OPEPARTNER (base locale) fonctionne ✅
- CaloCalc (VPS OVH via tunnel SSH) affiche 0 records ❌
- NC_ALLOW_LOCAL_EXTERNAL_DBS=true déjà configuré ✅

Décision prise : Garder CaloCalc sur VPS OVH (plus puissant)

Prochaine étape : Implémenter Solution 1 (IP Whitelistée + SSL)

Documents de référence dans docs/ :
- NOCODB_ETAT_FINAL_15MAI2026.md
- NOCODB_SOLUTION_TUNNEL_OVH.md
- TRANSITION_NOUVELLE_CONVERSATION.md

Peux-tu lire NOCODB_SOLUTION_TUNNEL_OVH.md et me guider pour 
appliquer la Solution 1 étape par étape ?
```

---

## 📊 STATISTIQUES SESSION

- **Durée :** 2h45 (14h30-17h15)
- **Tokens utilisés :** ~89k/200k
- **Tests effectués :** 20+
- **Documents créés :** 3
- **Problèmes résolus :** 1/2 (OPEPARTNER ✅, CaloCalc ⏳)

---

**Prêt pour nouvelle conversation** ✅  
**Objectif :** Connecter CaloCalc en 30min avec Solution 1
