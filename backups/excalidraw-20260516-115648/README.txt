========================================
BACKUP SERVICE EXCALIDRAW
Date: 2026-05-16 11:56:48
Raison: Avant suppression du healthcheck du container proxy
========================================

CONTENU DU BACKUP:
------------------
✓ excalidraw_storage.sql.gz (5.5K) - Base PostgreSQL complete
✓ docker-compose.yml (2.3K) - Configuration service
✓ proxy-inspect.json (13K) - Config container proxy
✓ backend-inspect.json (9.8K) - Config container backend
✓ excalidraw-proxy-old.tar.gz (25M) - Image Docker proxy
✓ RESTORE.sh - Script restauration automatique

RESTAURER EN CAS DE PROBLEME:
------------------------------
bash /root/backups/excalidraw-20260516-115648/RESTORE.sh

INFORMATIONS TECHNIQUES:
------------------------
- Container PostgreSQL: pk4s888o4wkc8ogokg0sg840
- Base: excalidraw_storage
- User: excalidraw_backend
- Service Coolify: o8wsgoowkcogkgk0g8o4g8s0

MODIFICATION PREVUE:
--------------------
Suppression du healthcheck pour eliminer le statut "Degraded" dans Coolify.
Service fonctionne normalement, seul le monitoring est impacte.
