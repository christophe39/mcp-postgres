# Bonnes pratiques de sécurité

## ⚠️ Règles absolues

### 1. **Jamais de credentials en clair dans Git**

❌ **Interdit** :
- Passwords, tokens, API keys dans le code source
- Credentials dans la documentation (README, guides techniques)
- Fichiers `.env` contenant des secrets réels

✅ **Autorisé** :
- Fichiers `.env.example` avec des placeholders
- Documentation référençant `***VOIR_FICHIER_.ENV***`
- Variables d'environnement injectées au runtime

### 2. **Pattern recommandé pour la documentation**

Lorsqu'un document technique doit mentionner des credentials :

```markdown
**Connexion PostgreSQL** :
```
Host: 10.0.1.23
Port: 5432
User: excalidraw_backend
Password: ***VOIR_FICHIER_.ENV_DU_SERVICE***
Database: excalidraw_storage
```

**Emplacement réel** : fichier `.env` du service concerné (non versionné)
```

### 3. **Rotation des credentials compromis**

Si un secret a été commité (même localement, même pas poussé) :

1. **Nettoyer l'historique Git** :
   ```bash
   git reset --soft HEAD~N  # N = nombre de commits à défaire
   # Modifier les fichiers pour retirer les secrets
   git add .
   git commit -m "docs: Version nettoyée (secrets retirés)"
   ```

2. **Regénérer le secret compromis** :
   - Password Postgres : `ALTER USER nom_user WITH PASSWORD 'nouveau_mot_de_passe';`
   - Tokens API : regénérer via l'interface admin du service
   - Clés SSH/GPG : révoquer et recréer

3. **Mettre à jour les `.env` des services** concernés

### 4. **Outils de prévention**

#### Pre-commit hooks (recommandé)

Installer `gitleaks` ou `detect-secrets` :

```bash
# Installation gitleaks (macOS)
brew install gitleaks

# Ajouter un hook pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
gitleaks protect --staged --verbose
EOF
chmod +x .git/hooks/pre-commit
```

#### GitHub Secret Scanning (si repo GitHub)

- Activer "Secret scanning" dans les settings du repo
- Activer "Push protection" pour bloquer les pushs contenant des secrets

### 5. **Checklist avant tout commit**

- [ ] Aucun fichier `.env` avec des vrais secrets n'est staged
- [ ] Les docs ne contiennent que des placeholders (`***VOIR_.ENV***`)
- [ ] Les exemples de code utilisent `process.env.VAR_NAME`, pas de valeurs hardcodées
- [ ] Si doute, relire le diff : `git diff --cached`

### 6. **Si un secret a été poussé sur GitHub**

**Procédure d'urgence** :

1. **Regénérer immédiatement** le secret compromis
2. **Nettoyer l'historique GitHub** :
   ```bash
   # Option 1 : BFG Repo-Cleaner (recommandé)
   brew install bfg
   bfg --replace-text passwords.txt repo.git
   git push --force

   # Option 2 : git filter-branch (plus complexe)
   git filter-branch --tree-filter 'rm -f fichier_compromis.txt' HEAD
   git push --force
   ```

3. **Notifier GitHub** via support si le repo était public

---

## 📋 Incident du 2026-05-16

**Détecté** : Credentials Postgres + ADMIN_TOKEN dans `docs/ARCHITECTURE.md` et `docs/MCP-EXCALIDRAW-TECHNICAL-BRIEF.md`

**Actions prises** :
- ✅ Vérification : commits non poussés sur GitHub (seulement local)
- ✅ Reset des commits locaux (`git reset --soft HEAD~2`)
- ✅ Remplacement des credentials par placeholders
- ✅ Commit nettoyé
- 🔄 À faire : Rotation des credentials par précaution

**Credentials à regénérer** :
1. Password Postgres user `excalidraw_backend` (service `excalidraw-storage-backend`)
2. `ADMIN_TOKEN` du service auth custom

---

*Document créé le 2026-05-16. À tenir à jour en cas de nouvel incident.*
