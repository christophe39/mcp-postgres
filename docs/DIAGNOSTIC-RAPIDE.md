# Diagnostic Rapide Excalidraw

> Aide-mémoire pour résoudre rapidement les problèmes courants

## 🚨 Problème : "Impossible de créer un lien de partage"

### 1. Test rapide

```bash
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}' -w "\nHTTP: %{http_code}\n"
```

### 2. Interpréter le résultat

| Code HTTP | Erreur | Solution | Fichier |
|-----------|--------|----------|---------|
| **404** | Cannot POST /api/v2/post/ | [→ Routing Traefik](#fix-404) | #1 |
| **502** | Bad Gateway | [→ Proxy ↔ Backend](#fix-502) | #2 |
| **201** | {"id":"..."} | ✅ API OK | - |

---

## <a name="fix-404"></a>Fix #1 : HTTP 404 (Routing Traefik)

**Cause :** Traefik route vers le backend au lieu du proxy.

**Diagnostic :**
```bash
ssh root@69.62.110.207
curl -s http://localhost:8080/api/http/routers | \
  jq -r '.[] | select(.rule | contains("exca-api")) | .service' | sort -u

# ❌ Si tu vois "backend-..." → PROBLÈME
```

**Solution (1 minute) :**

1. **Dans Coolify UI :**
   - Service Backend → Settings
   - Champ "Domains" → **VIDER COMPLÈTEMENT**
   - Save → Deploy

2. **OU en SSH :**
   ```bash
   cd /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0
   sed -i '/traefik.http.routers.*backend.*exca-api/d' docker-compose.yml
   docker compose up -d backend
   docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0
   ```

---

## <a name="fix-502"></a>Fix #2 : HTTP 502 (Proxy ↔ Backend)

**Cause :** Le proxy a l'ancienne IP du backend en cache.

**Solution (10 secondes) :**

```bash
ssh root@69.62.110.207
docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0
```

Attendre 3 secondes, puis retester.

---

## 📊 Checklist post-deploy

Après chaque modification dans Coolify :

```bash
ssh root@69.62.110.207

# 1. Vérifier que backend n'a PAS de route Traefik
curl -s http://localhost:8080/api/http/routers | \
  jq -r '.[] | select(.rule | contains("exca-api")) | .service' | sort -u
# ✅ Doit afficher SEULEMENT : excalidraw-proxy

# 2. Redémarrer le proxy
docker restart proxy-o8wsgoowkcogkgk0g8o4g8s0

# 3. Tester POST
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
# ✅ Doit retourner : {"id":"..."}

# 4. Tester dans Excalidraw
# → Dessiner + Share → Doit fonctionner
```

---

## 🆘 Panique totale

```bash
ssh root@69.62.110.207
cd /data/coolify/services/o8wsgoowkcogkgk0g8o4g8s0

# Tout redémarrer
docker compose restart

# Supprimer les routes backend
sed -i '/traefik.http.routers.*backend.*exca-api/d' docker-compose.yml
docker compose up -d

# Tester
curl -X POST https://exca-api.agnisolution.fr/api/v2/post/ -d '{"test":true}'
```

---

**Pour plus de détails :** Voir [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
