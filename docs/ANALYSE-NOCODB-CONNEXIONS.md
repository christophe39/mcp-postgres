# Analyse complète : Problème connexions NocoDB PostgreSQL
**Date** : 2026-05-19  
**Contexte** : Perte de connexion de TOUTES les bases PostgreSQL dans NocoDB

---

## 🏗️ Infrastructure découverte

### VPS Hostinger (69.62.110.207) - Serveur NocoDB

#### Container Postgres `pk4s888o4wkc8ogokg0sg840`
- **Image** : `postgres:17-alpine`
- **IP interne** : `10.0.1.23` (réseau Docker `coolify`)
- **Bases** :
  - `opepartner` (user: `nocodb_opepartner`)
  - `excalidraw_storage` (user: `excalidraw_backend`)
  - `calocalc_inscription` (user: `calocalc_user`) ⚠️ COPIE locale
  - `calocalc_prospection` (user: `calocalc_user`)

#### Container Postgres `c0408wgcs08kc0w480koowcs`
- **Image** : ancienne (3d877cc09383)
- **User admin** : `agni_admin`
- **Bases** :
  - `Base_AgniConsult` (probable)
  - `db_agni` (probable)
  - `calocalc_inscription` (ancienne, à vérifier)
  - `nocodb_db`

#### Tunnel SSH actif (autossh)
```bash
autossh -L 0.0.0.0:5433:10.0.1.7:5432 root@51.255.201.205
```
- **Port local** : 5433
- **Destination** : VPS OVH, IP interne 10.0.1.7, port 5432
- **Status** : ✅ ACTIF (PID 3432798)

---

### VPS OVH (51.255.201.205) - Serveur CaloCalc

#### Container Postgres `h48w8cwscggoo0s4ws8s4gws`
- **Image** : `postgres:17-alpine`
- **IP interne** : `10.0.1.7` (réseau Docker OVH)
- **Bases** :
  - `calocalc_inscription` (user: `calocalc_user`) ⚠️ BASE PRINCIPALE
  - `calocalc_docmost`
  - `calocalc_help`

**Accès depuis Hostinger** : via tunnel SSH sur `localhost:5433`

---

## 📊 État des 8 data sources PostgreSQL dans NocoDB

| # | Alias | Base cible | Host actuel | Port | User | Problème |
|---|-------|------------|-------------|------|------|----------|
| 1 | `Base_AgniConsult` | `Base_AgniConsult` | ❌ MANQUANT | - | - | Config incomplète |
| 2 | `Calocalc` | `calocalc_inscription` | ❌ MANQUANT | - | - | Config incomplète |
| 3 | `Calocalc_inscription` | `calocalc_inscription` | `pk4s888o4wkc8ogokg0sg840` | 5432 | `postgres` | ⚠️ Hostname bloqué |
| 4 | `Calocalc_native` | `postgres` | `pk4s888o4wkc8ogokg0sg840` | 5432 | `postgres` | ⚠️ Hostname bloqué |
| 5 | `calocalc_prospection` | `calocalc_prospection` | `pk4s888o4wkc8ogokg0sg840` | 5432 | `calocalc_user` | ⚠️ Hostname bloqué |
| 6 | `db_agni` | `db_agni` | `pk4s888o4wkc8ogokg0sg840` | 5432 | `postgres` | ⚠️ Hostname bloqué |
| 7 | `excalidraw` | `excalidraw_storage` | `pk4s888o4wkc8ogokg0sg840` | 5432 | `excalidraw_backend` | ⚠️ Hostname bloqué |
| 8 | `opepartnerv2` | `opepartner` | `pk4s888o4wkc8ogokg0sg840` | 5432 | `nocodb_opepartner` | ⚠️ Hostname bloqué |

---

## 🔍 Problèmes identifiés

### Problème 1 : Hostname Docker bloqué (6 sources)
**Erreur NocoDB** : "Forbidden host name or IP address"

**Cause** : NocoDB v0.301.5 bloque les hostnames Docker locaux (`pk4s888o4wkc8ogokg0sg840`) par sécurité.

**Sources affectées** :
- Calocalc_inscription
- Calocalc_native
- calocalc_prospection
- db_agni
- excalidraw
- opepartnerv2

### Problème 2 : Configs incomplètes (2 sources)
**Sources** :
- `Base_AgniConsult` : manque host, user, password
- `Calocalc` : manque host, user, password

### Problème 3 : Base CaloCalc dupliquée
Il existe **DEUX bases `calocalc_inscription`** :
1. **Sur OVH** (via tunnel port 5433) - BASE PRINCIPALE avec les vraies données
2. **Sur Hostinger** (dans pk4s888o4wkc8ogokg0sg840) - COPIE locale (à vérifier si à jour)

**Question** : Quelle base NocoDB doit-il utiliser ?

---

## 💡 Solutions proposées

### Option A : Tout migrer sur Hostinger (SIMPLE)
**Principe** : Utiliser uniquement les bases locales sur Hostinger (IP `10.0.1.23`)

**Avantages** :
- ✅ Pas de tunnel nécessaire
- ✅ Connexions directes rapides
- ✅ Tout sur un seul VPS

**Inconvénients** :
- ⚠️ Nécessite migration/sync des données CaloCalc depuis OVH
- ⚠️ Perte du cloisonnement OVH/Hostinger

**Actions** :
```sql
-- Remplacer tous les hostnames par IP locale
UPDATE nc_sources_v2
SET config = json_replace(config, '$.connection.host', '10.0.1.23')
WHERE json_extract(config, '$.connection.host') = 'pk4s888o4wkc8ogokg0sg840';
```

---

### Option B : Tunnel SSH pour CaloCalc, local pour le reste (HYBRIDE)
**Principe** : 
- CaloCalc reste sur OVH (via tunnel port 5433)
- OPEPARTNER, Excalidraw, db_agni sur Hostinger (IP locale)

**Avantages** :
- ✅ Garde le cloisonnement OVH/Hostinger
- ✅ CaloCalc reste sur son VPS dédié
- ✅ OPEPARTNER isolé sur Hostinger

**Actions** :
```sql
-- 1. Bases locales Hostinger → IP 10.0.1.23
UPDATE nc_sources_v2
SET config = json_replace(config, '$.connection.host', '10.0.1.23')
WHERE alias IN ('opepartnerv2', 'excalidraw', 'db_agni', 'calocalc_prospection');

-- 2. Bases CaloCalc sur OVH → localhost:5433 (tunnel)
UPDATE nc_sources_v2
SET config = json_set(
    config,
    '$.connection.host', 'localhost',
    '$.connection.port', 5433
)
WHERE alias IN ('Calocalc_inscription', 'Calocalc', 'Calocalc_native');
```

**Inconvénient** :
- ⚠️ NocoDB peut aussi bloquer `localhost` comme hostname

---

### Option C : Tout via IP (localhost tunnel = 127.0.0.1)
**Principe** : 
- Bases locales : IP `10.0.1.23`
- Bases OVH : IP `127.0.0.1` port 5433 (tunnel)

**Avantages** :
- ✅ Utilise des IPs, pas de hostname bloqué
- ✅ Garde le cloisonnement

**Actions** :
```sql
-- 1. Bases locales → 10.0.1.23:5432
UPDATE nc_sources_v2
SET config = json_set(
    config,
    '$.connection.host', '10.0.1.23',
    '$.connection.port', 5432
)
WHERE alias IN ('opepartnerv2', 'excalidraw', 'db_agni', 'calocalc_prospection');

-- 2. Bases OVH → 127.0.0.1:5433 (tunnel)
UPDATE nc_sources_v2
SET config = json_set(
    config,
    '$.connection.host', '127.0.0.1',
    '$.connection.port', 5433
)
WHERE alias IN ('Calocalc_inscription', 'Calocalc', 'Calocalc_native');
```

---

## ❓ Questions à clarifier

### 1. Architecture CaloCalc
- La base `calocalc_inscription` principale est-elle bien sur OVH ?
- La copie sur Hostinger est-elle à jour ou obsolète ?
- Faut-il garder le tunnel SSH ou tout migrer sur Hostinger ?

### 2. Base_AgniConsult
- Cette base est dans quel container Postgres ?
- Quel est le mot de passe du user d'accès ?
- Est-ce la base `Base_AgniConsult` ou `db_agni` ?

### 3. Source "Calocalc" vs "Calocalc_inscription"
- Pourquoi 2 sources pour la même base ?
- Doit-on en supprimer une ou les garder ?

---

## 🎯 Recommandation finale

**Je recommande Option C (IP + tunnel)** car :
1. Résout le problème "Forbidden hostname" pour TOUTES les sources
2. Garde le cloisonnement OVH (CaloCalc) / Hostinger (OPEPARTNER)
3. Utilise le tunnel SSH déjà en place
4. Pas de migration de données nécessaire

**Prochaines étapes** :
1. Clarifier les 3 questions ci-dessus
2. Préparer le script SQL final
3. Tester sur une source d'abord
4. Appliquer à toutes les sources

---

**Christophe, dis-moi :**
- Veux-tu garder CaloCalc sur OVH (tunnel) ou tout migrer sur Hostinger ?
- C'est quoi exactement la base `Base_AgniConsult` et où est-elle ?
