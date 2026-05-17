# Guide de rotation - Étapes simples

## 🎯 Ce que tu vas faire

1. Te connecter au VPS en SSH
2. Générer un nouveau password sécurisé
3. Le changer dans Postgres
4. Le mettre à jour dans Coolify

---

## 📝 Étape 1 : Connexion SSH et génération du nouveau password

**Copie-colle dans ton terminal Mac** :

```bash
# 1. Se connecter au VPS
ssh root@69.62.110.207

# 2. Une fois connecté (tu es maintenant sur le VPS), génère le nouveau password
NEW_PASSWORD=$(openssl rand -base64 32)

# 3. Affiche-le et COPIE-LE (tu en auras besoin dans 2 minutes)
echo "=========================================="
echo "NOUVEAU PASSWORD (À COPIER) :"
echo "$NEW_PASSWORD"
echo "=========================================="
```

⚠️ **STOP** : Note ce password quelque part (fichier texte temporaire sur ton Mac). Tu en auras besoin dans 30 secondes.

---

## 📝 Étape 2 : Changer le password dans Postgres

**Tu es toujours connecté en SSH sur le VPS**. Copie-colle ces commandes :

```bash
# 1. Se connecter au container Postgres (celui qui contient excalidraw_storage)
docker exec -it i004k4ckow8c8o8w004wk8oc psql -U excalidraw_backend -d excalidraw_storage

# 2. Tu vas voir un prompt "excalidraw_storage=>"
# Copie-colle cette commande EN REMPLAÇANT "COLLE_TON_PASSWORD_ICI" par le password copié à l'étape 1
ALTER USER excalidraw_backend WITH PASSWORD 'COLLE_TON_PASSWORD_ICI';

# 3. Tu devrais voir "ALTER ROLE"
# Quitte Postgres
\q

# 4. Déconnecte-toi du VPS
exit
```

✅ **Le password Postgres est changé**. Maintenant il faut mettre à jour Coolify.

---

## 📝 Étape 3 : Mettre à jour Coolify (Interface web)

1. **Ouvre ton navigateur** : https://coolify.agnisolution.fr
2. **Login** (tes identifiants Coolify habituels)
3. **Menu gauche** : Clique sur "Projects"
4. **Trouve l'application** : `excalidraw-storage-backend` (ou équivalent)
5. **Onglet "Environment Variables"**
6. **Trouve la variable** `POSTGRES_PASSWORD` ou `DATABASE_PASSWORD`
7. **Clique sur l'icône ✏️ (edit)**
8. **Colle le nouveau password** (celui généré à l'étape 1)
9. **Sauvegarde** (bouton "Update")
10. **Redémarre l'application** : bouton "Restart" ou "Redeploy"

⏳ Attends 30 secondes que le service redémarre.

---

## 📝 Étape 4 : Vérifier que ça marche

**Dans ton terminal Mac** :

```bash
# Reconnecte-toi au VPS
ssh root@69.62.110.207

# Trouve le container du storage-backend
docker ps | grep storage-backend

# Regarde les logs (remplace CONTAINER_ID par l'ID affiché)
docker logs CONTAINER_ID --tail 50

# Tu dois voir des logs normaux, PAS d'erreur "authentication failed"
```

Si tu vois :
- ✅ `Server started on port 8080` → **Parfait, c'est bon !**
- ❌ `Error: password authentication failed` → Le password dans Coolify n'est pas le bon, recommence l'étape 3

---

## 🎉 C'est fini !

Une fois que le service redémarre sans erreur, tu peux :

1. **Détruire ce document** (il contient des infos sensibles)
2. **Pousser sur GitHub** en toute sécurité :
   ```bash
   git push origin main
   ```

---

## ⚠️ En cas de problème

Si le service ne redémarre pas :

```bash
# Reconnecte-toi en SSH
ssh root@69.62.110.207

# Vérifie que le user Postgres existe encore
docker exec -it i004k4ckow8c8o8w004wk8oc psql -U postgres -d excalidraw_storage -c "\du"

# Tu dois voir "excalidraw_backend" dans la liste
```

Ensuite, contacte-moi dans le chat et donne-moi les logs d'erreur.

---

*Document à détruire après utilisation.*
